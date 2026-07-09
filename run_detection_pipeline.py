"""
run_detection_pipeline.py
Builds baseline_VV.tif (if missing) then runs NB03 flood detection for all months.
Run from project root with gis_project gis_env Python.
Outputs are saved incrementally — safe to kill and restart; completed months are skipped.
"""

import os, sys, warnings
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.shutil import copy as rio_copy
from rasterio.features import shapes as rio_shapes
from scipy.ndimage import binary_opening, median_filter
from shapely.geometry import shape
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend — no display needed
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import yaml

try:
    from skimage.filters import threshold_otsu
    _SKIMAGE_AVAILABLE = True
except ImportError:
    _SKIMAGE_AVAILABLE = False
    print("[WARN] scikit-image not installed — Otsu threshold unavailable; falling back to fixed −3 dB")

warnings.filterwarnings("ignore")

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)

with open("config/config.yaml") as f:
    cfg = yaml.safe_load(f)

PROCESSED_DIR       = os.path.join(PROJECT_ROOT, "data", "processed", "sar")
OUTPUT_DIR          = os.path.join(PROJECT_ROOT, "data", "outputs", "flood_extent")
BASELINE_PATH       = os.path.join(PROCESSED_DIR, "baseline_VV.tif")
BASELINE_MONTHS     = cfg["processing"]["baseline_months"]
OUTPUT_CRS          = cfg["aoi"]["output_crs"]
CHANGE_THRESHOLD_DB  = float(cfg["processing"].get("change_threshold_db", -5.0))
                               # raised from -3 dB: tropical forest/wet-soil onset can
                               # produce -3 to -5 dB drops with no standing water.
                               # Sep 2025 spike (3,427 km²) was likely wet-soil artifact.
                               # -5 dB requires deeper suppression consistent with open water.
RESAMPLE_M           = 100
FORCE_REPROCESS      = True    # rerun all months with corrected threshold

# Threshold method: read from config; fall back to "fixed" if skimage unavailable
_CFG_METHOD = cfg["processing"].get("flood_threshold_method", "fixed")
THRESHOLD_METHOD = _CFG_METHOD if (_CFG_METHOD != "otsu" or _SKIMAGE_AVAILABLE) else "fixed"

# Post-processing method: "median7" (UN-SPIDER recommended) or "opening3" (prior default)
POSTPROC_METHOD = "median7"   # change to "opening3" to restore prior behaviour

# VH/VV ratio discriminator — water has low VH relative to VV (ratio typically < -12 dB);
# wet soil and vegetation maintain higher VH.  Set to None to disable (no VH files yet).
VH_RATIO_THRESHOLD_DB = None   # enable by setting to e.g. -10.0 once VH composites verified

MASKS_DIR       = os.path.join(PROJECT_ROOT, "data", "raw", "masks")
SLOPE_PATH      = os.path.join(MASKS_DIR, "slope_mask.tif")
PERM_WATER_PATH = os.path.join(MASKS_DIR, "perm_water_mask.tif")

os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"Project root : {PROJECT_ROOT}")
print(f"Processed SAR: {PROCESSED_DIR}")
print(f"Outputs      : {OUTPUT_DIR}")
print(f"Threshold    : {THRESHOLD_METHOD.upper()}  ({CHANGE_THRESHOLD_DB} dB fixed fallback)  |  Resolution: {RESAMPLE_M} m")
print(f"Post-proc    : {POSTPROC_METHOD}")
print(f"Force reprocess: {FORCE_REPROCESS}")
print()

# ── Helpers ────────────────────────────────────────────────────────────────────

def read_band(path, resample_m=RESAMPLE_M):
    with rasterio.open(path) as src:
        if resample_m is None:
            arr = src.read(1).astype("float32")
            transform = src.transform
        else:
            native_res = abs(src.transform.a)
            scale = resample_m / native_res
            h = max(1, int(src.height / scale))
            w = max(1, int(src.width  / scale))
            # Pass (h, w) directly for single-band read — always returns 2D
            arr = src.read(1, out_shape=(h, w),
                           resampling=Resampling.average).astype("float32")
            transform = src.transform * src.transform.scale(scale, scale)
        assert arr.ndim == 2, f"read_band: expected 2D array, got {arr.shape} from {path}"
        return arr, transform, src.crs


