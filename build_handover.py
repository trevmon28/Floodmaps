"""
Assembles the researcher handover package into data/handover/
"""
import shutil, json, csv, warnings
from pathlib import Path

import pandas as pd

try:
    import geopandas as gpd
    _GPD_AVAILABLE = True
except ImportError:
    _GPD_AVAILABLE = False

ROOT       = Path(r'c:\Users\trevm\Projects\Floodmaps')
OUT        = ROOT / 'data' / 'handover'
FLOOD_DIR  = ROOT / 'data' / 'outputs' / 'flood_extent'
FRAMES_DIR = ROOT / 'data' / 'outputs' / 'sampling_frames'
DOCS_DIR   = ROOT / 'docs'

BAD_MONTHS = {'2025-01', '2025-02'}
# 2026-03/04 were recovered via MPC RTC (2026-07-10) and 2026-06 on 2026-09-08;
# no month is a gap any more. Kept as a fallback for CSVs without a quality column.
GAP_MONTHS = set()

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
    has_quality = 'quality' in (reader.fieldnames or [])
    fieldnames = reader.fieldnames if has_quality else reader.fieldnames + ['quality']
    for row in reader:
        m = row['month']
        # flood_stats.csv carries its own quality flag; only derive one if absent.
        if not row.get('quality'):
            row['quality'] = 'bad' if m in BAD_MONTHS else 'gap' if m in GAP_MONTHS else 'valid'
        if row['quality'] != 'bad':
            rows.append(row)
