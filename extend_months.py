"""
extend_months.py
================
Acquires and processes Sentinel-1 RTC SAR composites for a set of months, then runs
flood detection for each of them against the existing baseline_VV.tif.

Run from project root with the gis_env Python interpreter:
    & "C:/Users/trevm/Projects/SpatialLab/gis_env/Scripts/python.exe" extend_months.py
    & "C:/Users/trevm/Projects/SpatialLab/gis_env/Scripts/python.exe" extend_months.py 2026-06 2026-07

Months are given as YYYY-MM arguments; with no arguments it processes DEFAULT_MONTHS.

Prerequisites
-------------
- Existing baseline_VV.tif (2025-03/04/05 median) in data/processed/sar/
- Quality masks already built via build_masks.py
- Conda/venv with: rasterio, rioxarray, stackstac, pystac-client, odc-stac, odc-geo,
                   geopandas, scipy, numpy, matplotlib, pyyaml

What this script does
---------------------
1. For each target month:
   a. Searches Microsoft Planetary Computer for sentinel-1-rtc scenes intersecting
      the Eastern DRC AOI.
   b. Loads the VV band via odc-stac block by block, computes a monthly median
      composite at NATIVE_M resolution, converts sigma0 power to dB, writes a COG.
   c. If the VV file already exists it is skipped, unless FORCE_REPROCESS_SAR.
2. Runs the existing detection algorithm (threshold from config) for each month.
3. Updates data/outputs/flood_extent/flood_stats.csv and regenerates the
   time-series bar chart.

Read-failure handling
---------------------
MPC intermittently fails reads on RTC tiles that pass a header/center-window check —
surfacing as WarpOperationError or RasterioIOError during warp. Loading the whole AOI in
one call means one such failure loses the entire month, which is what produced the
2026-06 data gap. load_median_vv() composites in horizontal blocks and retries a failed
block later in the run; the failures are usually transient and read fine minutes later.
See that function for the full policy.
"""

import os
import re
import sys
import time
import warnings
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.shutil import copy as rio_copy
from rasterio.features import shapes as rio_shapes
from rasterio.warp import reproject, Resampling as WarpResampling
from scipy.ndimage import binary_opening, median_filter

try:
    from skimage.filters import threshold_otsu
    _SKIMAGE_AVAILABLE = True
except ImportError:
    _SKIMAGE_AVAILABLE = False
from shapely.geometry import shape
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml

warnings.filterwarnings("ignore")

# Allow unauthenticated reads from public AWS S3 buckets (Sentinel-1 data).
# Must be set before any rasterio / odc-stac import touches GDAL.
os.environ.setdefault("AWS_NO_SIGN_REQUEST", "YES")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-west-2")

# GDAL HTTP settings — set via os.environ so dask worker threads inherit them.
# rasterio.Env() is NOT inherited by threads spawned by dask.
os.environ["GDAL_HTTP_TIMEOUT"]              = "600"
os.environ["GDAL_HTTP_MAX_RETRY"]            = "5"
os.environ["GDAL_HTTP_RETRY_DELAY"]          = "2"
os.environ["GDAL_DISABLE_READDIR_ON_OPEN"]   = "EMPTY_DIR"
os.environ["CPL_VSIL_CURL_ALLOWED_EXTENSIONS"] = ".tiff,.tif"

# ── Config ────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)

with open("config/config.yaml") as f:
    cfg = yaml.safe_load(f)

PROCESSED_DIR     = PROJECT_ROOT / "data" / "processed" / "sar"
OUTPUT_DIR        = PROJECT_ROOT / "data" / "outputs" / "flood_extent"
MASKS_DIR         = PROJECT_ROOT / "data" / "raw" / "masks"
BASELINE_PATH     = PROCESSED_DIR / "baseline_VV.tif"
SLOPE_PATH        = MASKS_DIR / "slope_mask.tif"
PERM_WATER_PATH   = MASKS_DIR / "perm_water_mask.tif"
CSV_PATH          = OUTPUT_DIR / "flood_stats.csv"

