# Plan — GeoSQL Integration (Feature 003)
**Status:** Draft  
**Last updated:** 2026-07-08

---

## Phase 1 — Data Layer (PostGIS)

Goal: load all handover data into a local PostGIS database so GeoSQL can query it.

### Steps
1. Create PostGIS database `floodmaps_db` with PostGIS extension enabled.
2. Load flood extents (GeoJSON → PostGIS `flood_extents` table):
   ```python
   import geopandas as gpd
   from sqlalchemy import create_engine
   engine = create_engine("postgresql://localhost:5432/floodmaps_db")
   for geojson in Path("data/handover/flood_extents").glob("*.geojson"):
       gdf = gpd.read_file(geojson)
       month = geojson.stem.replace("flood_extent_", "")
       gdf["month"] = month
       gdf.to_postgis("flood_extents", engine, if_exists="append", index=False)
   ```
3. Load admin-2 and admin-3 parquets:
   ```python
   admin2 = gpd.read_parquet("data/handover/sampling_frames/admin2.parquet")
   admin2.to_postgis("admin2_flood", engine, if_exists="replace", index=False)
   ```
4. Load H3-7 parquet similarly → `h3_7_flood` table.
5. Load flood_stats.csv → `flood_stats` table (no geometry).
6. Add spatial indexes: `CREATE INDEX ON flood_extents USING GIST(geometry)`.

### Metadata Annotations (for GeoSQL auto-discovery)
Add `COMMENT ON TABLE` and `COMMENT ON COLUMN` annotations:
```sql
COMMENT ON TABLE flood_extents IS
  'Monthly Sentinel-1 flood extents for Eastern DRC (Jan 2025–Jul 2026). 
   Geometry is the dissolved flooded-area polygon per month. CRS: EPSG:4326.';

COMMENT ON COLUMN flood_extents.month IS
  'Month in YYYY-MM format (e.g. 2025-09).';
```

---

## Phase 2 — GeoSQL MCP Server Setup

1. Clone `dekart-xyz/geosql`:
   ```bash
   git clone https://github.com/dekart-xyz/geosql
   cd geosql && pip install -e .
   ```
2. Configure database connection in `geosql_config.yaml`:
   ```yaml
   database:
     type: postgresql
     connection_string: postgresql://localhost:5432/floodmaps_db
   cost_guardrails:
     max_rows_returned: 100000
     warn_above_rows: 10000
   geometry_validation:
     check_validity: true
     check_crs: EPSG:4326
   ```
3. Start MCP server:
   ```bash
   python -m geosql.mcp_server --config geosql_config.yaml --transport stdio
   ```
4. Register in Claude Code `settings.json` under `mcpServers`.

---

## Phase 3 — Claude MCP Tool Wiring

Add to `.claude/settings.json`:
```json
{
  "mcpServers": {
    "geosql": {
      "command": "python",
      "args": ["-m", "geosql.mcp_server", "--config", "geosql_config.yaml"],
      "cwd": "C:\\Users\\trevm\\Projects\\Floodmaps"
    }
  }
}
```

---

## Phase 4 — Validation Queries

Run these to confirm GeoSQL is working correctly:

```sql
-- 1. How many months of valid flood data are there?
SELECT COUNT(*) FROM flood_stats WHERE quality = 'valid';

-- 2. Which month had the largest flood extent?
SELECT month, flood_area_km2 FROM flood_stats ORDER BY flood_area_km2 DESC LIMIT 1;

-- 3. Which Admin-2 territories overlap with flood extents in Sep 2025?
SELECT a.adm2_name, ST_Area(ST_Intersection(a.geometry, f.geometry)::geography) / 1e6 AS overlap_km2
FROM admin2_flood a
JOIN flood_extents f ON ST_Intersects(a.geometry, f.geometry)
WHERE f.month = '2025-09'
ORDER BY overlap_km2 DESC;
```

---

## Phase 5 — Optional: Dekart Visual Feedback

1. Deploy Dekart locally via Docker:
   ```bash
   docker run -p 8080:8080 dekartxyz/dekart:latest
   ```
2. Configure GeoSQL to push results to Dekart endpoint.
3. Claude can then render query results visually and self-correct based on map output.

---

## Risk Register

| Risk | Likelihood | Mitigation |
|------|-----------|-----------|
| GeoSQL schema mismatch (geometry column naming) | Medium | Rename geometry → geom to match PostGIS conventions |
| PostGIS spatial index missing → slow queries | Low | Add GIST indexes in Phase 1 |
| GeoSQL not yet production-stable | Medium | Pin to known-good commit; test all Phase 4 queries |
| MCP server stdio vs HTTP conflict with flood_mcp_server.py | Low | Use different ports / transports |
