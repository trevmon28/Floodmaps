# DRC Flood Mapping Pipeline — Status Tracker

**Last updated:** 2026-09-23  
**AOI:** Eastern DRC (North Kivu, South Kivu, Ituri)  
**Period:** Jan 2025 – Jul 2026 (19 months, no gaps — Jun 2026 recovered and Jul 2026 re-pulled complete on 2026-09-08)  
**Threshold:** −5 dB change **+ −12 dB absolute ceiling** (absolute gate added 2026-09-22)  
**Masks:** slope >8°, permanent water buffered 3 px — applied *before* the 7×7 median filter  
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
| 5 — Extend to May–Jul 2026 | `extend_months.py` | ~2 hr | ✅ Complete — all three acquired full-fidelity, no degraded blocks |
| 6 — Absolute-gate re-release | `run_detection_pipeline.py` | ~15 min | ✅ Complete 2026-09-22 — all 19 months; May: 2.8; Jun: 23.3; Jul: 6.5 km² |

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
| 2026-05 | ✅ | 98.1 MB | — | — | RTC; 7.6% bbox coverage |
| 2026-06 | ✅ | 297.1 MB | — | — | RTC; **23.6% bbox coverage** — recovered 2026-09-08, was never a real gap |
| 2026-07 | ✅ | 107.7 MB | — | — | RTC; 8.5% bbox coverage (full month; was 2.5% on the mid-month pull) |

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
**Method:** Change detection — pixels where monthly VV drops > 5 dB below baseline = flooded  
**(threshold raised from 3 dB → 5 dB on 2026-07-09 after Sep 2025 artifact investigation)**

