# Feature 003 — GeoSQL Integration
**Status:** Planned  
**Author:** Trevor Monroe  
**Last updated:** 2026-07-08

---

## Background

**GeoSQL** ([dekart-xyz/geosql](https://github.com/dekart-xyz/geosql)) is an open-source
AI skill developed by Volodymyr Bilonenko (Dekart) that turns Claude and other LLMs into
geospatial SQL agents. It provides:

- **Automatic metadata discovery** — the agent reads database schemas and geospatial
  metadata (geometry columns, CRS, bounding boxes, row counts) without requiring manual
  annotation.
- **Cost guardrails** — a configurable billing-cap (default 10 GiB on BigQuery) and
  pre-query cost estimation step prevent runaway charges on large datasets.
- **Geometry validation** — sanity checks on output GeoJSON before returning results to
  the calling LLM (e.g. empty geometries, invalid CRS, self-intersecting polygons).
- **Visual feedback loop** — integrates with Dekart/Kepler.gl to render query results on
  a map, enabling the LLM to refine queries based on visual inspection.
- **Multi-engine SQL generation** — generates PostGIS, BigQuery Geo, and Wherobots
  spatial SQL using engine-appropriate functions (ST_INTERSECTS, ST_DISTANCE, etc.).

> **Note on naming:** The user originally referenced "GeoSGL/GeoSKL" — the correct
> project name is **GeoSQL** (dekart-xyz/geosql).

---

## Problem Statement

The current flood pipeline produces:
- Monthly flood extent GeoJSONs (EPSG:4326)
- Admin-2/3 and H3-7 sampling frames (GeoParquet)
- Flood stats CSV (area, % flooded per month)

Researchers using these outputs currently must write raw GeoPandas / SQL queries
manually. There is no natural-language query interface, no automated cost control for
large-area analyses, and no metadata catalog that describes the flood datasets to an
external agent.

---

## Goals

| Goal | Metric |
|------|--------|
| Natural-language flood queries via Claude | Agent answers "Which territories had > 50 km² of flooding in Sep 2025?" without writing code |
| Metadata auto-discovery | GeoSQL agent reads table schemas without manual annotation |
| Cost guardrails | BigQuery queries capped at 10 GiB by default; estimate shown before run |
| Geometry validation | Invalid / empty GeoJSON caught before map render |
| Visual result loop | Flood query results rendered in Dekart/Kepler.gl for LLM self-correction |

---

## Non-Goals

- Re-processing SAR rasters via SQL (raster ops remain in Python / rasterio)
- Real-time ingestion (batch monthly cadence unchanged)
- User-facing web UI (Dekart is the rendering layer, not a product)

---

## Proposed Architecture

```
Claude (claude-sonnet-4-6)
    ↓  natural language query
GeoSQL MCP tool
    ├── metadata_discovery()   →  reads PostGIS / BQ table schemas + geometry types
    ├── cost_estimate()        →  estimates bytes processed before running query
    ├── run_spatial_query()    →  executes and returns GeoJSON + tabular results
    └── validate_geometry()    →  sanity-checks output before returning
    ↓  GeoJSON result
Dekart / Kepler.gl             (optional visual feedback)
    ↓  rendered map
Claude self-correction loop    (refine query based on map)
```

### Data Layer Options

**Option A — PostGIS (recommended for local / low-cost)**
- Load `data/handover/` into a local PostGIS instance via `ogr2ogr` or `geopandas.to_postgis()`
- Free; no egress costs; queries run in seconds on <1 GB dataset
- GeoSQL connects via `postgresql://localhost:5432/floodmaps`

**Option B — Google BigQuery + BigQuery Geo**
- Upload parquets to a BigQuery dataset via `pandas-gbq`
- 10 GiB free query tier per month; GeoSQL cost cap prevents overrun
- Enables sharing with external researchers who have BQ access
- Connection: `bigquery://project_id/dataset_id`

---

## Algorithm Improvements from GeoSQL

Beyond query interface, GeoSQL enables two analytical improvements:

### 1. Spatial-Temporal Aggregation via SQL
Current limitation: flood stats are pre-aggregated at monthly cadence. With GeoSQL, a
researcher can ask: *"What is the cumulative flood duration (months exposed) per H3-7
hexagon?"* — a query the Python pipeline does not pre-compute.

```sql
-- Example: cumulative exposure per H3-7 cell
SELECT hex_id,
       COUNT(*) FILTER (WHERE flood_pct > 0) AS flood_months,
       MAX(flood_area_km2) AS peak_flood_km2
FROM h3_7_flood
GROUP BY hex_id
ORDER BY flood_months DESC;
```

### 2. Cross-Dataset Joins (flood × boundaries × towers)
GeoSQL can join flood extents with OpenCelliD tower locations to identify which
territories had both high flood exposure and poor cell coverage — directly informing
phone-survey inaccessibility weighting.

---

## Implementation Plan (see plan.md)

1. Load handover data into PostGIS (or BigQuery)
2. Install and configure GeoSQL MCP server
3. Wire GeoSQL to Claude via MCP tool definition
4. Add metadata annotations to flood tables
5. Configure 10 GiB cost cap and geometry validation
6. Add Dekart visual feedback (optional)
7. Write example queries in docs/

---

## Validation & Guardrails

| Guardrail | Implementation |
|-----------|---------------|
| Cost cap | `MAX_BYTES_BILLED = 10_737_418_240` (10 GiB) on BigQuery; enforced by GeoSQL |
| Geometry validation | `ST_IsValid()` check on all output geometries; empty results flagged |
| CRS enforcement | All tables stored in EPSG:4326; GeoSQL validates CRS on read |
| Schema validation | GeoSQL metadata_discovery() checks for required columns (month, geometry) |
| Row count sanity | Alert if query returns > 1M rows (likely Cartesian product) |

---

## Open Questions

1. PostGIS vs BigQuery — PostGIS is simpler and free; BigQuery enables sharing. Decide
   based on whether external collaborators need direct SQL access.
2. Dekart self-hosting vs managed — Dekart is open-source; managed tier (dekart.cloud)
   costs ~$20/month. For local use, self-host.
3. MCP server transport — stdio (local dev) or HTTP (if deployed alongside flood_api.py).
