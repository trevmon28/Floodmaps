import json
from pathlib import Path

def code_cell(source):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source}

def md_cell(source):
    return {"cell_type": "markdown", "metadata": {}, "source": source}

cells = []

# --- Header ---
cells.append(md_cell(
    "# Notebook 5 — Sampling Frame\n\n"
    "Joins monthly flood extent data to World Bank admin-3 boundaries and H3-7 hexagons.\n"
    "Outputs two GeoParquet tables suitable for phone-survey sampling frame design.\n\n"
    "**Provinces:** North Kivu, South Kivu, Ituri  \n"
    "**Period:** 2025-03 – 2026-02 (valid months only)  \n"
    "**Admin boundaries:** geoBoundaries (World Bank) COD ADM2  \n"
    "**Hex grid:** H3 resolution 7 (~5 km²)  \n"
    "**Cell towers:** OpenCelliD DRC (MCC=630) — requires API token"
))

# --- Setup ---
cells.append(code_cell(
    "from pathlib import Path\n"
    "import os\n\n"
    "def _find_project_root():\n"
    "    for candidate in [Path(os.path.abspath('')), Path(os.path.abspath('')).parent]:\n"
    "        if (candidate / 'config' / 'config.yaml').exists():\n"
    "            return candidate\n"
    "    raise FileNotFoundError('Cannot locate config/config.yaml. Run from project root or notebooks/.')\n\n"
    "PROJECT_ROOT = _find_project_root()\n"
    "os.chdir(PROJECT_ROOT)\n"
    "print('Project root:', PROJECT_ROOT)"
))

# --- Package check ---
cells.append(code_cell(
    "import importlib, subprocess, sys\n"
    "needed = ['geopandas', 'pandas', 'shapely', 'h3', 'requests', 'pyarrow', 'tqdm']\n"
    "missing = [p for p in needed if importlib.util.find_spec(p) is None]\n"
    "if missing:\n"
    "    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet'] + missing)\n"
    "    print(f'Installed: {missing}')\n"
    "else:\n"
    "    print('All packages present.')"
))

# --- Imports & config ---
cells.append(code_cell(
    "import json, warnings\n"
    "import requests\n"
    "import pandas as pd\n"
    "import geopandas as gpd\n"
    "import h3\n"
    "from shapely.geometry import shape, mapping, Polygon\n"
    "from tqdm import tqdm\n"
    "warnings.filterwarnings('ignore')\n\n"
    "OUTPUT_DIR  = Path('data/outputs/flood_extent')\n"
    "FRAMES_DIR  = Path('data/outputs/sampling_frames')\n"
    "FRAMES_DIR.mkdir(parents=True, exist_ok=True)\n\n"
    "PROVINCES   = ['North Kivu', 'Sud-Kivu', 'Ituri']   # geoBoundaries ADM1 name variants\n"
    "AOI_BBOX    = dict(min_lon=26.8, max_lon=30.8, min_lat=-5.9, max_lat=3.0)\n"
    "H3_RES      = 7\n"
    "BAD_MONTHS  = {'2025-01', '2025-02'}\n"
    "GAP_MONTHS  = {'2026-03', '2026-04'}\n\n"
    "print('Config ready.')"
))

# --- Section: Load flood data ---
cells.append(md_cell("## 1  Load flood data"))

cells.append(code_cell(
    "df = pd.read_csv(OUTPUT_DIR / 'flood_stats.csv', index_col='month').sort_index()\n"
    "df['quality'] = 'valid'\n"
    "df.loc[df.index.isin(BAD_MONTHS), 'quality'] = 'bad'\n"
    "df.loc[df.index.isin(GAP_MONTHS),  'quality'] = 'gap'\n"
    "valid_months = df[df['quality'] == 'valid'].index.tolist()\n\n"
    "flood_gdfs = {}\n"
    "for month in valid_months:\n"
    "    p = OUTPUT_DIR / f'flood_extent_{month}.geojson'\n"
    "    if p.exists():\n"
    "        flood_gdfs[month] = gpd.read_file(p)\n\n"
    "print(f'Loaded {len(flood_gdfs)} valid flood layers: {list(flood_gdfs.keys())}')"
))

# --- Section: World Bank admin boundaries ---
cells.append(md_cell(
    "## 2  World Bank admin-3 boundaries (geoBoundaries)\n\n"
    "Downloads DRC ADM1 (provinces) and ADM2 (territories) from the geoBoundaries API, "
    "which is the open boundary dataset used by the World Bank and humanitarian organisations."
))

