"""
Assembles the researcher handover package into data/handover/
"""
import shutil, json, csv
from pathlib import Path

ROOT       = Path(r'c:\Users\trevm\Projects\Floodmaps')
OUT        = ROOT / 'data' / 'handover'
FLOOD_DIR  = ROOT / 'data' / 'outputs' / 'flood_extent'
FRAMES_DIR = ROOT / 'data' / 'outputs' / 'sampling_frames'
DOCS_DIR   = ROOT / 'docs'

BAD_MONTHS = {'2025-01', '2025-02'}
GAP_MONTHS = {'2026-03', '2026-04'}

# Clean and create output folders
if OUT.exists():
    shutil.rmtree(OUT)
for sub in ['flood_extents', 'sampling_frames', 'maps']:
    (OUT / sub).mkdir(parents=True)

# 1. Valid GeoJSON flood extents
copied_geojson = []
for f in sorted(FLOOD_DIR.glob('flood_extent_????-??.geojson')):
    month = f.stem.replace('flood_extent_', '')
    if month in BAD_MONTHS:
        continue
    shutil.copy(f, OUT / 'flood_extents' / f.name)
    copied_geojson.append(month)

# 2. flood_stats.csv (valid months only, with quality flag)
stats_src = FLOOD_DIR / 'flood_stats.csv'
stats_out = OUT / 'flood_stats.csv'
rows = []
with open(stats_src) as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames + ['quality']
    for row in reader:
        m = row['month']
        row['quality'] = 'bad' if m in BAD_MONTHS else 'gap' if m in GAP_MONTHS else 'valid'
        if m not in BAD_MONTHS:
            rows.append(row)
with open(stats_out, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

# 3. Sampling frame GeoParquets
for name in ['admin3.parquet', 'h3_7.parquet']:
    src = FRAMES_DIR / name
    if src.exists():
        shutil.copy(src, OUT / 'sampling_frames' / name)

# 4. Interactive HTML maps
for name in ['flood_map_interactive.html', 'flood_sampling_map.html']:
    src = DOCS_DIR / name
    if src.exists():
        shutil.copy(src, OUT / 'maps' / name)

# 5. README
readme = """\
# Eastern DRC Flood Mapping — Researcher Handover
**Date:** 2026-05-19
**Contact:** Trevor Monroe
**AOI:** North Kivu, South Kivu, Ituri (Eastern DRC)
**Period:** March 2025 – February 2026 (14 valid months)
**Method:** Sentinel-1 SAR change detection (−3 dB threshold, 100 m resolution)

---

## Files

### flood_extents/
Monthly flood extent polygons in GeoJSON format (WGS84 / EPSG:4326).
One file per valid month: `flood_extent_YYYY-MM.geojson`

Each feature has one property:
- `month` — the month of the flood detection (YYYY-MM)

**Load in Python:**
```python
import geopandas as gpd
gdf = gpd.read_file("flood_extents/flood_extent_2025-09.geojson")
```

**Load in QGIS / ArcGIS:** Drag and drop the .geojson file directly.

**Check if a point was flooded:**
```python
from shapely.geometry import Point
point = Point(29.23, -3.38)  # lon, lat
flooded = gdf[gdf.geometry.contains(point)]
print("Flooded" if len(flooded) else "Not flooded")
```

---

### flood_stats.csv
Monthly summary table with columns:
- `month` — YYYY-MM
- `flood_area_km2` — total flooded area in km²
- `flooded_pct` — percentage of AOI flooded
- `quality` — `valid` | `gap` (no satellite coverage)

---

### sampling_frames/
GeoParquet tables joining flood data to administrative boundaries and H3-7 hexagons.
Suitable for phone-survey sampling frame design.

**admin3.parquet** — one row per territory per month
- `shapeName` — territory name
- `shapeISO` — ISO code
- `flood_area_km2` — flooded area within territory
- `quality` — data quality flag
- `geometry` — territory polygon

**h3_7.parquet** — one row per H3-7 hexagon (~5 km²) per month
- `h3_index` — H3 cell identifier
- `flood_area_km2` — flooded area within hex
- `quality` — data quality flag
- `geometry` — hexagon polygon

**Load in Python:**
```python
import geopandas as gpd
admin3 = gpd.read_parquet("sampling_frames/admin3.parquet")
h3_7   = gpd.read_parquet("sampling_frames/h3_7.parquet")
```

---

### maps/
Interactive HTML maps — open in any web browser, no internet required.

**flood_map_interactive.html**
Monthly flood extents with layer toggle. Use the panel on the right to switch months.

**flood_sampling_map.html**
Flood extents + admin-3 territory boundaries coloured by peak flood area.
H3-7 hex grid available as a toggle layer (off by default).

**To view:** Double-click the .html file — it opens in your browser.
No installation needed.

---

## Data quality notes

| Month | Status | Reason |
|-------|--------|--------|
| 2025-01 | EXCLUDED | Uncalibrated amplitude data |
| 2025-02 | EXCLUDED | Uncalibrated amplitude data |
| 2026-03 | gap | Insufficient S1 satellite coverage (<5 MB source) |
| 2026-04 | gap | Insufficient S1 satellite coverage (<5 MB source) |
| All others | valid | Calibrated sigma₀ dB, quality masks applied |

## Peak flood event
September 2025: **3,428 km²** — dominant signal consistent with short rains season
in South Kivu. Verify against OCHA/ReliefWeb DRC situation reports for Sep–Oct 2025.

---

## Software requirements (Python users)
```
geopandas>=0.14
pyarrow>=14
shapely>=2.0
folium>=0.15      # only needed to re-render maps
h3>=4.0           # only needed for H3 hex queries
```
"""

(OUT / 'README.md').write_text(readme, encoding='utf-8')

# Summary
print("=== Handover package built ===")
print(f"Location: {OUT}")
print(f"  flood_extents/   {len(copied_geojson)} GeoJSONs: {copied_geojson}")
for name in ['admin3.parquet', 'h3_7.parquet']:
    exists = (OUT / 'sampling_frames' / name).exists()
    print(f"  sampling_frames/{name}  {'OK' if exists else 'MISSING'}")
for name in ['flood_map_interactive.html', 'flood_sampling_map.html']:
    exists = (OUT / 'maps' / name).exists()
    print(f"  maps/{name}  {'OK' if exists else 'MISSING'}")
print(f"  flood_stats.csv  {len(rows)} rows")
print(f"  README.md")
print()

# Zip it up
zip_path = ROOT / 'data' / 'eastern_drc_flood_data'
shutil.make_archive(str(zip_path), 'zip', OUT)
print(f"Zipped: {zip_path}.zip  ({(zip_path.with_suffix('.zip')).stat().st_size / 1e6:.1f} MB)")
