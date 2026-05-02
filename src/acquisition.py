"""
Data discovery and download via STAC for Sentinel-1 and Sentinel-2.
"""
import yaml
import pystac_client
import stackstac
import geopandas as gpd
from shapely.geometry import box
import pandas as pd


def load_config(path="config/config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def get_aoi_geometry(cfg):
    b = cfg["aoi"]["bbox"]
    return box(b["west"], b["south"], b["east"], b["north"])


def search_sentinel1(cfg, start, end):
    # Element84 Earth Search — free, no API key required
    catalog = pystac_client.Client.open(cfg["data_sources"]["sar"]["catalog"])
    aoi = get_aoi_geometry(cfg)
    results = catalog.search(
        collections=[cfg["data_sources"]["sar"]["collection"]],
        intersects=aoi.__geo_interface__,
        datetime=f"{start}/{end}",
    )
    items = list(results.items())
    print(f"Found {len(items)} Sentinel-1 scenes ({start} to {end})")
    return items


def search_sentinel2(cfg, start, end):
    # Element84 Earth Search — free, no API key required
    catalog = pystac_client.Client.open(cfg["data_sources"]["optical"]["catalog"])
    aoi = get_aoi_geometry(cfg)
    results = catalog.search(
        collections=[cfg["data_sources"]["optical"]["collection"]],
        intersects=aoi.__geo_interface__,
        datetime=f"{start}/{end}",
        query={"eo:cloud_cover": {"lt": cfg["data_sources"]["optical"]["max_cloud_cover"]}},
    )
    items = list(results.items())
    print(f"Found {len(items)} Sentinel-2 scenes under cloud threshold ({start} to {end})")
    return items


def monthly_date_ranges(cfg):
    start = pd.Timestamp(cfg["temporal"]["start"])
    end = pd.Timestamp(cfg["temporal"]["end"])
    months = pd.date_range(start, end, freq="MS")
    return [(str(m.date()), str((m + pd.offsets.MonthEnd(1)).date())) for m in months]
