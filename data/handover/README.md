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
