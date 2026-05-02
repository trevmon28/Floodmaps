"""
run_pipeline.py — Non-interactive end-to-end pipeline runner.

Runs all processing steps without opening Jupyter.
Use this to regenerate outputs for a new month or full reprocessing run.

Usage:
    python run_pipeline.py                        # full pipeline
    python run_pipeline.py --month 2025-06        # single month only
    python run_pipeline.py --step preprocess      # single step only

Steps: acquire | preprocess | detect | composite | export
"""
import os
import yaml
import argparse
import numpy as np
import rasterio
from rasterio.shutil import copy as rio_copy
import pystac_client
import stackstac
import pandas as pd
from shapely.geometry import box
from scipy.ndimage import uniform_filter
import warnings
warnings.filterwarnings('ignore')


def load_config(path='config/config.yaml'):
    with open(path) as f:
        return yaml.safe_load(f)


def monthly_date_ranges(cfg):
    start = pd.Timestamp(cfg['temporal']['start'])
    end = pd.Timestamp(cfg['temporal']['end'])
    months = pd.date_range(start, end, freq='MS')
    return [(str(m.date()), str((m + pd.offsets.MonthEnd(1)).date())) for m in months]


def to_db(arr):
    return 10 * np.log10(np.where(arr > 0, arr, np.nan))


def lee_filter(arr, size=7):
    img = arr.astype('float64')
    img_mean = uniform_filter(img, size)
    img_sq_mean = uniform_filter(img ** 2, size)
    img_var = img_sq_mean - img_mean ** 2
    overall_var = np.nanvar(img)
    weights = img_var / (img_var + overall_var + 1e-10)
    return img_mean + weights * (img - img_mean)


def write_cog(array, profile, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tmp = output_path + '.tmp.tif'
    profile.update(driver='GTiff', compress='deflate', tiled=True,
                   blockxsize=512, blockysize=512, dtype='float32', count=1)
    with rasterio.open(tmp, 'w', **profile) as dst:
        dst.write(array.astype('float32'), 1)
    with rasterio.open(tmp, 'r+') as dst:
        dst.build_overviews([2, 4, 8, 16], rasterio.enums.Resampling.average)
        dst.update_tags(ns='rio_overview', resampling='average')
    rio_copy(tmp, output_path, driver='GTiff', copy_src_overviews=True,
             compress='deflate', tiled=True, blockxsize=512, blockysize=512)
    os.remove(tmp)
    print(f'  Saved: {output_path}')


def step_preprocess(cfg, months=None):
    print('\n=== STEP: Preprocessing ===')
    b = cfg['aoi']['bbox']
    bbox = [b['west'], b['south'], b['east'], b['north']]
    output_crs = cfg['aoi']['output_crs']
    processed_dir = 'data/processed/sar'
    os.makedirs(processed_dir, exist_ok=True)

    catalog = pystac_client.Client.open(cfg['data_sources']['sar']['catalog'])
    date_ranges = months or monthly_date_ranges(cfg)

    for start, end in date_ranges:
        month_str = start[:7]
        out_vv = f'{processed_dir}/{month_str}_VV.tif'
        out_vh = f'{processed_dir}/{month_str}_VH.tif'

        if os.path.exists(out_vv) and os.path.exists(out_vh):
            print(f'  {month_str} already processed — skipping')
            continue

        print(f'  Processing {month_str}...')
        results = catalog.search(
            collections=[cfg['data_sources']['sar']['collection']],
            bbox=bbox,
            datetime=f'{start}/{end}',
        )
        items = list(results.items())
        if not items:
            print(f'  No scenes for {month_str} — skipping')
            continue

        stack = stackstac.stack(
            items, assets=['vv', 'vh'], bounds_latlon=bbox,
            epsg=int(output_crs.split(':')[1]), resolution=20, dtype='float64',
            rescale=False,
        )
        composite = stack.median(dim='time').compute()

        for band_name, band_idx in [('VV', 0), ('VH', 1)]:
            arr = composite.isel(band=band_idx).values
            arr = lee_filter(arr)
            arr = to_db(arr)
            profile = {
                'crs': output_crs,
                'transform': composite.rio.transform(),
                'width': arr.shape[1],
                'height': arr.shape[0],
                'nodata': float('nan'),
            }
            write_cog(arr, profile, f'{processed_dir}/{month_str}_{band_name}.tif')

    # Build baseline
    baseline_path = f'{processed_dir}/baseline_VV.tif'
    if not os.path.exists(baseline_path):
        n = cfg['processing']['baseline_months']
        files = sorted([f for f in os.listdir(processed_dir) if f.endswith('_VV.tif')])[:n]
        if len(files) == n:
            arrays, profile = [], None
            for fname in files:
                with rasterio.open(f'{processed_dir}/{fname}') as src:
                    arrays.append(src.read(1).astype('float32'))
                    profile = profile or src.profile.copy()
            baseline = np.nanmedian(np.stack(arrays), axis=0)
            write_cog(baseline, profile, baseline_path)
            print(f'  Baseline saved: {baseline_path}')


def step_detect(cfg):
    print('\n=== STEP: Flood Detection ===')
    from skimage.filters import threshold_otsu
    processed_dir = 'data/processed/sar'
    output_dir = 'data/outputs/flood_extent'
    os.makedirs(output_dir, exist_ok=True)

    baseline_path = f'{processed_dir}/baseline_VV.tif'
    if not os.path.exists(baseline_path):
        print('  Baseline not found — run preprocess step first')
        return

    with rasterio.open(baseline_path) as src:
        baseline = src.read(1).astype('float32')
        profile = src.profile.copy()

    vv_files = sorted([f for f in os.listdir(processed_dir)
                       if f.endswith('_VV.tif') and 'baseline' not in f])

    for fname in vv_files:
        month_str = fname[:7]
        out_path = f'{output_dir}/flood_extent_{month_str}.tif'
        if os.path.exists(out_path):
            print(f'  {month_str} already exists — skipping')
            continue

        with rasterio.open(f'{processed_dir}/{fname}') as src:
            vv = src.read(1).astype('float32')

        change = vv - baseline
        flood_mask = (change < -3.0).astype('uint8')  # >3 dB drop = flood
        flood_mask[~np.isfinite(vv)] = 255             # nodata

        out_profile = profile.copy()
        out_profile.update(dtype='uint8', nodata=255)
        write_cog(flood_mask, out_profile, out_path)
        flooded_pct = (flood_mask == 1).sum() / (flood_mask != 255).sum() * 100
        print(f'  {month_str}: {flooded_pct:.1f}% of AOI flagged as flooded')


def main():
    parser = argparse.ArgumentParser(description='DRC Flood Mapping Pipeline')
    parser.add_argument('--step', choices=['preprocess', 'detect', 'all'], default='all')
    parser.add_argument('--month', type=str, default=None,
                        help='Process single month e.g. 2025-06')
    args = parser.parse_args()

    cfg = load_config()
    print(f'Pipeline: {cfg["project"]["name"]}')
    print(f'AOI: {cfg["aoi"]["name"]}')

    months = None
    if args.month:
        start = pd.Timestamp(args.month)
        end = start + pd.offsets.MonthEnd(1)
        months = [(str(start.date()), str(end.date()))]
        print(f'Single month mode: {months[0]}')

    if args.step in ('preprocess', 'all'):
        step_preprocess(cfg, months)
    if args.step in ('detect', 'all'):
        step_detect(cfg)

    print('\nPipeline complete.')


if __name__ == '__main__':
    main()
