"""
SAR preprocessing: speckle filtering, terrain correction, dB conversion.
Optical preprocessing: cloud masking, MNDWI computation.
"""
import numpy as np
import xarray as xr
from scipy.ndimage import uniform_filter, variance


def to_db(backscatter):
    """Convert linear backscatter to dB."""
    return 10 * np.log10(np.where(backscatter > 0, backscatter, np.nan))


def lee_filter(da, size=7):
    """Lee speckle filter applied per spatial window."""
    img = da.values.astype("float64")
    img_mean = uniform_filter(img, size)
    img_sq_mean = uniform_filter(img ** 2, size)
    img_var = img_sq_mean - img_mean ** 2
    overall_var = np.nanvar(img)
    weights = img_var / (img_var + overall_var + 1e-10)
    filtered = img_mean + weights * (img - img_mean)
    return xr.DataArray(filtered, coords=da.coords, dims=da.dims, attrs=da.attrs)


def compute_mndwi(green, swir):
    """Modified NDWI — positive values indicate water."""
    return (green - swir) / (green + swir + 1e-9)


def mask_clouds_s2(ds):
    """Apply Sentinel-2 SCL cloud mask (bands 8/9/10 = cloud shadow/medium/high)."""
    scl = ds["SCL"]
    cloud_mask = scl.isin([8, 9, 10, 3])  # cloud shadow, med cloud, high cloud, dark pixels
    return ds.where(~cloud_mask)
