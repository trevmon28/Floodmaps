# UN-SPIDER Tool Assessment
**Project:** DRC Flood Extent Mapping  
**Assessed:** 2026-07-08  
**Assessor:** Trevor Monroe

---

## What is UN-SPIDER?

**UN-SPIDER** (United Nations Platform for Space-based Information for Disaster Management
and Emergency Response) is an initiative of the UN Office for Outer Space Affairs (UNOOSA).
It is primarily a **knowledge hub and advisory platform**, not a software tool or data
service. It does not provide:
- Direct data downloads or a data API
- Processing infrastructure or cloud compute
- A Python package or CLI tool to install

What it *does* provide — and what is directly useful to this project — is a set of
**validated, peer-reviewed recommended practices** for applying satellite imagery to
disaster mapping, including a well-documented Sentinel-1 SAR flood mapping workflow.

---

## UN-SPIDER Flood Mapping Workflow (7-Step Algorithm)

UN-SPIDER publishes a step-by-step recommended practice for flood mapping with
Sentinel-1 and Sentinel-2 that is directly comparable to this project's pipeline.

| Step | UN-SPIDER Recommendation | Current Pipeline |
|------|--------------------------|-----------------|
| 1 | Orbit file application (precise orbit corrections) | ❌ Not applied — Element84 products are GRD; orbit files needed only for precise geocoding |
| 2 | Thermal noise removal (Level-1 GRD correction) | ❌ Not explicitly applied — Element84 tiles are pre-corrected at the platform level |
| 3 | Radiometric calibration (DN → backscatter sigma₀) | ✅ Applied via dB conversion in preprocessing.py |
| 4 | Speckle filtering — Lee 5×5 | ✅ Applied (Lee filter in preprocessing.py) |
| 5 | Terrain correction (Range-Doppler TC) | ⚠️ Applied implicitly via Element84 GRD product; explicit RTC not verified |
| 6 | **Binarization** — Combined minimum + **Otsu's method** | ⚠️ Current pipeline uses **fixed −3 dB threshold**; Otsu not yet implemented |
| 7 | Post-processing — **median filter 7×7** | ❌ Current pipeline uses `binary_opening` (3×3 structuring element); 7×7 median not applied |

### Key Gap: Adaptive Otsu vs Fixed −3 dB

The most significant methodological difference is in **Step 6 — binarization**.

**Current approach (fixed −3 dB change detection):**
- All pixels where `monthly_VV − baseline_VV < −3 dB` are classified as flooded.
- Threshold is constant across all months, terrains, and vegetation types.
- Simple and computationally cheap; appropriate for rapid operational use.
- Risk: Under-detects floods in months with naturally lower backscatter (dense forest,
  wet soil); over-detects in urban areas with specular reflection.

**UN-SPIDER recommended approach (combined minimum + Otsu):**
- Compute minimum backscatter across a multi-temporal stack (identifies persistently
  dark pixels = standing water).
- Apply Otsu's method (`skimage.filters.threshold_otsu`) to the bimodal histogram of
  the minimum composite to find the optimal water/land threshold automatically.
- Threshold adapts per scene and terrain type — more robust across seasons.

**Recommendation:** Implement Otsu as an optional mode in `run_detection_pipeline.py`
(controlled by `config.yaml`: `flood_threshold_method: otsu` vs `fixed`). The config
already has `flood_threshold_method: otsu` set — but the actual code uses `CHANGE_THRESHOLD_DB = -3.0`.
Close this gap as a high-priority follow-up.

---

## UN-SPIDER Data Sources Relevant to This Project

UN-SPIDER does not provide data directly but points to sources already in use:

| UN-SPIDER Pointer | Status in This Project |
|-------------------|----------------------|
| Copernicus Open Access Hub / ESA SciHub | ✅ Using Element84 Earth Search (equivalent free STAC) |
| Google Earth Engine (GEE) | Not used — pipeline is local Python |
| Copernicus DEM GLO-30 | ✅ Used for slope mask |
| JRC Global Surface Water | ✅ Used for permanent water mask |
| OCHA HDX admin boundaries | ✅ Used (ADM2, ADM3) |

