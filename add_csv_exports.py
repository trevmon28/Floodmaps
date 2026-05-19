"""
Adds CSV exports to the existing handover package and re-zips.
"""
import shutil
import pandas as pd
import geopandas as gpd
from pathlib import Path

ROOT      = Path(r'c:\Users\trevm\Projects\Floodmaps')
OUT       = ROOT / 'data' / 'handover'
FRAMES    = ROOT / 'data' / 'outputs' / 'sampling_frames'
FLOOD_DIR = ROOT / 'data' / 'outputs' / 'flood_extent'

BAD_MONTHS = {'2025-01', '2025-02'}

csv_dir = OUT / 'csv'
csv_dir.mkdir(exist_ok=True)

# 1. Admin-3 flood data (no geometry — ready for Excel/SPSS/Stata)
print("Building admin3_flood.csv...")
admin3 = gpd.read_parquet(FRAMES / 'admin3.parquet')
admin3_csv = admin3.drop(columns='geometry').copy()
admin3_csv['centroid_lon'] = admin3.geometry.centroid.x.round(5)
admin3_csv['centroid_lat'] = admin3.geometry.centroid.y.round(5)
admin3_csv.to_csv(csv_dir / 'admin3_flood.csv', index=False)
print(f"  {len(admin3_csv)} rows")

# 2. H3-7 flood data (no geometry — h3_index is the join key)
print("Building h3_7_flood.csv...")
h3 = gpd.read_parquet(FRAMES / 'h3_7.parquet')
h3_csv = h3.drop(columns='geometry').copy()
h3_csv['centroid_lon'] = h3.geometry.centroid.x.round(5)
h3_csv['centroid_lat'] = h3.geometry.centroid.y.round(5)
h3_csv.to_csv(csv_dir / 'h3_7_flood.csv', index=False)
print(f"  {len(h3_csv)} rows")

# 3. Flood polygon centroids — one row per polygon per month
print("Building flood_centroids.csv...")
centroid_rows = []
for f in sorted(FLOOD_DIR.glob('flood_extent_????-??.geojson')):
    month = f.stem.replace('flood_extent_', '')
    if month in BAD_MONTHS:
        continue
    gdf = gpd.read_file(f)
    if gdf.empty:
        continue
    gdf = gdf.to_crs('EPSG:32735')
    gdf['area_km2'] = (gdf.geometry.area / 1e6).round(3)
    gdf = gdf.to_crs('EPSG:4326')
    gdf['centroid_lon'] = gdf.geometry.centroid.x.round(5)
    gdf['centroid_lat'] = gdf.geometry.centroid.y.round(5)
    for _, row in gdf.iterrows():
        centroid_rows.append({
            'month': month,
            'centroid_lon': row['centroid_lon'],
            'centroid_lat': row['centroid_lat'],
            'area_km2': row['area_km2'],
        })

centroids_df = pd.DataFrame(centroid_rows)
centroids_df.to_csv(csv_dir / 'flood_centroids.csv', index=False)
print(f"  {len(centroids_df)} rows")

# 4. Wide-format admin-3 table (one row per territory, months as columns)
print("Building admin3_flood_wide.csv...")
wide = admin3_csv.pivot_table(
    index=['shapeName', 'shapeISO', 'centroid_lon', 'centroid_lat'],
    columns='month',
    values='flood_area_km2',
    aggfunc='sum'
).reset_index()
wide.columns.name = None
wide.to_csv(csv_dir / 'admin3_flood_wide.csv', index=False)
print(f"  {len(wide)} territories × {len(wide.columns)} columns")

# Update README section
readme_addition = """
---

## CSV files (csv/ folder)
For use in Excel, SPSS, Stata, or R without GIS software.

| File | Description |
|------|-------------|
| `admin3_flood.csv` | Long format: one row per territory per month. Includes centroid lat/lon for mapping. |
| `admin3_flood_wide.csv` | Wide format: one row per territory, flood area columns for each month. Easy to join to survey data. |
| `h3_7_flood.csv` | One row per H3-7 hex per month. Join on `h3_index` using the `h3` Python library. |
| `flood_centroids.csv` | One row per flood polygon per month with centroid lat/lon and area. |

**Joining to phone survey data (admin-3):**
Match on territory name (`shapeName`) or use the centroid coordinates.

**Key columns:**
- `flood_area_km2` — flooded area within the unit that month
- `centroid_lon` / `centroid_lat` — centre point of the unit
- `quality` — `valid` or `gap` (gap = no satellite data that month)
"""

readme_path = OUT / 'README.md'
with open(readme_path, 'a', encoding='utf-8') as f:
    f.write(readme_addition)

# Re-zip
zip_path = ROOT / 'data' / 'eastern_drc_flood_data'
shutil.make_archive(str(zip_path), 'zip', OUT)
size_mb = zip_path.with_suffix('.zip').stat().st_size / 1e6

print()
print("=== CSV exports added ===")
for f in sorted(csv_dir.iterdir()):
    print(f"  csv/{f.name}  ({f.stat().st_size / 1e3:.0f} KB)")
print(f"\nRe-zipped: eastern_drc_flood_data.zip  ({size_mb:.1f} MB)")