def write_cog(array, profile, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tmp = output_path + ".tmp.tif"
    p = profile.copy()
    p.update(driver="GTiff", compress="deflate", tiled=True,
             blockxsize=512, blockysize=512, count=1)
    with rasterio.open(tmp, "w", **p) as dst:
        dst.write(array, 1)
    with rasterio.open(tmp, "r+") as dst:
        dst.build_overviews([2, 4, 8, 16], rasterio.enums.Resampling.nearest)
        dst.update_tags(ns="rio_overview", resampling="nearest")
    rio_copy(tmp, output_path, driver="GTiff", copy_src_overviews=True,
             compress="deflate", tiled=True, blockxsize=512, blockysize=512)
    os.remove(tmp)
    print(f"  Saved: {output_path}")


# ── Step 1: Build baseline ─────────────────────────────────────────────────────

if os.path.exists(BASELINE_PATH):
    print(f"[BASELINE] Already exists — skipping build.")
else:
    print(f"[BASELINE] Building from first {BASELINE_MONTHS} VV months at {RESAMPLE_M}m...")
    vv_all = sorted([f for f in os.listdir(PROCESSED_DIR)
                     if f.endswith("_VV.tif") and "baseline" not in f])

    # 2025-01 and 2025-02 were processed by an older NB02 build that stored raw
    # amplitude DN instead of calibrated sigma0 dB — their medians are ~+21 dB
    # vs the correct ~-8 dB for all later months. Skip them for the baseline.
    calibrated = [f for f in vv_all if f >= "2025-03"]
    files_for_baseline = calibrated[:BASELINE_MONTHS]

    if len(files_for_baseline) < BASELINE_MONTHS:
        print(f"  ERROR: Not enough calibrated VV files. Aborting.")
        sys.exit(1)

    print(f"  Using: {files_for_baseline}")

    # Read all baseline months through read_band at RESAMPLE_M — identical to the
    # detection read path — so baseline and monthly values are in the same scale.
    # Three float32 arrays at 100m each ~175 MB; well within memory budget.
    a, transform, crs = read_band(os.path.join(PROCESSED_DIR, files_for_baseline[0]))
    b, _,         _   = read_band(os.path.join(PROCESSED_DIR, files_for_baseline[1]))
    c, _,         _   = read_band(os.path.join(PROCESSED_DIR, files_for_baseline[2]))
    print(f"  Shapes : {a.shape}, {b.shape}, {c.shape}")

    # NaN-safe 3-value median via fmax/fmin (no stack needed)
    median = np.fmax(np.fmin(a, b), np.fmin(np.fmax(a, b), c))
    del a, b, c

    profile = {
        "driver": "GTiff", "dtype": "float32", "nodata": None,
        "crs": crs, "transform": transform,
        "width": median.shape[1], "height": median.shape[0], "count": 1,
        "compress": "deflate", "tiled": True, "blockxsize": 512, "blockysize": 512,
    }
    write_cog(median, profile, BASELINE_PATH)
    del median
    print(f"[BASELINE] Done. {BASELINE_PATH}")

print()

# ── Step 2: Load baseline ─────────────────────────────────────────────────────

with rasterio.open(BASELINE_PATH) as _src:
    print(f"[BASELINE] File  : {_src.width}×{_src.height} px, native_res={abs(_src.transform.a):.2f} m, crs={_src.crs}")
baseline, baseline_transform, baseline_crs = read_band(BASELINE_PATH)
print(f"[BASELINE] Loaded: {baseline.shape} @ {RESAMPLE_M}m")
print(f"[BASELINE] Range : {np.nanmin(baseline):.1f} to {np.nanmax(baseline):.1f} dB")
print()

# ── Step 2b: Load quality masks (optional — skip gracefully if not built yet) ──

def load_mask_aligned(mask_path, target_shape, target_transform, target_crs):
    """Read a mask and resample it to match the target array shape/transform."""
    from rasterio.warp import reproject, Resampling as WarpResampling
    with rasterio.open(mask_path) as src:
        dest = np.zeros(target_shape, dtype="uint8")
        reproject(
            source=rasterio.band(src, 1),
            destination=dest,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=target_transform,
            dst_crs=target_crs,
            resampling=WarpResampling.nearest,
        )
    return dest

slope_mask_arr     = None
perm_water_mask_arr = None

if os.path.exists(SLOPE_PATH):
    print(f"[MASKS] Slope mask found: {SLOPE_PATH}")
else:
    print("[MASKS] Slope mask not found — run build_masks.py to enable. Skipping.")

if os.path.exists(PERM_WATER_PATH):
    print(f"[MASKS] Permanent water mask found: {PERM_WATER_PATH}")
else:
    print("[MASKS] Permanent water mask not found — run build_masks.py to enable. Skipping.")

masks_available = os.path.exists(SLOPE_PATH) or os.path.exists(PERM_WATER_PATH)
print(f"[MASKS] Quality masking: {'ENABLED' if masks_available else 'DISABLED (run build_masks.py)'}")
print()

# ── Step 3: Flood detection loop ──────────────────────────────────────────────

vv_files = sorted([f for f in os.listdir(PROCESSED_DIR)
                   if f.endswith("_VV.tif") and "baseline" not in f])
print(f"[DETECT] Found {len(vv_files)} monthly VV files to process.")

flood_stats = []

for i, fname in enumerate(vv_files, 1):
    month_str = fname[:7]
    out_tif   = os.path.join(OUTPUT_DIR, f"flood_extent_{month_str}.tif")
    out_json  = os.path.join(OUTPUT_DIR, f"flood_extent_{month_str}.geojson")

    print(f"[{i:02d}/{len(vv_files)}] {month_str}", end=" ... ", flush=True)

    if not FORCE_REPROCESS and os.path.exists(out_tif) and os.path.exists(out_json):
        print("already done — skipping")
        with rasterio.open(out_tif) as src:
            arr = src.read(1)
        valid_px   = int((arr != 255).sum())
        flooded_px = int((arr == 1).sum())
        area_km2   = round(flooded_px * (RESAMPLE_M / 1000) ** 2, 1)
        pct        = round(flooded_px / valid_px * 100, 2) if valid_px else 0
        flood_stats.append({"month": month_str, "flooded_pct": pct,
                            "flooded_px": flooded_px, "flood_area_km2": area_km2})
        continue

    vv, transform, crs = read_band(os.path.join(PROCESSED_DIR, fname))

    change = vv - baseline

    # ── Binarisation ──────────────────────────────────────────────────────────
    if THRESHOLD_METHOD == "otsu":
        # Adaptive Otsu threshold (UN-SPIDER step 6): find optimal water/land
        # split from the bimodal dB-change histogram for this specific month.
        finite_change = change[np.isfinite(change)]
        if finite_change.size > 0:
            thresh = threshold_otsu(finite_change)
            # Otsu finds the split but we only want pixels darker than land →
            # take the lower (water) half of the histogram.
            thresh = min(thresh, CHANGE_THRESHOLD_DB)
        else:
            thresh = CHANGE_THRESHOLD_DB
        flood_mask = (change < thresh).astype("uint8")
        print(f"  [Otsu] thresh={thresh:.2f} dB", end="  ", flush=True)
    else:
        flood_mask = (change < CHANGE_THRESHOLD_DB).astype("uint8")

    nodata_mask = ~np.isfinite(vv) | ~np.isfinite(baseline)
    flood_mask[nodata_mask] = 255

    # ── Post-processing noise removal ─────────────────────────────────────────
    if POSTPROC_METHOD == "median7":
        # 7×7 median filter (UN-SPIDER step 7) — more spatially adaptive than
        # binary_opening; preserves area while suppressing isolated noisy pixels.
        valid_binary = (flood_mask == 1).astype("float32")
        smoothed     = median_filter(valid_binary, size=7)
        flood_mask   = np.where(flood_mask == 255, 255,
                                (smoothed > 0.5).astype("uint8"))
    else:
        # Prior default: binary morphological opening (3×3)
        valid   = flood_mask == 1
        cleaned = binary_opening(valid, structure=np.ones((3, 3)))
        flood_mask[valid & ~cleaned] = 0

    # ── Apply quality masks (set flagged pixels to nodata=255) ────────────────
    if os.path.exists(SLOPE_PATH):
        slope_m = load_mask_aligned(SLOPE_PATH, flood_mask.shape, transform, crs)
        flood_mask[slope_m == 1] = 255

    if os.path.exists(PERM_WATER_PATH):
        water_m = load_mask_aligned(PERM_WATER_PATH, flood_mask.shape, transform, crs)
        flood_mask[water_m == 1] = 255

    # ── VH/VV ratio discriminator (wet-soil / wet-vegetation suppression) ────
    # Open water: VH << VV (ratio typically < -10 dB).
    # Wet soil / wet forest: VH and VV both reduced but ratio is higher (~-6 to -8 dB).
    # If VH file is available and VH_RATIO_THRESHOLD_DB is set, mask pixels where
    # the VH/VV ratio is above the threshold (not water-like).
    if VH_RATIO_THRESHOLD_DB is not None:
        vh_path = os.path.join(PROCESSED_DIR, fname.replace("_VV.tif", "_VH.tif"))
        if os.path.exists(vh_path):
            vh, _, _ = read_band(vh_path)
            with np.errstate(invalid="ignore"):
                vh_vv_ratio = vh - vv   # both in dB, so subtraction = ratio in dB
            # mask pixels where ratio is too high to be open water
            non_water_ratio = (vh_vv_ratio > VH_RATIO_THRESHOLD_DB) & np.isfinite(vh_vv_ratio)
            flood_mask[non_water_ratio & (flood_mask == 1)] = 0
            ratio_removed = int(non_water_ratio.sum())
            print(f"  [VH/VV] {ratio_removed:,} px removed by ratio filter", end="  ", flush=True)

    out_profile = {
        "driver": "GTiff", "dtype": "uint8", "nodata": 255,
        "crs": crs, "transform": transform,
        "width": flood_mask.shape[1], "height": flood_mask.shape[0], "count": 1,
        "compress": "deflate", "tiled": True, "blockxsize": 512, "blockysize": 512,
    }
    tmp = out_tif + ".tmp.tif"
    with rasterio.open(tmp, "w", **out_profile) as dst:
        dst.write(flood_mask, 1)
    with rasterio.open(tmp, "r+") as dst:
        dst.build_overviews([2, 4, 8, 16], Resampling.nearest)
        dst.update_tags(ns="rio_overview", resampling="nearest")
    rio_copy(tmp, out_tif, driver="GTiff", copy_src_overviews=True,
             compress="deflate", tiled=True, blockxsize=512, blockysize=512)
    os.remove(tmp)

    flood_geoms = [
        shape(s) for s, v in rio_shapes(flood_mask, mask=(flood_mask == 1), transform=transform)
    ]
    if flood_geoms:
        gdf = gpd.GeoDataFrame({"month": [month_str] * len(flood_geoms)}, geometry=flood_geoms, crs=crs)
        gdf = gdf.dissolve(by="month").reset_index()
        gdf = gdf.to_crs("EPSG:4326")
        gdf.to_file(out_json, driver="GeoJSON")

    valid_px   = int((flood_mask != 255).sum())
    flooded_px = int((flood_mask == 1).sum())
    area_km2   = round(flooded_px * (RESAMPLE_M / 1000) ** 2, 1)
    pct        = round(flooded_px / valid_px * 100, 2) if valid_px else 0
    flood_stats.append({"month": month_str, "flooded_pct": pct,
                        "flooded_px": flooded_px, "flood_area_km2": area_km2})

    geojson_note = f"{len(flood_geoms)} polygon(s)" if flood_geoms else "no flooded pixels"
    print(f"{pct}% flooded — {area_km2} km²  ({geojson_note})")

# ── Step 4: Summary table + charts ────────────────────────────────────────────

print()
print("[SUMMARY]")
df = pd.DataFrame(flood_stats).set_index("month").sort_index()
print(df.to_string())

# Save stats CSV
csv_path = os.path.join(OUTPUT_DIR, "flood_stats.csv")
df.to_csv(csv_path)
print(f"\nStats saved: {csv_path}")

# Bar chart — flood area per month
fig, ax = plt.subplots(figsize=(13, 4))
ax.bar(df.index, df["flood_area_km2"], color="#1a6faf")
ax.set_ylabel("Flooded area (km²)")
ax.set_xlabel("Month")
ax.set_title("Monthly Flood Extent — Eastern DRC (100 m, -3 dB threshold)")
ax.tick_params(axis="x", rotation=45)
plt.tight_layout()
chart_path = os.path.join(OUTPUT_DIR, "flood_area_timeseries.png")
plt.savefig(chart_path, dpi=150)
plt.close()
print(f"Chart saved: {chart_path}")

# Map of latest flood extent
flood_files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".tif")])
if flood_files:
    latest = flood_files[-1]
    with rasterio.open(os.path.join(OUTPUT_DIR, latest)) as src:
        flood = src.read(1)

    cmap   = mcolors.ListedColormap(["#d4e6b5", "#1a6faf", "#cccccc"])
    bounds = [-0.5, 0.5, 1.5, 255.5]
    norm   = mcolors.BoundaryNorm(bounds, cmap.N)
    month_label = latest.replace("flood_extent_", "").replace(".tif", "")

    plt.figure(figsize=(14, 10))
    im = plt.imshow(flood, cmap=cmap, norm=norm)
    cbar = plt.colorbar(im, ticks=[0, 1, 255], shrink=0.6)
    cbar.set_ticklabels(["Not flooded", "Flooded", "Nodata"])
    plt.title(f"Flood Extent — {month_label}")
    plt.axis("off")
    plt.tight_layout()
    map_path = os.path.join(OUTPUT_DIR, f"flood_map_{month_label}.png")
    plt.savefig(map_path, dpi=150)
    plt.close()
    print(f"Map saved : {map_path}")

print()
print("[DONE] Pipeline complete.")