UN-SPIDER also recommends the **Copernicus Emergency Management Service (CEMS)** rapid
mapping product as a validation reference — this is not currently used and would be
valuable for validating the September 2025 flood peak.

---

## Specific Value UN-SPIDER Adds to This Project

### 1. Algorithm Validation Checklist

UN-SPIDER's recommended practice provides a peer-reviewed checklist this project can
use to audit its own methodology. Current gaps identified:
- [ ] Verify thermal noise removal status of Element84 GRD tiles
- [ ] Implement Otsu adaptive threshold (config already set; code not yet updated)
- [ ] Replace `binary_opening(3×3)` with median filter `7×7` for post-processing noise removal
- [ ] Document which Range-Doppler Terrain Correction version is applied by Element84

### 2. Reference Case Studies

UN-SPIDER published validated flood maps for Mozambique (Cyclone Idai, 2019) and
Pakistan (monsoon flooding, 2022) using Sentinel-1 SAR. These can serve as calibration
benchmarks — if the pipeline produces comparable backscatter histograms and flood
extents on similar terrain, it provides confidence in the DRC results.

### 3. Capacity Building Materials

UN-SPIDER's Python Jupyter notebooks (available on GitHub/Binder) provide a reference
implementation of the 7-step algorithm. These can be cross-referenced when debugging
unexpected detection results (e.g., the October–November 2025 dip in flood area).

### 4. CEMS Validation

The **Copernicus Emergency Management Service** rapid mapping activations for DRC flood
events in 2025 (if any were triggered) would provide independent flood extent polygons
to validate against this project's output. UN-SPIDER provides pointers to CEMS.

---

## What UN-SPIDER Cannot Help With

| Limitation | Impact |
|-----------|--------|
| No data API — advisory only | Cannot replace STAC-based acquisition |
| No Python package — Jupyter notebooks only | Integration requires manual porting |
| Focuses on rapid-response mapping (single event) not monthly time series | Time-series design decisions remain project-specific |
| GEE-centric tutorials | GEE is not used; local Python pipeline requires adaptation |
| Processing infrastructure not provided | Compute resources remain local |

---

## Recommended Actions

1. **Implement Otsu adaptive threshold** (closes the biggest algorithmic gap):
   ```python
   from skimage.filters import threshold_otsu
   # In run_detection_pipeline.py, add option:
   if cfg["processing"]["flood_threshold_method"] == "otsu":
       valid_change = change[np.isfinite(change)]
       thresh = threshold_otsu(valid_change)
       flood_mask = (change < thresh).astype("uint8")
   else:
       flood_mask = (change < CHANGE_THRESHOLD_DB).astype("uint8")
   ```

2. **Upgrade post-processing from binary_opening to 7×7 median filter**:
   ```python
   from scipy.ndimage import median_filter
   flood_clean = median_filter(flood_mask.astype("float32"), size=7)
   flood_mask = (flood_clean > 0.5).astype("uint8")
   ```

3. **Check CEMS activations** for DRC 2025 at
   `https://emergency.copernicus.eu/mapping/list-of-activations-rapid`
   and compare flood extents against the September 2025 peak (3,427 km²).

4. **Reference UN-SPIDER case studies** in the research paper methodology section to
   contextualise the DRC pipeline within validated international practice.

---

## Verdict

UN-SPIDER is **moderately helpful** for this project. Its primary value is as a
**methodological validation framework** rather than a data or software tool. The 7-step
algorithm reveals two concrete gaps in the current pipeline (Otsu threshold, 7×7 median
filter) that are worth closing. The CEMS validation pointer is also useful. However,
UN-SPIDER cannot replace any of the existing technical components.

**Priority:** Implement Otsu threshold and 7×7 median filter as a follow-up task
(estimated 2–4 hours). File as a new speckit task (feature 005).
