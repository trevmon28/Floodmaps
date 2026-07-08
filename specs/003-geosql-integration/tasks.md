# Tasks — GeoSQL Integration (Feature 003)

## P0 — Foundation

- [ ] **003-01** Create PostGIS database `floodmaps_db` with PostGIS extension  
      `createdb floodmaps_db && psql -c "CREATE EXTENSION postgis;" floodmaps_db`

- [ ] **003-02** Write `load_to_postgis.py` — loads all handover data (flood extents,
      admin-2/3, H3-7, flood_stats) into PostGIS tables with spatial indexes and
      `COMMENT ON TABLE/COLUMN` metadata annotations.

- [ ] **003-03** Install GeoSQL from `dekart-xyz/geosql` into the gis_env environment
      and verify `python -m geosql.mcp_server --help` exits cleanly.

## P1 — Configuration

- [ ] **003-04** Create `geosql_config.yaml` in project root with PostGIS connection
      string, row-count guardrails (warn > 10k, cap > 100k), and geometry validation
      (check ST_IsValid, enforce EPSG:4326).

- [ ] **003-05** Register `geosql` MCP server in `.claude/settings.json` using stdio
      transport; verify Claude Code picks up the server on restart.

- [ ] **003-06** Write `docs/geosql_queries.md` with 5 example natural-language queries
      and their expected SQL translations (sourced from Phase 4 validation list in plan.md).

## P2 — Validation

- [ ] **003-07** Run all 3 validation queries from `plan.md § Phase 4` against the live
      PostGIS database and record results in `specs/003-geosql-integration/validation.md`.

- [ ] **003-08** Test metadata auto-discovery: ask Claude "what flood data is available?"
      and confirm GeoSQL returns correct table names, column types, and bounding boxes
      without manual prompting.

- [ ] **003-09** Test cost guardrail: craft a query that would exceed 100k rows without
      the cap; confirm GeoSQL blocks it and returns an explanatory error.

## P3 — Optional Enhancements

- [ ] **003-10** (Optional) Deploy Dekart via Docker; configure GeoSQL to send results to
      Dekart for visual rendering; test self-correction loop with Claude.

- [ ] **003-11** (Optional) Load flood data into BigQuery as an alternative backend and
      test GeoSQL with BigQuery Geo functions; compare query latency vs PostGIS.