cells.append(code_cell(
    "def fetch_geoboundaries(iso3, level, cache_dir=Path('data/raw/boundaries')):\n"
    "    cache_dir.mkdir(parents=True, exist_ok=True)\n"
    "    cache_file = cache_dir / f'{iso3}_{level}.geojson'\n"
    "    if cache_file.exists():\n"
    "        print(f'  Using cached {cache_file}')\n"
    "        return gpd.read_file(cache_file)\n"
    "    url = f'https://www.geoboundaries.org/api/current/gbOpen/{iso3}/{level}/'\n"
    "    meta = requests.get(url, timeout=30).json()\n"
    "    dl_url = meta['gjDownloadURL']\n"
    "    print(f'  Downloading {iso3} {level} from geoBoundaries...')\n"
    "    gdf = gpd.read_file(dl_url)\n"
    "    gdf.to_file(cache_file, driver='GeoJSON')\n"
    "    print(f'  Cached to {cache_file}')\n"
    "    return gdf\n\n"
    "print('Fetching ADM1 (provinces)...')\n"
    "adm1 = fetch_geoboundaries('COD', 'ADM1')\n"
    "print(f'  ADM1 columns: {list(adm1.columns)}')\n"
    "print(adm1[['shapeName']].drop_duplicates().head(10).to_string())"
))

cells.append(code_cell(
    "# Filter ADM1 to our three provinces (match on name containing key terms)\n"
    "prov_mask = adm1['shapeName'].str.contains('Kivu|Ituri', case=False, na=False)\n"
    "target_provs = adm1[prov_mask]\n"
    "print('Target provinces found:')\n"
    "print(target_provs[['shapeName']].to_string())"
))

cells.append(code_cell(
    "print('Fetching ADM2 (territories / admin-3)...')\n"
    "adm2 = fetch_geoboundaries('COD', 'ADM2')\n"
    "print(f'  Total ADM2 features: {len(adm2)}')\n\n"
    "# Spatial filter: keep only territories within our three provinces\n"
    "prov_union = target_provs.dissolve().geometry.iloc[0]\n"
    "adm2_aoi = adm2[adm2.geometry.intersects(prov_union)].copy()\n"
    "adm2_aoi = adm2_aoi.to_crs('EPSG:4326')\n"
    "print(f'  ADM2 territories in AOI: {len(adm2_aoi)}')\n"
    "print(adm2_aoi[['shapeName', 'shapeISO']].head(10).to_string())"
))

# --- Section: H3-7 hex grid ---
cells.append(md_cell("## 3  H3-7 hexagon grid"))

cells.append(code_cell(
    "# Generate H3-7 hexagons covering the AOI bounding box\n"
    "aoi_poly = {\n"
    "    'type': 'Polygon',\n"
    "    'coordinates': [[\n"
    "        [AOI_BBOX['min_lon'], AOI_BBOX['min_lat']],\n"
    "        [AOI_BBOX['max_lon'], AOI_BBOX['min_lat']],\n"
    "        [AOI_BBOX['max_lon'], AOI_BBOX['max_lat']],\n"
    "        [AOI_BBOX['min_lon'], AOI_BBOX['max_lat']],\n"
    "        [AOI_BBOX['min_lon'], AOI_BBOX['min_lat']],\n"
    "    ]]\n"
    "}\n\n"
    "hex_ids = list(h3.polyfill_geojson(aoi_poly, H3_RES))\n"
    "print(f'H3-7 hexagons in bounding box: {len(hex_ids)}')\n\n"
    "# Clip to provinces union\n"
    "def h3_to_polygon(h):\n"
    "    coords = h3.h3_to_geo_boundary(h, geo_json=True)\n"
    "    return Polygon(coords)\n\n"
    "hex_gdf = gpd.GeoDataFrame(\n"
    "    {'h3_index': hex_ids},\n"
    "    geometry=[h3_to_polygon(h) for h in hex_ids],\n"
    "    crs='EPSG:4326'\n"
    ")\n"
    "hex_gdf = hex_gdf[hex_gdf.geometry.intersects(prov_union)].copy()\n"
    "print(f'H3-7 hexagons clipped to provinces: {len(hex_gdf)}')"
))

# --- Section: Spatial join flood → admin-3 ---
cells.append(md_cell("## 4  Spatial join: flood extent → admin-3"))

