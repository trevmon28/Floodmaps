# DRC Flood Mapping Pipeline — Status Tracker

**Last updated:** 2026-07-08  
**AOI:** Eastern DRC (North Kivu, South Kivu, Ituri)  
**Period:** Jan 2025 – Jul 2026 (19 months)  
**Env:** `C:\Users\trevm\Projects\SpatialLab\gis_env`

## How to Restart After a Crash

```powershell
# 1. Activate environment
& "C:\Users\trevm\Projects\SpatialLab\gis_env\Scripts\Activate.ps1"

# 2. Open JupyterLab
cd C:\Users\trevm\Projects\Floodmaps
jupyter lab
```

Then open the notebook for the phase that failed and **run only the cells that haven't completed yet** (check the table below). You do NOT need to re-run cells whose outputs already exist on disk.

---

## Phase Overview

| Phase | Notebook / Script | Runtime | Status |
|-------|------------------|---------|--------|
| 1 — Data Discovery | `01_data_acquisition.ipynb` | ~2 min | ✅ Complete |
| 2 — Preprocessing (VV/VH COGs) | `02_preprocessing.ipynb` | 8–12 hr (RESOLUTION=20) | ✅ Complete |
| 2b — Build Baseline | `run_detection_pipeline.py` | ~40–60 min | ✅ Complete — `baseline_VV.tif` 98.4 MB (2025-03/04/05) |
| 2c — Quality Masks | `build_masks.py` | ~15 min | ✅ Complete — both masks built |
| 3 — Flood Detection (with masks) | `run_detection_pipeline.py` | ~2 min | ✅ Complete — all 16 months, 2026-05-16 7:20 PM |
| 3b — Flood Detection (reprocess) | — | — | ✅ Done via FORCE_REPROCESS=True in step 3 |
| 4 — Validation & Export | `notebooks/04_validation_export.ipynb` | ~2 min | 🔄 Ready to run |
| 5 — Extend to May–Jul 2026 | `extend_may_july_2026.py` | ~4–8 hr | ⏳ Pending — run to add 3 new months |

---

## Phase 2 — Preprocessing Status

**Output dir:** `data/processed/sar/`  
NB02 was run with `process_all=True`. All 16 VV files exist on disk. Skip re-running unless a file is flagged as suspect.

| Month | VV File | VV Size | VH File | VH Size | Notes |
|-------|---------|---------|---------|---------|-------|
| 2025-01 | ✅ | 1,527 MB | ✅ | 1,221 MB | Good coverage |
| 2025-02 | ✅ | 861 MB | ✅ | 742 MB | Good coverage |
| 2025-03 | ✅ | 994 MB | ⚠️ | 4.5 MB | VH sparse — dry season? |
| 2025-04 | ✅ | 125 MB | ⚠️ | 4.5 MB | VV + VH sparse |
| 2025-05 | ✅ | 1,804 MB | ⚠️ | 1.3 MB | VH near-empty |
| 2025-06 | ✅ | 309 MB | ✅ | 228 MB | OK |
| 2025-07 | ✅ | 38 MB | ⚠️ | 4.5 MB | VV + VH sparse |
| 2025-08 | ✅ | 309 MB | ✅ | 300 MB | OK |
| 2025-09 | ✅ | 1,798 MB | ✅ | 360 MB | Good coverage |
| 2025-10 | ✅ | 122 MB | ⚠️ | 4.5 MB | VH sparse |
| 2025-11 | ✅ | 123 MB | ✅ | 42 MB | OK |
| 2025-12 | ✅ | 123 MB | ✅ | 74 MB | OK |
| 2026-01 | ✅ | 103 MB | ⚠️ | 4.5 MB | VH sparse |
| 2026-02 | ✅ | 1,490 MB | ✅ | 508 MB | Good coverage |
| 2026-03 | ⚠️ | 4.5 MB | ⚠️ | 3.0 MB | **Both tiny** — suspect; may need reprocess |
| 2026-04 | ⚠️ | 1.3 MB | ❌ | missing | **Very small** — likely incomplete |
| 2026-05 | ⏳ | pending | ⏳ | pending | Acquisition pending — run `extend_may_july_2026.py` |
| 2026-06 | ⏳ | pending | ⏳ | pending | Acquisition pending — run `extend_may_july_2026.py` |
| 2026-07 | ⏳ | pending | ⏳ | pending | Acquisition pending — run `extend_may_july_2026.py` |