| Month | TIF Output | GeoJSON | Flood Area (−5 dB) | Notes |
|-------|-----------|---------|-------------------|-------|
| 2025-01 | ✅ | — | 0.0 km² | ⚠️ VV raw amplitude — unreliable |
| 2025-02 | ✅ | — | 0.0 km² | ⚠️ VV raw amplitude — unreliable |
| 2025-03 | ✅ | — | 0.0 km² | Baseline month — self-comparison = 0 |
| 2025-04 | ✅ | — | 0.0 km² | Baseline month — self-comparison = 0 |
| 2025-05 | ✅ | ✅ | 6.1 km² | Late long-rains (unchanged by the gate) |
| 2025-06 | ✅ | ✅ | 0.8 km² | Early dry season |
| 2025-07 | ✅ | — | 0.0 km² | Nothing survives absolute gating |
| 2025-08 | ✅ | ✅ | 0.0 km² | Nothing survives absolute gating |
| **2025-09** | ✅ | ✅ | **209.9 km²** | **Peak** *(3,427 → 217.2 at −5 dB → 209.9 with abs gate: only −3%)* |
| 2025-10 | ✅ | — | 0.0 km² | Nothing survives absolute gating |
| 2025-11 | ✅ | ✅ | 0.5 km² | |
| 2025-12 | ✅ | ✅ | 0.9 km² | |
| 2026-01 | ✅ | ✅ | 1.4 km² | |
| 2026-02 | ✅ | ✅ | 11.1 km² | Long-rains onset |
| 2026-03 | ✅ | ✅ | 5.6 km² | RTC recovery; 7.1% coverage |
| 2026-04 | ✅ | ✅ | 2.5 km² | RTC recovery; 5.2% coverage |
| 2026-05 | ✅ | ✅ | 2.8 km² | 7.6% coverage |
| 2026-06 | ✅ | ✅ | 23.3 km² | 23.6% coverage; 46 patches, median 18 px |
| 2026-07 | ✅ | ✅ | 6.5 km² | 8.5% coverage; 23 patches, median 10 px (was 610 / 1 px) |

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
| **Absolute km² not comparable across months** | Coverage varies 0.9%–50.5% of bbox and months image *different places*; r=0.50 between usable area and reported km² | Report density (% of usable area) alongside usable km²; compare only within a fixed reference footprint |
| **Baseline depth is shallow** | 45.6% of baseline pixels rest on a single observation, so the "dry" median cannot reject transient water; only 4.3% have all 3 obs | Widen the baseline window beyond 2025-03/04/05 |
| ~~Detection fires on open water~~ **ADDRESSED 2026-09-22** | Relative change alone flagged pixels at −7.3 dB (p90, 2026-07) where open water sits at −23 dB and dry land at −10.5 dB | Fixed: −12 dB absolute ceiling + 3 px water-mask buffer + masks applied before smoothing. Peak month moved −3%, 2026-07 −79%, fragmentation resolved (610 → 23 patches) |
| **−12 dB ceiling is uncalibrated** | Still reasoned from scene statistics, not ground truth. But a sweep (2026-09-23) shows results are **not knife-edge**: between −10 and −12 dB the corroborated anchor months move ≤1.5×, and the ranking is stable at every setting tested. Below −12 dB everything collapses (−14 dB cuts most months by 70–80%), so −12 sits at the knee | Sweep detail in `docs/validation_2026-09.md`. Ground-truth calibration still wanted, but the published conclusions do not hinge on the exact value within −10…−12 |
| **VH/VV discriminator still disabled** | VH is the strongest open-water discriminator available; `vh_ratio_threshold_db` remains `null` | ✅ VH now acquired for 2026-01…07 (2026-04…07 on 2026-09-23). Ready to enable — test it **before** revisiting the water buffer, since VH may permit a smaller buffer |
| ~~Uvira may be over-corrected~~ **RESOLVED 2026-09-23** | Uvira's entire pre-revision 8.82 km² came from **2026-07 alone** — the most contaminated month — and it shows ~0 in every other month including ones with documented events. GDACS records no DRC event in July 2026, and the removed pixels have a median of −16.7 dB (darker than typical flood at −13/−14, closer to open water at −23), i.e. lake/river surface rather than inundated land | Removal is defensible; the targeting warning is downgraded to a normal caveat. 249 px (2.49 km²) removed by the buffer alone remain ambiguous — dark *and* near-shore fits both a calm-water artifact and real riparian flooding |
| **Baseline contains a documented flood** | Baseline = 2025-03/04/05; GDACS records an in-AOI flood 2025-05-01→05-14. Suppresses detection where flooding recurs; 2025-05 self-compares | Rebuild from a flood-free window. 2025 dry season (Jun–Aug) has no in-AOI events but poor coverage (0.9% / 4.1%) — a longer window or per-pixel low percentile is likely more robust than a 3-month median |
| **Otsu absolute gate is a trap** | `absolute_threshold_method: otsu` finds the open-water/land split (−12 to −16.8 dB here), far darker than vegetated flooding; it cut 2025-09 to 108.5 km² and 2026-07 to 0.2 km² | Keep `fixed` unless mapping open water only |

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
| 2026-07-08 | Extended temporal window to Jul 2026 | `config/config.yaml` end date → 2026-07-31; `extend_months.py` created; PIPELINE_STATUS.md updated |
| 2026-07-08 | Sep 2025 anomaly investigation | Cross-checked 3,427.6 km² against OCHA ReliefWeb + CEMS: no corroborating activations. Major 2025 DRC floods were Apr–May. Sep = rainy-season onset → wet-soil/forest false positive. Threshold raised to -5 dB; FORCE_REPROCESS=True. Full rerun of detection needed. |
| 2026-07-09 | Full reprocess at −5 dB complete | All 16 months regenerated. Sep 2025: 3,427.6 → **217.2 km²** (94% reduction). Seasonal pattern now correct. Feb 2026: 108.6 → 17.4 km². All months consistent with expected climate signal. |
| 2026-07-10 | Extended to May–Jul 2026 via `extend_months.py` | Used `sentinel-1-rtc` (MPC) + rasterio read-validation filter. May: **5.8 km²** (7.6% spatial coverage — sparse RTC tiles). June: **data gap** (WarpOperationError — corrupt MPC tiles persisted beyond center-window filter). July: **0.0 km²** (2.5% coverage, partial month — re-run after 2026-07-31). Fixed CSV-update bug in extend script (rows were not overwritten on re-run). |