cells.append(code_cell(
    "admin3_rows = []\n\n"
    "for month, gdf in tqdm(flood_gdfs.items(), desc='Admin-3 join'):\n"
    "    if gdf.empty:\n"
    "        continue\n"
    "    gdf = gdf.to_crs('EPSG:4326')\n"
    "    joined = gpd.overlay(adm2_aoi[['shapeName', 'shapeISO', 'geometry']], gdf, how='intersection')\n"
    "    if joined.empty:\n"
    "        continue\n"
    "    joined = joined.to_crs('EPSG:32735')  # UTM 35S for area calc\n"
    "    joined['flood_area_km2'] = joined.geometry.area / 1e6\n"
    "    for _, row in adm2_aoi.iterrows():\n"
    "        terr_area = row.geometry.to_crs('EPSG:32735').area / 1e6 if hasattr(row.geometry, 'to_crs') else 0\n"
    "        terr_flood = joined[joined['shapeName'] == row['shapeName']]['flood_area_km2'].sum()\n"
    "        admin3_rows.append({\n"
    "            'month': month,\n"
    "            'shapeName': row['shapeName'],\n"
    "            'shapeISO': row.get('shapeISO', ''),\n"
    "            'flood_area_km2': round(terr_flood, 3),\n"
    "            'quality': df.loc[month, 'quality'] if month in df.index else 'valid',\n"
    "        })\n\n"
    "admin3_df = pd.DataFrame(admin3_rows)\n"
    "admin3_gdf = adm2_aoi[['shapeName', 'shapeISO', 'geometry']].merge(admin3_df, on=['shapeName', 'shapeISO'], how='left')\n"
    "print(f'Admin-3 rows: {len(admin3_df)}')\n"
    "print(admin3_df[admin3_df['flood_area_km2'] > 0].head(10).to_string())"
))

# --- Section: Spatial join flood → H3-7 ---
cells.append(md_cell("## 5  Spatial join: flood extent → H3-7"))

cells.append(code_cell(
    "h3_rows = []\n\n"
    "for month, gdf in tqdm(flood_gdfs.items(), desc='H3-7 join'):\n"
    "    if gdf.empty:\n"
    "        continue\n"
    "    gdf = gdf.to_crs('EPSG:4326')\n"
    "    joined = gpd.overlay(hex_gdf[['h3_index', 'geometry']], gdf, how='intersection')\n"
    "    if joined.empty:\n"
    "        continue\n"
    "    joined = joined.to_crs('EPSG:32735')\n"
    "    joined['flood_area_km2'] = joined.geometry.area / 1e6\n"
    "    flood_by_hex = joined.groupby('h3_index')['flood_area_km2'].sum().reset_index()\n"
    "    flood_by_hex['month'] = month\n"
    "    flood_by_hex['quality'] = df.loc[month, 'quality'] if month in df.index else 'valid'\n"
    "    h3_rows.append(flood_by_hex)\n\n"
    "h3_df = pd.concat(h3_rows, ignore_index=True) if h3_rows else pd.DataFrame()\n"
    "h3_gdf = hex_gdf.merge(h3_df, on='h3_index', how='left')\n"
    "print(f'H3-7 rows: {len(h3_df)}')\n"
    "print(h3_df[h3_df['flood_area_km2'] > 0].head(10).to_string())"
))

# --- Section: OpenCelliD ---
cells.append(md_cell(
    "## 6  Cell tower locations (OpenCelliD)\n\n"
    "Register at [opencellid.org](https://opencellid.org) to get a free API token.  \n"
    "Set `OPENCELLID_TOKEN` below and re-run this cell to download DRC towers (MCC=630)."
))

