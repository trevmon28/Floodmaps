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