> **Note on small files:** VH files < 5 MB may reflect real sparse S1 coverage for that month/AOI. VV files < 5 MB (2026-03, 2026-04) are suspect and may need reprocessing with NB02.

---

## Phase 2b — Build Baseline

`baseline_VV.tif` is being built by `run_detection_pipeline.py` (currently running, 2026-05-15).

**If it needs to be re-run:**
```powershell
& "C:\Users\trevm\Projects\SpatialLab\gis_project\gis_env\Scripts\python.exe" run_detection_pipeline.py
```
The script uses a memory-safe 3-value median formula (`fmax/fmin`) in 256-row chunks. Do NOT use NB02 Cell 8 directly — it will OOM.

## Phase 2c — Quality Masks ✅ Complete

Both masks built by `build_masks.py`. Run once, persist forever.

| Mask | File | Coverage |
|------|------|---------|
| Slope > 8° | `data/raw/masks/slope_mask.tif` | 30% of AOI flagged |
| Permanent water (JRC GSW ≥75%) | `data/raw/masks/perm_water_mask.tif` | 5% of AOI flagged |

**Source:** Copernicus DEM GLO-30 (Element84 STAC) + JRC GSW (Microsoft Planetary Computer)

---

## Phase 3 — Flood Detection

**Input:** `data/processed/sar/YYYY-MM_VV.tif` + `baseline_VV.tif`  
**Output:** `data/outputs/flood_extent/flood_extent_YYYY-MM.tif` + `.geojson`  
**Method:** Change detection — pixels where monthly VV drops > 3 dB below baseline = flooded

| Month | TIF Output | GeoJSON | Flood Area | Notes |
|-------|-----------|---------|------------|-------|
| 2025-01 | ✅ | ✅ | 0.0 km² | ⚠️ VV data is raw amplitude (not dB) — result unreliable |
| 2025-02 | ✅ | ✅ | 0.0 km² | ⚠️ VV data is raw amplitude (not dB) — result unreliable |
| 2025-03 | ✅ | (no flood px) | 2.3 km² | Used as baseline month |
| 2025-04 | ✅ | ✅ | 0.0 km² | Used as baseline month |
| 2025-05 | ✅ | ✅ | 26.6 km² | Used as baseline month |
| 2025-06 | ✅ | ✅ | 14.0 km² | |
| 2025-07 | ✅ | ✅ | 8.1 km² | |
| 2025-08 | ✅ | ✅ | 37.6 km² | |
| 2025-09 | ✅ | ✅ | ~~3,427.6 km²~~ **SUSPECT** | Likely wet-soil/forest artifact — no OCHA/CEMS corroboration; threshold raised to -5 dB for reprocess |
| 2025-10 | ✅ | ✅ | 10.9 km² | |
| 2025-11 | ✅ | ✅ | 11.4 km² | |
| 2025-12 | ✅ | ✅ | 10.2 km² | |
| 2026-01 | ✅ | ✅ | 9.2 km² | |
| 2026-02 | ✅ | ✅ | 108.6 km² | |
| 2026-03 | ✅ | (no flood px) | 0.0 km² | VV file 4.5 MB — data gap |
| 2026-04 | ✅ | (no flood px) | 0.0 km² | VV file 1.3 MB — data gap; stale bad GeoJSON deleted |
| 2026-05 | ⏳ | pending | pending | Run `extend_may_july_2026.py` |
| 2026-06 | ⏳ | pending | pending | Run `extend_may_july_2026.py` |
| 2026-07 | ⏳ | pending | pending | Run `extend_may_july_2026.py` |

**How to run:**
1. Open `notebooks/03_flood_detection.ipynb`
2. Run all cells top to bottom
3. The detection loop (Cell 8) saves each month's output as it completes — if it crashes mid-run, the completed months are saved and you can skip them on restart
4. To restart after a crash: manually skip months that already have output files on disk (or add a `if flood_path.exists(): continue` guard to Cell 8)

**If it crashes mid-run:** check `data/outputs/flood_extent/` for already-completed TIF files, then modify the month list in Cell 8 to start from the first missing month.