cells.append(code_cell(
    "OPENCELLID_TOKEN = ''  # <-- paste your token here\n\n"
    "towers_gdf = None\n\n"
    "if OPENCELLID_TOKEN:\n"
    "    import io\n"
    "    tower_cache = Path('data/raw/opencellid_cod.csv')\n"
    "    if not tower_cache.exists():\n"
    "        print('Downloading DRC cell towers from OpenCelliD...')\n"
    "        url = f'https://opencellid.org/ocid/downloads?token={OPENCELLID_TOKEN}&type=mcc&file=630.csv.gz'\n"
    "        r = requests.get(url, stream=True, timeout=120)\n"
    "        tower_cache.parent.mkdir(parents=True, exist_ok=True)\n"
    "        with open(tower_cache.with_suffix('.csv.gz'), 'wb') as f:\n"
    "            for chunk in r.iter_content(chunk_size=8192):\n"
    "                f.write(chunk)\n"
    "        import gzip, shutil\n"
    "        with gzip.open(tower_cache.with_suffix('.csv.gz'), 'rb') as f_in:\n"
    "            with open(tower_cache, 'wb') as f_out:\n"
    "                shutil.copyfileobj(f_in, f_out)\n"
    "        print(f'  Saved to {tower_cache}')\n"
    "    towers_raw = pd.read_csv(tower_cache,\n"
    "        names=['radio','mcc','net','area','cell','unit','lon','lat','range','samples',\n"
    "               'changeable','created','updated','averageSignal'])\n"
    "    towers_raw = towers_raw[(towers_raw.lat.between(AOI_BBOX['min_lat'], AOI_BBOX['max_lat'])) &\n"
    "                            (towers_raw.lon.between(AOI_BBOX['min_lon'], AOI_BBOX['max_lon']))]\n"
    "    towers_gdf = gpd.GeoDataFrame(towers_raw,\n"
    "        geometry=gpd.points_from_xy(towers_raw.lon, towers_raw.lat), crs='EPSG:4326')\n"
    "    print(f'  Towers in AOI: {len(towers_gdf)}')\n\n"
    "    # Join tower counts to admin-3\n"
    "    t_admin = gpd.sjoin(towers_gdf[['radio','geometry']], adm2_aoi[['shapeName','geometry']], how='left', predicate='within')\n"
    "    tower_counts = t_admin.groupby('shapeName').size().reset_index(name='tower_count')\n"
    "    admin3_gdf = admin3_gdf.merge(tower_counts, on='shapeName', how='left')\n"
    "    admin3_gdf['tower_count'] = admin3_gdf['tower_count'].fillna(0).astype(int)\n\n"
    "    # Join tower counts to H3-7\n"
    "    t_hex = gpd.sjoin(towers_gdf[['radio','geometry']], hex_gdf[['h3_index','geometry']], how='left', predicate='within')\n"
    "    hex_tower = t_hex.groupby('h3_index').size().reset_index(name='tower_count')\n"
    "    h3_gdf = h3_gdf.merge(hex_tower, on='h3_index', how='left')\n"
    "    h3_gdf['tower_count'] = h3_gdf['tower_count'].fillna(0).astype(int)\n"
    "    print('Tower counts joined to admin-3 and H3-7.')\n"
    "else:\n"
    "    print('No OpenCelliD token set — skipping tower data. Set OPENCELLID_TOKEN and re-run.')"
))

# --- Section: Export ---
cells.append(md_cell("## 7  Export GeoParquet"))

cells.append(code_cell(
    "admin3_out = FRAMES_DIR / 'admin3.parquet'\n"
    "h3_out     = FRAMES_DIR / 'h3_7.parquet'\n\n"
    "admin3_gdf.to_parquet(admin3_out, index=False)\n"
    "h3_gdf.to_parquet(h3_out, index=False)\n\n"
    "print(f'Exported admin3.parquet  ({len(admin3_gdf):,} rows) -> {admin3_out}')\n"
    "print(f'Exported h3_7.parquet    ({len(h3_gdf):,} rows)  -> {h3_out}')"
))

# --- Section: Summary ---
cells.append(md_cell("## 8  Summary"))

cells.append(code_cell(
    "print('=== Sampling Frame Summary ===')\n"
    "print(f'Admin-3 territories in AOI : {adm2_aoi.shapeName.nunique()}')\n"
    "print(f'H3-7 hexagons in AOI       : {hex_gdf.h3_index.nunique()}')\n"
    "print(f'Valid flood months         : {len(flood_gdfs)}')\n"
    "if towers_gdf is not None:\n"
    "    print(f'Cell towers in AOI         : {len(towers_gdf)}')\n"
    "else:\n"
    "    print('Cell towers                : not loaded (no token)')\n"
    "print()\n"
    "print('Top 10 territories by peak flood area:')\n"
    "peak = admin3_df.groupby('shapeName')['flood_area_km2'].max().sort_values(ascending=False).head(10)\n"
    "print(peak.to_string())"
))

# --- Build notebook ---
nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python (gis_project_env)", "language": "python", "name": "gis_project_env"},
        "language_info": {"name": "python", "version": "3.14.4"}
    },
    "cells": cells
}

out = Path(r'c:\Users\trevm\Projects\Floodmaps\notebooks\05_sampling_frame.ipynb')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print(f'Written: {out}')