AOI_BBOX          = [cfg["aoi"]["bbox"]["west"],  cfg["aoi"]["bbox"]["south"],
                     cfg["aoi"]["bbox"]["east"],  cfg["aoi"]["bbox"]["north"]]
OUTPUT_CRS        = cfg["aoi"]["output_crs"]
STAC_URL          = cfg["data_sources"]["sar"]["catalog"]
COLLECTION        = cfg["data_sources"]["sar"]["collection"]

DEFAULT_MONTHS       = ["2026-05", "2026-06", "2026-07"]
NEW_MONTHS           = sys.argv[1:] or DEFAULT_MONTHS
for _m in NEW_MONTHS:
    if not re.fullmatch(r"\d{4}-\d{2}", _m):
        sys.exit(f"ERROR: month arguments must look like YYYY-MM (got {_m!r})")

CHANGE_THRESHOLD_DB  = float(cfg["processing"].get("change_threshold_db", -5.0))
RESAMPLE_M           = 100          # detection resolution (metres)
NATIVE_M             = 40           # acquisition resolution (metres) — 40 m for new months;
                                    # detection resamples to 100 m regardless, result is identical
FORCE_REPROCESS_SAR  = True         # overwrite existing files (needed after switching GRD→RTC)
BLOCK_ROWS           = 2048         # rows per acquisition block — confines a corrupt tile
                                    # to one strip instead of failing the whole month

_CFG_METHOD      = cfg["processing"].get("flood_threshold_method", "fixed")
THRESHOLD_METHOD = _CFG_METHOD if (_CFG_METHOD != "otsu" or _SKIMAGE_AVAILABLE) else "fixed"
POSTPROC_METHOD  = "median7"        # 7×7 median (UN-SPIDER); "opening3" for prior default

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR,    exist_ok=True)

print("=" * 70)
print("  DRC Flood Mapping — Monthly Extension")
print("=" * 70)
print(f"  AOI    : {AOI_BBOX}")
print(f"  Months : {NEW_MONTHS}")
print(f"  Catalog: {STAC_URL}")
print()

# ── Helpers (shared with run_detection_pipeline.py) ───────────────────────────