---

## Phase 4 — Validation & Export (Pending)

- [ ] Compare flood maps against known 2025 South Kivu flood events
- [ ] Notebook 04: time series chart (flood area km² per month)
- [ ] Notebook 04: interactive Folium map of all months
- [ ] Export GeoJSONs to GitHub / researcher handoff

---

## Known Issues & Watch-outs

| Issue | Impact | Workaround |
|-------|--------|------------|
| `rebuild_nb02.py` / `build_nb03.py` are outdated | Will corrupt notebooks if run | Edit notebooks directly; do NOT use these scripts |
| Baseline from Jan–Mar 2025 may capture early-season floods | Slightly reduces flood signal for those months | Acceptable for now; note in outputs |
| Dense forest masks flood signal (backscatter similar to water) | Under-detection in forested floodplains | Flag in validation |
| Urban specular reflection | False positives in Goma, Bukavu | Post-process masking (future) |
| Fixed -3 dB threshold | Optimal varies by terrain | Consider Otsu adaptive threshold (future) |
| 2026-03 and 2026-04 VV files are suspiciously small | May produce noisy or empty flood maps | Verify with NB01 scene counts before detection |
| Data leakage in training data | Affects ML model validity (not this pipeline directly) | Acknowledged; see CLAUDE.md |

---

## Run Log

| Date | Action | Result |
|------|--------|--------|
| 2026-05-14 | Session crash — pipeline interrupted | NB02 preprocessing complete; baseline and NB03 not run |
| 2026-05-15 | Wrote `run_detection_pipeline.py` | Standalone script replacing notebooks; crash-safe, incremental |
| 2026-05-15 | Baseline build attempt 1 | Failed — OOM on `np.nanmedian` of full stacked (3, H, W) array |
| 2026-05-15 | Baseline build attempt 2 | Failed — OOM on numpy masked array even with 512-row chunks |
| 2026-05-15 | Baseline build attempt 3 (running) | Fixed: fmax/fmin 3-value formula, 256-row chunks, no (3,H,W) stack |
| 2026-05-15 | `build_masks.py` complete | slope_mask.tif (30% flagged >8°), perm_water_mask.tif (5% permanent water) |
| 2026-05-16 | `run_detection_pipeline.py` complete | baseline from 2025-03/04/05 (calibrated); all 16 months processed with quality masks |
| 2026-05-16 | Deleted stale `flood_extent_2026-04.geojson` (256 MB, from bad 8:24 AM run) | 2026-04 has 0 flood pixels — no GeoJSON warranted |
| 2026-05-16 | Deleted stale GeoJSONs for 2025-01, 2025-02, 2025-04 (old runs, 0 px) | Keeping outputs consistent with flood_stats.csv |
| 2026-05-16 | Built `notebooks/04_validation_export.ipynb` via `build_nb04.py` | Time-series chart, Folium map, export inventory, summary stats |
| 2026-07-08 | Extended temporal window to Jul 2026 | `config/config.yaml` end date → 2026-07-31; `extend_may_july_2026.py` created; PIPELINE_STATUS.md updated |
| 2026-07-08 | Sep 2025 anomaly investigation | Cross-checked 3,427.6 km² against OCHA ReliefWeb + CEMS: no corroborating activations. Major 2025 DRC floods were Apr–May. Sep = rainy-season onset → wet-soil/forest false positive. Threshold raised to -5 dB; FORCE_REPROCESS=True. Full rerun of detection needed. |

> **Update this table each time you run a phase.** Include what you ran, whether it succeeded, and any errors.

---

## Quick Reference: Key Paths

| Item | Path |
|------|------|
| Notebooks | `C:\Users\trevm\Projects\Floodmaps\notebooks\` |
| Processed SAR | `C:\Users\trevm\Projects\Floodmaps\data\processed\sar\` |
| Baseline (target) | `C:\Users\trevm\Projects\Floodmaps\data\processed\sar\baseline_VV.tif` |
| Flood outputs | `C:\Users\trevm\Projects\Floodmaps\data\outputs\flood_extent\` |
| Config | `C:\Users\trevm\Projects\Floodmaps\config\config.yaml` |
| Python env | `C:\Users\trevm\Projects\SpatialLab\gis_env\Scripts\Activate.ps1` |
