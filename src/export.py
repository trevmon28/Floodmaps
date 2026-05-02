"""
Export flood extent maps as Cloud-Optimized GeoTIFFs (COG).
Designed for handoff to analysts combining with mobile phone / population data.
"""
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds
import numpy as np
import os


def write_cog(array, profile, output_path):
    """
    Write a numpy array as a Cloud-Optimized GeoTIFF.
    COG layout: tiled internally, with overviews, for efficient remote access.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    profile.update(
        driver="GTiff",
        compress="deflate",
        tiled=True,
        blockxsize=512,
        blockysize=512,
        interleave="band",
        BIGTIFF="IF_SAFER",
    )

    tmp_path = output_path + ".tmp.tif"
    with rasterio.open(tmp_path, "w", **profile) as dst:
        dst.write(array, 1)

    # Build overviews then copy to final COG
    with rasterio.open(tmp_path, "r+") as dst:
        dst.build_overviews([2, 4, 8, 16, 32], rasterio.enums.Resampling.average)
        dst.update_tags(ns="rio_overview", resampling="average")

    from rasterio.shutil import copy as rio_copy
    rio_copy(tmp_path, output_path, driver="GTiff", copy_src_overviews=True,
             compress="deflate", tiled=True, blockxsize=512, blockysize=512)
    os.remove(tmp_path)
    print(f"Saved COG: {output_path}")


def export_monthly_flood(flood_mask_da, month_str, output_dir, crs, transform):
    """
    Export a single monthly flood extent mask as a COG.
    flood_mask_da: boolean or uint8 DataArray (1=flooded, 0=not flooded, 255=nodata)
    """
    arr = flood_mask_da.values.astype("uint8")
    profile = {
        "crs": crs,
        "transform": transform,
        "width": arr.shape[-1],
        "height": arr.shape[-2],
        "count": 1,
        "dtype": "uint8",
        "nodata": 255,
    }
    out_path = os.path.join(output_dir, f"flood_extent_{month_str}.tif")
    write_cog(arr, profile, out_path)
    return out_path