| 2026-09-08 | Re-pulled May–Jul 2026 via `extend_months.py` (renamed from `extend_may_july_2026.py`, months now CLI args) | **Jun 2026 recovered: 35.4 km² — it was never a data gap.** The month was lost to one transient MPC read failure aborting a whole-AOI load. Jul re-pulled complete: 2.5% → 8.5% coverage, 0.0 → 31.0 km². May reproduced exactly (20,753,755 px / 98.1 MB / 5.8 km²). No block needed the lenient fallback. |
| 2026-09-08 | Root-caused the 2026-06 gap | Failures are **transient**, not corrupt tiles: the same scenes that threw WarpOperationError/RasterioIOError read perfectly minutes later (A/B measured identical to the pixel under both signing methods). Fix = block-wise compositing + deferred second-pass retry; `fail_on_error=False` kept as last resort only, since applying it unconditionally silently cost 2026-05 2.85M valid px. |
| 2026-09-08 | Coverage audit of all 19 months | Coverage ranges 0.9%–50.5% of bbox and **no pixel is covered in all 19 months** (≥13/19 gives 10,792 km²). Absolute km² correlates with usable area at r=0.50, so the month-to-month km² series is not comparable as published. Baseline rests on a **single** observation for 45.6% of its area (only 4.3% has all 3). |

| 2026-09-22 | Full re-release: absolute-backscatter gate + buffered water mask | Relative change alone was flagging dry-land-bright pixels. Added −12 dB absolute ceiling, 3 px permanent-water buffer, and moved quality masks *before* the 7×7 median filter. All 19 months reprocessed. Series total 342.6 → **271.4 km²**. Discriminating, not blanket: 2025-09 −3% (217.2 → 209.9), 2026-07 −79% (31.0 → 6.5), marginal months (2025-07/08/10) → 0.0. Fragmentation resolved: 2026-07 from 610 patches/median 1 px to 23/median 10 px. Deleted 3 stale GeoJSONs for months that now detect zero. |
| 2026-09-22 | Rejected Otsu for the absolute gate | First attempt used `min(otsu(VV), −12)`. Otsu locates the open-water/land split (−12 to −16.8 dB), darker than the vegetated flooding being mapped (flagged pixels median −13 to −14 dB), so it behaved as an open-water detector: 2025-09 → 108.5 km², 2026-07 → 0.2 km². Switched to a fixed −12 dB ceiling; results then matched the modelled prediction (predicted 210.8, actual 209.9 for 2025-09). |

| 2026-09-23 | External validation cross-check (preliminary) | CEMS/Charter/GDACS/UN-SPIDER. **CEMS returns zero DRC activations 2023–2026** — activation is request-driven, so its silence carries no information for this country; the paper's §5.2 CEMS inference is withdrawn (physical argument unaffected). GDACS: both in-AOI events detected (2025-05 South Kivu; 2026-02→03 North Kivu, duration matches across two months), true negatives agree. **2025-09 (209.9 km²) and 2026-06 (23.3 km²) have no corroboration** — the two largest months. Full writeup in `docs/validation_2026-09.md`. |
| 2026-09-23 | **Baseline contamination confirmed externally** | Baseline = 2025-03/04/05. GDACS records an in-AOI flood 2025-05-01→05-14 and a boundary event 2025-03-28→04-17. The "dry" baseline therefore contains documented flooding, suppressing detection where flooding recurs, and 2025-05 is compared against a baseline containing itself. Previously speculative in CLAUDE.md; now evidence-backed. Not yet fixed. |
| 2026-09-23 | VH acquired for 2026-04…07 | `extend_months.py --band vh` (acquisition-only path added). Coverage matches VV exactly: 5.2% / 7.6% / 23.6% / 8.5%. VH now present for every month from 2026-01. `vh_ratio_threshold_db` still `null` — not enabled, would move the numbers a third time. |

| 2026-09-23 | Uvira investigation + threshold sensitivity sweep (read-only, no outputs changed) | **Uvira resolved**: its whole 8.82 km² came from 2026-07; decomposition of the 884 px = 143 removed by the absolute gate, 249 by the water buffer alone, ~363 by the mask-before-smooth reordering, 129 surviving. No GDACS event in Jul 2026 and median −16.7 dB → artifact, not recurrent flood. **Sensitivity**: ceilings −10/−11/−12/−13/−14 dB on six key months. Stable −10→−12 (2025-05 unchanged at 6.1; 2025-09 215.6→209.8), steep collapse below −12 (−14 dB: 2026-02 −75%, 2026-06 −78%). No threshold reverses the corroborated/uncorroborated contrast — the Sep 2025 peak dominates by 10–30× throughout. |

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
