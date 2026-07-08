"""
build_masks.py
Downloads and builds two static quality masks for the DRC flood detection pipeline:

  1. Slope mask (Copernicus DEM GLO-30 via Element84 STAC)
     - Pixels with terrain slope > 8° are flagged as unreliable
     - Removes Virunga / Ruwenzori mountain artefacts from flood maps

  2. Permanent water mask (JRC Global Surface Water v1.4 2021)
     - Pixels where water occurrence >= 75% across 1984-2021 are permanent water
     - Prevents permanent lakes/rivers from being flagged as flood events

Both masks are saved as uint8 COGs in OUTPUT_CRS at RESAMPLE_M resolution,
aligned to the AOI bounding box. Apply in the detection loop: mask pixels → nodata (255).

Run once; outputs persist in data/raw/masks/.
"""

import os, sys, warnings
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.shutil import copy as rio_copy
from rasterio.warp import reproject, Resampling as WarpResampling
import yaml
import pystac_client
import planetary_computer
import odc.stac

warnings.filterwarnings("ignore")
os.environ["AWS_NO_SIGN_REQUEST"] = "YES"

# ── Config ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)

with open("config/config.yaml") as f:
    cfg = yaml.safe_load(f)

b = cfg["aoi"]["bbox"]
BBOX       = [b["west"], b["south"], b["east"], b["north"]]
OUTPUT_CRS = cfg["aoi"]["output_crs"]
RESAMPLE_M = 100   # match detection pipeline resolution

MASKS_DIR = os.path.join(PROJECT_ROOT, "data", "raw", "masks")
os.makedirs(MASKS_DIR, exist_ok=True)

SLOPE_PATH      = os.path.join(MASKS_DIR, "slope_mask.tif")
PERM_WATER_PATH = os.path.join(MASKS_DIR, "perm_water_mask.tif")

SLOPE_THRESHOLD_DEG   = 8.0   # degrees — matches COD plan
PERM_WATER_OCCURRENCE = 75    # % — pixels water >= this % of the time are permanent

print(f"Masks dir  : {MASKS_DIR}")
print(f"Output CRS : {OUTPUT_CRS}  |  Resolution: {RESAMPLE_M} m")
print(f"AOI (WGS84): {BBOX}")
print()


def write_mask_cog(array, profile, path):
    """Write uint8 mask as a Cloud-Optimised GeoTIFF."""
    tmp = path + ".tmp.tif"
    p = profile.copy()
    p.update(driver="GTiff", dtype="uint8", count=1, nodata=None,
             compress="deflate", tiled=True, blockxsize=512, blockysize=512)
    with rasterio.open(tmp, "w", **p) as dst:
        dst.write(array.astype("uint8"), 1)
    with rasterio.open(tmp, "r+") as dst:
        dst.build_overviews([2, 4, 8, 16], Resampling.nearest)
        dst.update_tags(ns="rio_overview", resampling="nearest")
    rio_copy(tmp, path, driver="GTiff", copy_src_overviews=True,
             compress="deflate", tiled=True, blockxsize=512, blockysize=512)
    os.remove(tmp)
    print(f"  Saved: {path}")


# ══════════════════════════════════════════════════════════════════════════════
# MASK 1 — Slope from Copernicus DEM GLO-30
# ══════════════════════════════════════════════════════════════════════════════

if os.path.exists(SLOPE_PATH):
    print("[SLOPE] Already exists — skipping.")