def write_cog(array, profile, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(output_path) + ".tmp.tif"
    p = profile.copy()
    p.update(driver="GTiff", compress="deflate", tiled=True,
             blockxsize=512, blockysize=512, count=1)
    with rasterio.open(tmp, "w", **p) as dst:
        dst.write(array, 1)
    with rasterio.open(tmp, "r+") as dst:
        dst.build_overviews([2, 4, 8, 16], rasterio.enums.Resampling.nearest)
        dst.update_tags(ns="rio_overview", resampling="nearest")
    rio_copy(tmp, str(output_path), driver="GTiff", copy_src_overviews=True,
             compress="deflate", tiled=True, blockxsize=512, blockysize=512)
    os.remove(tmp)
    print(f"    Saved: {output_path}")


def read_band_at(path, resample_m=RESAMPLE_M):
    with rasterio.open(path) as src:
        native_res = abs(src.transform.a)
        scale = resample_m / native_res
        h = max(1, int(src.height / scale))
        w = max(1, int(src.width  / scale))
        arr = src.read(1, out_shape=(h, w), resampling=Resampling.average).astype("float32")
        transform = src.transform * src.transform.scale(scale, scale)
    return arr, transform, src.crs


def load_median_vv(items, month_str, native_m=NATIVE_M, block_rows=BLOCK_ROWS):
    """
    Monthly median VV composite over `items`, computed in horizontal blocks.

    Loading the whole AOI at once means any single read failure aborts the month — the
    2026-06 data gap. Blocks bound the blast radius, cap peak memory, and give progress.

    Retry policy
    ------------
    MPC read failures here are overwhelmingly *transient*, not corrupt data: 2026-05
    blocks 9/10 failed mid-run with WarpOperationError/RasterioIOError and then read
    perfectly, to the pixel, minutes later. (Signing style is irrelevant — sign_inplace
    and patch_url were measured identical. patch_url is kept only so runs longer than a
    SAS lifetime stay safe.) So blocks are attempted strictly, and stragglers are
    deferred to a second pass after the rest of the month rather than being retried in
    a tight backoff loop.

    ``fail_on_error=False`` is the last resort only. It stops a genuinely unreadable
    tile from taking the month down, but it applies to *every* read failure, so using
    it unconditionally silently swallows transient errors as nodata — that quietly cost
    2026-05 a sixth of its valid pixels (2.85M px, exactly blocks 9+10) before the
    deferred pass existed. Any block that reaches it is reported to the caller.

    Returns (array, geobox, degraded_row_ranges).
    """
    from odc.stac import load as odc_load
    from odc.geo.geobox import GeoBox
    from odc.geo.geom import box
    import planetary_computer

    bbox_native = box(*AOI_BBOX, crs="EPSG:4326").to_crs(OUTPUT_CRS).boundingbox
    geobox = GeoBox.from_bbox(bbox_native, resolution=native_m)
    ny, nx = geobox.shape
    n_blocks = (ny + block_rows - 1) // block_rows
    print(f"  [SAR] {month_str}: target grid {ny} x {nx} @ {native_m} m "
          f"— {n_blocks} block(s) of {block_rows} rows")

    out      = np.full((ny, nx), np.nan, dtype="float32")
    degraded = []

    def _median(sub_geobox, strict):
        ds = odc_load(items, bands=["vv"], geobox=sub_geobox,
                      chunks={"x": 2048, "y": 2048}, groupby="solar_day",
                      patch_url=planetary_computer.sign,
                      fail_on_error=strict)
        if "vv" not in ds:
            raise KeyError("'vv' missing from loaded dataset")
        return ds["vv"].median(dim="time").compute().values.astype("float32")

    def _try(bi, y0, y1, tries, delay, strict=True):
        """Attempt one block; on success write it into `out` and return True."""
        sub = geobox[y0:y1, :]
        for attempt in range(1, tries + 1):
            try:
                block = _median(sub, strict)
            except Exception as e:
                if attempt < tries:
                    print(f"{type(e).__name__}, retry in {delay * attempt}s ...",
                          end=" ", flush=True)
                    time.sleep(delay * attempt)
                else:
                    print(f"{type(e).__name__}", end=" ", flush=True)
                continue
            out[y0:y1] = block
            # RTC nodata arrives as 0, not NaN — the zero→NaN conversion happens in
            # preprocess_month, so isfinite() here would count nodata as valid.
            valid = int((block > 0).sum())
            note  = "" if strict else " (lenient — partial coverage)"
            print(f"ok{note} — {100 * valid / block.size:.1f}% valid")
            return True
        return False

    # Pass 1 — quick strict attempts. Most blocks land here.
    pending = []
    for bi, y0 in enumerate(range(0, ny, block_rows), start=1):
        y1 = min(y0 + block_rows, ny)
        print(f"    block {bi}/{n_blocks} (rows {y0}-{y1}) ...", end=" ", flush=True)
        if not _try(bi, y0, y1, tries=2, delay=10):
            print("- deferring")
            pending.append((bi, y0, y1))

    # Pass 2 — MPC read failures are usually transient and clear within minutes, so
    # retry the stragglers after the rest of the month rather than sitting in a
    # backoff loop. This is what recovers 2026-05 blocks 9/10, which fail strictly
    # mid-run but read perfectly a few minutes later.
    if pending:
        print(f"  [SAR] {month_str}: second pass over {len(pending)} deferred block(s)")
        still = []
        for bi, y0, y1 in pending:
            print(f"    block {bi}/{n_blocks} (retry) ...", end=" ", flush=True)
            if not _try(bi, y0, y1, tries=3, delay=30):
                print("- still failing")
                still.append((bi, y0, y1))
        pending = still

    # Pass 3 — genuinely unreadable tiles: take partial coverage over losing the month.
    for bi, y0, y1 in pending:
        print(f"    block {bi}/{n_blocks} (lenient) ...", end=" ", flush=True)
        if not _try(bi, y0, y1, tries=1, delay=0, strict=False):
            print("- left as nodata")
        degraded.append((y0, y1))

    return out, geobox, degraded


def load_mask_aligned(mask_path, target_shape, target_transform, target_crs):
    with rasterio.open(mask_path) as src:
        dest = np.zeros(target_shape, dtype="uint8")
        reproject(source=rasterio.band(src, 1), destination=dest,
                  src_transform=src.transform, src_crs=src.crs,
                  dst_transform=target_transform, dst_crs=target_crs,
                  resampling=WarpResampling.nearest)
    return dest


# ── Phase 1: SAR Preprocessing (acquire + composite + dB → COG) ──────────────

def preprocess_month(month_str):
    """
    Search STAC, composite the monthly VV median at NATIVE_M resolution via
    load_median_vv(), convert sigma0 power → dB, write COG.

    Returns the output path, or None if no scenes were found.
    """
    out_path = PROCESSED_DIR / f"{month_str}_VV.tif"
    if out_path.exists() and not FORCE_REPROCESS_SAR:
        size_mb = out_path.stat().st_size / 1e6
        print(f"  [SAR] {month_str}: already exists ({size_mb:.1f} MB) — skipping acquisition.")
        return out_path

    # Date range: full calendar month
    year, month = int(month_str[:4]), int(month_str[5:])
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    dt_start = f"{month_str}-01T00:00:00Z"
    dt_end   = f"{month_str}-{last_day:02d}T23:59:59Z"

    try:
        from pystac_client import Client
    except ImportError:
        print("  ERROR: pystac-client not installed.  Run: pip install pystac-client")
        return None

    try:
        import odc.stac  # noqa: F401 — used by load_median_vv
        import odc.geo   # noqa: F401 — registers ds.odc accessor
    except ImportError:
        print("  ERROR: odc-stac / odc-geo not installed. Run: pip install odc-stac odc-geo")
        return None

    # ── Search MPC sentinel-1-rtc (Radiometrically Terrain Corrected) ──────────
    # RTC delivers float32 sigma0 power — matches the format NB02 (02_preprocessing.ipynb)
    # used for all existing months. GRD (raw amplitude DN) gives wrong dB values because
    # the calibration constant differs between MPC and Element84.
    # Items are left UNSIGNED here on purpose: load_median_vv passes
    # patch_url=planetary_computer.sign so each asset URL is signed at read time.
    # Signing once up front bakes in a SAS token that expires part way through a
    # multi-hour run, which surfaces as RasterioIOError on the later blocks.
    import planetary_computer
    print(f"  [SAR] {month_str}: searching MPC sentinel-1-rtc …")
    mpc_client = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    mpc_search = mpc_client.search(
        collections=["sentinel-1-rtc"],
        bbox=AOI_BBOX,
        datetime=f"{dt_start}/{dt_end}",
        limit=500,
    )
    items = [it for it in mpc_search.items() if "vv" in it.assets]
    print(f"  [SAR] {month_str}: found {len(items)} RTC VV scenes.")

    if not items:
        print(f"  [SAR] {month_str}: no scenes found — writing empty placeholder.")
        placeholder = np.full((1, 1), np.nan, dtype="float32")
        profile = {
            "driver": "GTiff", "dtype": "float32", "nodata": np.nan,
            "count": 1, "height": 1, "width": 1,
            "crs": OUTPUT_CRS,
            "transform": rasterio.transform.from_bounds(*AOI_BBOX, 1, 1),
        }
        write_cog(placeholder, profile, out_path)
        return out_path

    # Pre-filter: read a small center window from each file — filters corrupt tiles
    # that pass HEAD checks but fail during odc-stac warp (causing WarpOperationError).
    from concurrent.futures import ThreadPoolExecutor
    from rasterio.windows import Window

    def _rio_readable(item):
        href = planetary_computer.sign(item.assets["vv"].href)
        try:
            with rasterio.open(href) as src:
                h, w = src.height, src.width
                win = Window(w // 4, h // 4, min(256, w // 2), min(256, h // 2))
                src.read(1, window=win)
            return True
        except Exception:
            return False

    print(f"  [SAR] {month_str}: read-validating {len(items)} RTC files (parallel) …")
    with ThreadPoolExecutor(max_workers=10) as ex:
        flags = list(ex.map(_rio_readable, items))
    items = [it for it, ok in zip(items, flags) if ok]
    print(f"  [SAR] {month_str}: {len(items)} items passed read validation.")
    if not items:
        print(f"  [SAR] {month_str}: no readable files — skipping.")
        return None

    print(f"  [SAR] {month_str}: loading VV band via odc-stac at {NATIVE_M} m …")
    try:
        vv_raw, geobox, degraded_blocks = load_median_vv(items, month_str)
    except Exception as _e:
        print(f"  [SAR] {month_str}: compute error ({type(_e).__name__}): {_e}. Skipping.")
        return None

    if degraded_blocks:
        rows = ", ".join(f"{a}-{b}" for a, b in degraded_blocks)
        print(f"  [SAR] {month_str}: WARNING — {len(degraded_blocks)} block(s) needed the "
              f"lenient fallback; coverage there is partial (rows {rows})")

    # RTC stores float32 sigma0 power; treat 0 as nodata
    vv_raw = np.where(vv_raw <= 0, np.nan, vv_raw)

    valid_px = int(np.isfinite(vv_raw).sum())
    total_px = vv_raw.size
    print(f"  [SAR] {month_str}: {valid_px:,} / {total_px:,} valid pixels "
          f"({100*valid_px/total_px:.1f}%)")
    if valid_px == 0:
        print(f"  [SAR] {month_str}: ERROR — 0 valid pixels. Skipping write.")
        return None

    # RTC sigma0 power → dB (same formula as NB02 to_db)
    with np.errstate(divide="ignore", invalid="ignore"):
        db = np.where(vv_raw > 0, 10.0 * np.log10(vv_raw), np.nan)

    transform = geobox.transform
    crs       = str(geobox.crs)

    profile = {
        "driver": "GTiff", "dtype": "float32", "nodata": np.nan,
        "crs": str(crs), "transform": transform,
        "height": db.shape[0], "width": db.shape[1], "count": 1,
    }
    write_cog(db, profile, out_path)
    size_mb = out_path.stat().st_size / 1e6
    print(f"  [SAR] {month_str}: composite written ({size_mb:.1f} MB).")
    return out_path


# ── Phase 2: Flood Detection ───────────────────────────────────────────────────

def detect_month(month_str, baseline, baseline_transform, baseline_crs):
    """Run change detection for one month against the provided baseline (threshold from config)."""
    vv_path  = PROCESSED_DIR / f"{month_str}_VV.tif"
    out_tif  = OUTPUT_DIR    / f"flood_extent_{month_str}.tif"
    out_json = OUTPUT_DIR    / f"flood_extent_{month_str}.geojson"

    if not vv_path.exists():
        print(f"  [DETECT] {month_str}: VV file missing — skipping detection.")
        return {"month": month_str, "flooded_pct": 0.0, "flooded_px": 0, "flood_area_km2": 0.0}

    size_mb = vv_path.stat().st_size / 1e6
    print(f"  [DETECT] {month_str}: VV = {size_mb:.1f} MB", end=" … ", flush=True)

    if size_mb < 2.0:
        print("too sparse — marking as data gap.")
        return {"month": month_str, "flooded_pct": None, "flooded_px": 0, "flood_area_km2": 0.0,
                "quality": "gap"}

    vv, transform, crs = read_band_at(vv_path)

    change = vv - baseline

    # Binarisation: Otsu adaptive or fixed −3 dB
    if THRESHOLD_METHOD == "otsu" and _SKIMAGE_AVAILABLE:
        finite_change = change[np.isfinite(change)]
        thresh = min(threshold_otsu(finite_change), CHANGE_THRESHOLD_DB) if finite_change.size > 0 else CHANGE_THRESHOLD_DB
        flood_mask = (change < thresh).astype("uint8")
    else:
        flood_mask = (change < CHANGE_THRESHOLD_DB).astype("uint8")

    nodata_mask = ~np.isfinite(vv) | ~np.isfinite(baseline)
    flood_mask[nodata_mask] = 255

    # Post-processing: 7×7 median filter (UN-SPIDER) or 3×3 binary opening
    if POSTPROC_METHOD == "median7":
        valid_binary = (flood_mask == 1).astype("float32")
        smoothed     = median_filter(valid_binary, size=7)
        flood_mask   = np.where(flood_mask == 255, 255, (smoothed > 0.5).astype("uint8"))
    else:
        valid   = flood_mask == 1
        cleaned = binary_opening(valid, structure=np.ones((3, 3)))
        flood_mask[valid & ~cleaned] = 0

    if SLOPE_PATH.exists():
        slope_m = load_mask_aligned(SLOPE_PATH, flood_mask.shape, transform, crs)
        flood_mask[slope_m == 1] = 255

    if PERM_WATER_PATH.exists():
        water_m = load_mask_aligned(PERM_WATER_PATH, flood_mask.shape, transform, crs)
        flood_mask[water_m == 1] = 255

    out_profile = {
        "driver": "GTiff", "dtype": "uint8", "nodata": 255,
        "crs": crs, "transform": transform,
        "width": flood_mask.shape[1], "height": flood_mask.shape[0], "count": 1,
        "compress": "deflate", "tiled": True, "blockxsize": 512, "blockysize": 512,
    }
    tmp = str(out_tif) + ".tmp.tif"
    with rasterio.open(tmp, "w", **out_profile) as dst:
        dst.write(flood_mask, 1)
    with rasterio.open(tmp, "r+") as dst:
        dst.build_overviews([2, 4, 8, 16], Resampling.nearest)
        dst.update_tags(ns="rio_overview", resampling="nearest")
    rio_copy(tmp, str(out_tif), driver="GTiff", copy_src_overviews=True,
             compress="deflate", tiled=True, blockxsize=512, blockysize=512)
    os.remove(tmp)

    flood_geoms = [shape(s) for s, v in rio_shapes(flood_mask, mask=(flood_mask == 1),
                                                    transform=transform)]
    if flood_geoms:
        gdf = gpd.GeoDataFrame({"month": [month_str] * len(flood_geoms)},
                                geometry=flood_geoms, crs=crs)
        gdf = gdf.dissolve(by="month").reset_index().to_crs("EPSG:4326")
        gdf.to_file(str(out_json), driver="GeoJSON")

    valid_px   = int((flood_mask != 255).sum())
    flooded_px = int((flood_mask == 1).sum())
    area_km2   = round(flooded_px * (RESAMPLE_M / 1000) ** 2, 1)
    pct        = round(flooded_px / valid_px * 100, 2) if valid_px else 0.0

    polys = f"{len(flood_geoms)} polygon(s)" if flood_geoms else "no flood pixels"
    print(f"{pct:.2f}% flooded — {area_km2} km²  ({polys})")

    return {"month": month_str, "flooded_pct": pct, "flooded_px": flooded_px,
            "flood_area_km2": area_km2, "quality": "valid"}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not BASELINE_PATH.exists():
        print(f"ERROR: baseline_VV.tif not found at {BASELINE_PATH}")
        print("       Run run_detection_pipeline.py first to build the baseline.")
        sys.exit(1)

    print("[BASELINE] Loading …")
    baseline, baseline_transform, baseline_crs = read_band_at(BASELINE_PATH)
    print(f"[BASELINE] Shape: {baseline.shape}  Range: {np.nanmin(baseline):.1f}–{np.nanmax(baseline):.1f} dB\n")

    # ── Acquisition ──────────────────────────────────────────────────────────
    print("─" * 50)
    print("Phase 1 — SAR Acquisition & Preprocessing")
    print("─" * 50)
    for month_str in NEW_MONTHS:
        preprocess_month(month_str)
    print()

    # ── Detection ────────────────────────────────────────────────────────────
    print("─" * 50)
    print("Phase 2 — Flood Detection")
    print("─" * 50)
    new_rows = []
    for month_str in NEW_MONTHS:
        row = detect_month(month_str, baseline, baseline_transform, baseline_crs)
        new_rows.append(row)
    print()

    # ── Update flood_stats.csv ────────────────────────────────────────────────
    print("─" * 50)
    print("Phase 3 — Updating flood_stats.csv")
    print("─" * 50)
    if CSV_PATH.exists():
        existing = pd.read_csv(CSV_PATH, index_col="month")
    else:
        existing = pd.DataFrame()

    new_df = pd.DataFrame(new_rows).set_index("month")
    # Drop existing rows for months being reprocessed, then append updated ones
    combined = pd.concat([existing[~existing.index.isin(new_df.index)], new_df]).sort_index()
    combined.to_csv(CSV_PATH)
    print(f"  Updated: {CSV_PATH}  ({len(combined)} total months)")
    print()

    # ── Regenerate time-series chart ──────────────────────────────────────────
    print("─" * 50)
    print("Phase 4 — Regenerating time-series chart")
    print("─" * 50)
    plot_df = combined[combined["flood_area_km2"].notna()].copy()
    colors  = ["#d9534f" if str(m) in NEW_MONTHS else "#1a6faf" for m in plot_df.index]

    fig, ax = plt.subplots(figsize=(15, 4))
    ax.bar(plot_df.index, plot_df["flood_area_km2"], color=colors)
    ax.set_ylabel("Flooded area (km²)")
    ax.set_xlabel("Month")
    span = f"{plot_df.index[0]} – {plot_df.index[-1]}" if len(plot_df) else "no data"
    ax.set_title(f"Monthly Flood Extent — Eastern DRC  |  {span}  "
                 f"({RESAMPLE_M} m, {CHANGE_THRESHOLD_DB:g} dB threshold)\n"
                 f"Red bars = months reprocessed in this run ({', '.join(NEW_MONTHS)})")
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()

    chart_path = OUTPUT_DIR / "flood_area_timeseries.png"
    plt.savefig(str(chart_path), dpi=150)
    plt.close()
    print(f"  Chart saved: {chart_path}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 50)
    print("  New months summary")
    print("=" * 50)
    for row in new_rows:
        q = row.get("quality", "valid")
        area = row.get("flood_area_km2", 0)
        pct  = row.get("flooded_pct", 0)
        print(f"  {row['month']}  {area:>8.1f} km²   {str(pct):>6}%   [{q}]")

    print()
    print(f"[DONE] Extension complete for {', '.join(NEW_MONTHS)}.")
    print("       Next steps:")
    print("       1. Inspect VV file sizes: ls data/processed/sar/*_VV.tif")
    print("       2. Re-run notebooks/04_validation_export.ipynb to refresh the Folium map.")
    print("       3. Run build_handover.py to update the researcher package.")
    print("       4. Update PIPELINE_STATUS.md with the new month results.")


if __name__ == "__main__":
    main()
