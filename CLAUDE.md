# CLAUDE.md — DRC Flood Extent Mapping

## Shared VPS

`flood-mcp` (`/opt/flood` on the VPS) runs on a shared Bluehost VPS used by
several other projects. See `C:\Users\trevm\Projects\VPS.md` for host access,
all services on the box, and the auto-deploy mechanism (weekly, Sundays
04:00 UTC). Public routing goes through Traefik (not nginx) — this service's
domain is `mcp-flood.trevormonroe.com` (note the naming break: `mcp-flood`,
not `flood-mcp` like every other service).

## Overview

SAR-based flood detection pipeline for eastern DRC (North Kivu, South Kivu, Ituri).
GitHub repo: `https://github.com/trevmon28/Floodmaps`
Run locally using the `gis_env` virtual environment at `C:\Users\trevm\Projects\SpatialLab\gis_env`.

Activate with:
```powershell
& "C:\Users\trevm\Projects\SpatialLab\gis_env\Scripts\Activate.ps1"
```

## Pipeline

| Notebook | Input | Output | Notes |
|----------|-------|--------|-------|
| `01_data_acquisition.ipynb` | STAC catalog | Scene inventory + AOI map | Discovery only, no downloads |
| `02_preprocessing.ipynb` | Sentinel-1 GRD via Element84 | `data/processed/sar/YYYY-MM_VV.tif`, `baseline_VV.tif` | Main compute bottleneck |
| `03_flood_detection.ipynb` | Processed VV tifs + baseline | `data/outputs/flood_extent/flood_extent_YYYY-MM.tif` | Change detection, -3 dB threshold |

## AOI & Temporal Coverage

- **AOI:** Eastern DRC — `[26.8, -5.9, 30.8, 3.0]` (WGS84), output CRS EPSG:32735
- **Period:** 2025-01-01 to 2026-04-30 (monthly)
- **Source:** Sentinel-1 GRD, Element84 Earth Search (no API key required)

## Key Config Variables (NB02)

- `process_all = False / True` — False processes one month (month_idx=0), True runs all
- `RESOLUTION = 100` — use 100 for testing, 20 for production (overnight run)
- `BASELINE_MONTHS = 3` — set in config.yaml; was temporarily overridden to 1 for single-month testing

## How to Edit Notebooks

All notebooks are JSON. Edit via Python scripts (see `build_nb03.py`, `rebuild_nb02.py`) or directly.
After editing, push with git:

```bash
git add notebooks/
git commit -m "description"
git push origin master
```

Do NOT use the build scripts to regenerate notebooks from scratch — they are outdated (pre-memory-fix).
Edit the notebooks directly or via targeted Python patches.

## Current Pipeline Status (as of May 2026)

- NB01: Complete — STAC discovery working on Element84
- NB02: Working — resolved stackstac → odc-stac, CRS, S3, memory issues. Uses dask chunks + per-band compute.
- NB03: Working — produced `flood_extent_2025-01.tif` in at least one test run
- No `.tif` output files currently on disk — pipeline needs a full re-run

## Pending / Next Steps

- [ ] Full production run: NB02 with `process_all=True, RESOLUTION=20` → all 16 months
- [ ] Validate flood extent maps against known flood events (e.g., 2025 South Kivu floods)
- [ ] Notebook 04: Export / visualisation — interactive map, time series chart of flooded area %
- [ ] Consider adaptive threshold (Otsu per scene) instead of fixed -3 dB

## Known Issues

- `rebuild_nb02.py` is outdated — missing dask chunks and uses `resolution=20` without memory safeguards. Do not use it to regenerate NB02.
- `build_nb03.py` still has the old Colab git-clone cell — also outdated.
- Baseline built from first 3 months (Jan–Mar 2025) may contain flood events if eastern DRC had early 2025 flooding.