else:
    print("[SLOPE] Fetching Copernicus DEM GLO-30 via Element84 STAC...")
    try:
        catalog = pystac_client.Client.open("https://earth-search.aws.element84.com/v1")
        search  = catalog.search(collections=["cop-dem-glo-30"], bbox=BBOX)
        items   = list(search.items())
        print(f"  Found {len(items)} DEM tile(s).")

        if not items:
            raise RuntimeError("No DEM tiles found for AOI.")

        # Load at RESAMPLE_M in OUTPUT_CRS — odc-stac handles mosaicking automatically
        ds = odc.stac.load(
            items,
            bands      = ["data"],
            bbox       = BBOX,
            resolution = RESAMPLE_M,
            crs        = OUTPUT_CRS,
            dtype      = "float32",
            chunks     = {"x": 512, "y": 512},
        )
        # Multiple time slices possible if tiles have different dates; take max (stable terrain)
        dem = ds["data"].max(dim="time").compute().values
        print(f"  DEM loaded: {dem.shape}, range {np.nanmin(dem):.0f}–{np.nanmax(dem):.0f} m")

        # Slope from projected DEM (pixel size = RESAMPLE_M metres)
        gy, gx   = np.gradient(dem, RESAMPLE_M)
        slope_deg = np.degrees(np.arctan(np.sqrt(gx**2 + gy**2)))
        slope_mask = (slope_deg > SLOPE_THRESHOLD_DEG).astype("uint8")
        flagged_pct = 100 * slope_mask.sum() / slope_mask.size
        print(f"  Slope mask: {flagged_pct:.1f}% of pixels flagged (>{SLOPE_THRESHOLD_DEG}°)")

        # Build profile from loaded dataset
        transform = ds.odc.transform
        profile = {
            "crs": OUTPUT_CRS,
            "transform": transform,
            "width": slope_mask.shape[1],
            "height": slope_mask.shape[0],
        }
        write_mask_cog(slope_mask, profile, SLOPE_PATH)
        print("[SLOPE] Done.")

    except Exception as e:
        print(f"[SLOPE] FAILED: {e}")
        print("  Slope mask will not be applied. Resolve the error and re-run build_masks.py.")

print()


# ══════════════════════════════════════════════════════════════════════════════
# MASK 2 — Permanent water from JRC Global Surface Water v1.4 2021
# ══════════════════════════════════════════════════════════════════════════════

if os.path.exists(PERM_WATER_PATH):
    print("[JRC] Already exists — skipping.")
else:
    print("[JRC] Fetching JRC Global Surface Water occurrence via Microsoft Planetary Computer...")
    try:
        mpc_catalog = pystac_client.Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=planetary_computer.sign_inplace,
        )
        search = mpc_catalog.search(collections=["jrc-gsw"], bbox=BBOX)
        items  = list(search.items())
        print(f"  Found {len(items)} JRC GSW item(s).")

        if not items:
            raise RuntimeError("No JRC GSW items found for AOI.")

        ds = odc.stac.load(
            items,
            bands      = ["occurrence"],
            bbox       = BBOX,
            resolution = RESAMPLE_M,
            crs        = OUTPUT_CRS,
            dtype      = "float32",
            chunks     = {"x": 512, "y": 512},
        )
        # occurrence is a static product; take max across any time dimension
        occurrence = ds["occurrence"].max(dim="time").compute().values
        print(f"  Occurrence loaded: {occurrence.shape}, range {np.nanmin(occurrence):.0f}–{np.nanmax(occurrence):.0f}%")

        perm_water  = (occurrence >= PERM_WATER_OCCURRENCE).astype("uint8")
        flagged_pct = 100 * perm_water.sum() / perm_water.size
        print(f"  Permanent water mask: {flagged_pct:.1f}% of pixels flagged (>={PERM_WATER_OCCURRENCE}% occurrence)")

        transform = ds.odc.transform
        profile = {
            "crs": OUTPUT_CRS,
            "transform": transform,
            "width": perm_water.shape[1],
            "height": perm_water.shape[0],
        }
        write_mask_cog(perm_water, profile, PERM_WATER_PATH)
        print("[JRC] Done.")

    except Exception as e:
        print(f"[JRC] FAILED: {e}")
        print("  Permanent water mask will not be applied. Re-run build_masks.py to retry.")

print()
print("build_masks.py complete.")
print(f"  Slope mask      : {'OK' if os.path.exists(SLOPE_PATH) else 'MISSING'} — {SLOPE_PATH}")
print(f"  Perm water mask : {'OK' if os.path.exists(PERM_WATER_PATH) else 'MISSING'} — {PERM_WATER_PATH}")
