"""
Flood detection using SAR change detection and Otsu thresholding.
"""
import numpy as np
import xarray as xr
from skimage.filters import threshold_otsu


def build_baseline(sar_stack, n_months=3):
    """
    Compute median backscatter baseline from first n_months of the stack.
    Stack should be a DataArray with a 'time' dimension.
    """
    baseline_period = sar_stack.isel(time=slice(0, n_months))
    return baseline_period.median(dim="time")


def detect_flood_sar(sar_image, baseline, threshold_db=-3.0):
    """
    Flag pixels where backscatter dropped > threshold_db below baseline.
    Flood = significant decrease in backscatter (water absorbs SAR signal).
    Returns boolean DataArray: True = flooded.
    """
    change = sar_image - baseline
    return change < threshold_db


def otsu_water_mask(sar_image_db):
    """
    Otsu thresholding on dB image to separate water from land.
    Water has low backscatter; land has higher backscatter.
    Returns boolean DataArray: True = water/flooded.
    """
    valid = sar_image_db.values[np.isfinite(sar_image_db.values)]
    if len(valid) == 0:
        return xr.full_like(sar_image_db, False, dtype=bool)
    threshold = threshold_otsu(valid)
    return sar_image_db < threshold


def combine_flood_masks(sar_mask, optical_mask=None):
    """
    Combine SAR and optical flood masks where both are available.
    Uses SAR as primary; optical confirms where cloud-free.
    """
    if optical_mask is None:
        return sar_mask
    return sar_mask | optical_mask


def mask_terrain_artifacts(flood_mask, slope_threshold_deg=5.0, slope_da=None):
    """
    Remove SAR layover/shadow artifacts in steep terrain.
    Pixels with slope > threshold are unreliable and should be masked out.
    """
    if slope_da is None:
        return flood_mask
    return flood_mask.where(slope_da <= slope_threshold_deg, other=False)