with open(stats_out, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

# 3. Sampling frame GeoParquets + CSV exports
for name in ['admin2.parquet', 'admin3.parquet', 'h3_7.parquet']:
    src = FRAMES_DIR / name
    if src.exists():
        shutil.copy(src, OUT / 'sampling_frames' / name)

# 3b. CSV versions of sampling frames (long + wide)
csv_dir = OUT / 'csv'
csv_dir.mkdir(exist_ok=True)

for frame_name, unit_col in [('admin2', 'shapeName'), ('admin3', 'admin3Name'),
                               ('h3_7', 'h3_index')]:
    parquet_path = FRAMES_DIR / f'{frame_name}.parquet'
    if not parquet_path.exists() or not _GPD_AVAILABLE:
        continue
    warnings.filterwarnings('ignore')
    gdf = gpd.read_parquet(parquet_path)
    df  = pd.DataFrame(gdf.drop(columns=['geometry'], errors='ignore'))

    # Long format
    df.to_csv(csv_dir / f'{frame_name}_flood.csv', index=False)

    # Wide format (months as columns)
    if 'month' in df.columns and unit_col in df.columns and 'flood_area_km2' in df.columns:
        wide = df.pivot_table(index=unit_col, columns='month',
                              values='flood_area_km2', aggfunc='sum').reset_index()
        wide.to_csv(csv_dir / f'{frame_name}_flood_wide.csv', index=False)

# 3c. Admin-3 summary exposure statistics (for survey design stratification)
admin3_parquet = FRAMES_DIR / 'admin3.parquet'
if admin3_parquet.exists() and _GPD_AVAILABLE:
    warnings.filterwarnings('ignore')
    gdf3  = gpd.read_parquet(admin3_parquet)
    df3   = pd.DataFrame(gdf3.drop(columns=['geometry'], errors='ignore'))

    valid_df3 = df3[~df3.get('month', pd.Series()).isin(BAD_MONTHS | GAP_MONTHS)]

    unit3 = 'admin3Name' if 'admin3Name' in df3.columns else 'shapeName'
    if unit3 in df3.columns and 'flood_area_km2' in df3.columns:
        summary = valid_df3.groupby(unit3).agg(
            peak_flood_km2   =('flood_area_km2', 'max'),
            mean_flood_km2   =('flood_area_km2', 'mean'),
            months_exposed_10km2=('flood_area_km2', lambda x: (x >= 10).sum()),
        ).reset_index()
        # Percentage-flooded alternative threshold (>5% area) if flooded_pct present
        if 'flooded_pct' in df3.columns:
            pct_exposed = valid_df3.groupby(unit3)['flooded_pct'].apply(
                lambda x: (x >= 5).sum()
            ).reset_index(name='months_exposed_5pct')
            summary = summary.merge(pct_exposed, on=unit3, how='left')
        summary.to_csv(csv_dir / 'admin3_flood_summary.csv', index=False)
        print(f"  admin3_flood_summary.csv  {len(summary)} Admin-3 units")

# Flood centroids CSV
centroid_path = FLOOD_DIR / 'flood_centroids.csv'
if centroid_path.exists():
    shutil.copy(centroid_path, csv_dir / 'flood_centroids.csv')

# 4. Interactive HTML maps
for name in ['flood_map_interactive.html', 'flood_sampling_map.html']:
    src = DOCS_DIR / name
    if src.exists():
        shutil.copy(src, OUT / 'maps' / name)

# 5. README
readme = """\
# Eastern DRC Flood Mapping — Researcher Handover
**Date:** 2026-09-09
**Contact:** Trevor Monroe
**AOI:** North Kivu, South Kivu, Ituri (Eastern DRC)
**Period:** January 2025 – July 2026 (19 months, 17 valid, no gaps)
**Method:** Sentinel-1 SAR change detection (Otsu adaptive / fixed −5 dB threshold, 100 m resolution)
**License:** CC-BY 4.0 — see LICENSE in repository root

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
- `quality` — `valid` (all delivered months; `bad` months are excluded from this package)

### csv/admin3_flood_summary.csv
One row per Admin-3 unit — recommended for MSNA survey stratification:
- `admin3Name` — secteur/chefferie name
- `peak_flood_km2` — maximum single-month flood area (all valid months)
- `mean_flood_km2` — mean flood area across valid months
- `months_exposed_10km2` — count of valid months with ≥10 km² flooded
- `months_exposed_5pct` — count of valid months with ≥5% of unit area flooded

### csv/admin3_flood.csv / admin3_flood_wide.csv
Long-format and wide-format monthly flood tables per Admin-3 unit.

---

### sampling_frames/
GeoParquet tables joining flood data to administrative boundaries and H3-7 hexagons.
Suitable for phone-survey sampling frame design.

**admin3.parquet** — one row per territory per month
- `admin3Name` — territory name
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
| All others | valid | Calibrated sigma₀ dB, quality masks applied |

### Comparing months
Monthly SAR coverage ranges from 0.9% to 50.5% of the AOI bounding box, and different
months image **different places** — no pixel is covered in all 19 months. Reported
`flood_area_km2` correlates with usable area at r = 0.50, so absolute km² is **not**
comparable month to month; use `flooded_pct` (share of usable area) for comparisons and
always report the covered area alongside.

### Open-water false positives
Before the permanent-water mask is applied, 81–99% of every month's detected pixels sit
on JRC permanent water. Calm water is specular at C-band and reads as a large negative
dB change against a windier baseline, so lakes and rivers register as "flooded". The
mask removes them, but the extent that survives is largely the fringe around those water
bodies rather than independent flood signal.

2026-07 is the extreme case: 5,513 km² detected raw, 99.4% of it on permanent water,
leaving 610 fragments at a median of 1 pixel (versus 98% of area in patches ≥10 px for
2025-09). Treat 2026-07 as a water-edge artifact, not a seasonal peak.

## Peak flood event
September 2025: **217.2 km²** — dominant signal consistent with the short-rains onset
in South Kivu. (An earlier release quoted 3,428 km² from a −3 dB threshold; that was
confirmed a wet-soil/forest artifact and the threshold was raised to −5 dB on
2026-07-09.) Verify against OCHA/ReliefWeb DRC situation reports for Sep–Oct 2025.

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
for name in ['admin2.parquet', 'admin3.parquet', 'h3_7.parquet']:
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
