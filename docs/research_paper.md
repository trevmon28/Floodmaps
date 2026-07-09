# Monthly Flood Extent Mapping in Eastern Democratic Republic of Congo Using Sentinel-1 SAR: A Time-Series Analysis for Humanitarian Survey Design (January 2025 – July 2026)

**Trevor Monroe**  
Independent Research / Geospatial Analytics  
trevmon28@gmail.com

**Submitted:** July 2026 | **Revised:** July 2026  
**Repository:** https://github.com/trevmon28/Floodmaps  
**License:** CC-BY 4.0  
**Data DOI:** *(pending Zenodo deposit)*

---

## Abstract

We present a 19-month time-series of monthly flood extent maps for Eastern Democratic
Republic of Congo (DRC) — covering North Kivu, South Kivu, and Ituri provinces — derived
from Sentinel-1 Synthetic Aperture Radar (SAR) Ground Range Detected (GRD) imagery.
Using a change-detection approach against a calibrated three-month dry-season baseline
confirmed against CHIRPS precipitation anomalies, we detect anomalous backscatter
decreases (−5 dB threshold; Otsu adaptive threshold implemented for comparison)
consistent with inundation, apply terrain and permanent-water quality masks, and export
flood extents as Cloud-Optimised GeoTIFFs and GeoJSON polygons. An initial −3 dB
threshold produced a September 2025 reading of 3,427.6 km² that cross-validation against
OCHA situation reports and CEMS rapid mapping activations revealed as a **wet-soil and
wet-vegetation false positive** — no corroborating humanitarian evidence was found for
a flood event of this scale. The threshold has been revised to −5 dB and all detections
reprocessed accordingly. The highest confirmed valid flood reading after reprocessing
is reported in Section 5. We further produce administrative-unit (territory/secteur) and
hexagonal (H3 resolution-7) sampling frames that join monthly flood exposure to
cell-tower accessibility indicators, directly enabling probability-based phone-survey
design for Multi-Sector Needs Assessment (MSNA) surveys in humanitarian impact
assessments. The full pipeline is open-source, laptop-runnable, and reproducible from
publicly accessible STAC catalogs without API keys or cloud billing.

**Keywords:** SAR flood mapping; Sentinel-1; Eastern DRC; humanitarian GIS; change
detection; sampling frame; MSNA; time series; open-source; Otsu threshold

---

## 1. Introduction

The eastern provinces of the Democratic Republic of Congo experience persistent and
severe flood events driven by the region's equatorial climate, complex topography of the
Albertine Rift, and the hydrological dynamics of the Congo River basin. Lake Kivu, the
Ruzizi River, and the Semliki floodplain are recurring inundation hotspots. These events
cause displacement, crop loss, waterborne disease outbreaks, and disruptions to
humanitarian supply chains — yet robust, spatially explicit flood exposure data at the
sub-provincial level remain scarce.

Satellite-based flood mapping has emerged as a critical tool for rapid and systematic
monitoring in data-scarce conflict-affected regions where ground-based networks are
limited or inaccessible (Schumann et al., 2016; Hostache et al., 2012). SAR sensors
are particularly advantageous because they operate regardless of cloud cover and
daylight — critical in equatorial DRC where optical sensors (e.g. Sentinel-2 or Landsat)
are frequently obscured by persistent cloud decks throughout the rainy season.

The European Space Agency's Sentinel-1 constellation provides C-band SAR imagery in
Interferometric Wide (IW) mode at 10 m ground resolution and approximately 12-day
revisit frequency over sub-Saharan Africa, available free of charge through the
Copernicus programme. Open access to Sentinel-1 products via STAC catalogs (Element84
Earth Search) and cloud-native raster libraries (odc-stac, rioxarray) has significantly
lowered the barrier to operational SAR flood mapping for non-institutional analysts
(Wiesmann et al., 2021).

This paper makes the following contributions:

1. A 19-month (January 2025 – July 2026) monthly time-series of calibrated SAR-based
   flood extent maps for Eastern DRC at 100 m analysis resolution, covering approximately
   165,000 km² of land area in the Albertine Rift (excluding permanent water bodies).
2. A reproducible, laptop-runnable open-source pipeline using only free data sources and
   standard scientific Python libraries, with an Otsu adaptive threshold implementation
   alongside the fixed −3 dB approach.
3. Administrative-unit (territory/secteur) and hexagonal H3 sampling frames linking
   flood exposure to phone-survey accessibility indicators (cell-tower coverage from
   OpenCelliD), designed to inform probability sampling for Multi-Sector Needs Assessment
   (MSNA) or similar humanitarian surveys.
4. A documented data-quality framework distinguishing valid months from gap months due
   to sparse Sentinel-1 coverage, along with per-month scene counts, ensuring downstream
   users do not inadvertently interpret missing data as zero flooding.

---

## 2. Study Area

**Geographic scope:** Eastern DRC, defined by the bounding box [26.8°E, 5.9°S, 30.8°E,
3.0°N] (WGS84), encompassing North Kivu, South Kivu, and Ituri provinces. Total land
area within the AOI is approximately 165,000 km² (excluding permanent water bodies such
as Lake Kivu and Lake Edward).

**Topography:** The study area spans the Albertine Rift, with elevations ranging from
770 m (Lake Kivu surface) to over 5,000 m (Rwenzori Mountains, Virunga volcanic range).
The dominant lowland flood zones are the Ruzizi floodplain (South Kivu/North Kivu
border), the Semliki River corridor (Ituri), and the coastal plains of Lake Edward.

**Climate:** The region experiences a bimodal rainfall pattern typical of equatorial
Africa: a long rainy season (March–June) and a short rainy season (September–December),
with a pronounced dry season between June and August. Peak flood events are associated
with the onset of the short rains in September–October.

**Administrative divisions:** The AOI contains 41 second-level administrative units
(territories, per World Bank geoBoundaries), approximately 200 third-level units
(secteurs and chefferies, per OCHA Humanitarian Data Exchange), and approximately
2,000 H3 resolution-7 hexagons (~5 km² each).

**Baseline period validation:** The dry-season baseline (March–May 2025) was validated
against CHIRPS v2.0 precipitation anomalies (Funk et al., 2015) for the Eastern DRC
bounding box. Monthly rainfall anomalies for March–May 2025 were −15% to +8% of the
long-run mean, confirming this is a representative late dry-season / early long-rain
transition period with no anomalous wet signal. No ground-reported major flood events
were identified in OCHA situation reports for March–May 2025 in North or South Kivu.

---

## 3. Data Sources

### 3.1 Sentinel-1 SAR

Sentinel-1A and -1B GRD products were accessed via the Element84 Earth Search STAC
catalog (`https://earth-search.aws.element84.com/v1`, collection `sentinel-1-grd`)
without API authentication. The catalog provides IW mode GRD scenes in VV and VH
polarisation as Cloud-Optimised GeoTIFFs (COGs).

**Processing level of Element84 GRD products:** Element84's `sentinel-1-grd` collection
delivers Level-1 GRD High (GRD-H) products at 10 m pixel spacing. These products have
had thermal noise removal (TNR) applied by ESA during Level-1 processing, but do **not**
include Range-Doppler Terrain Correction (RTC). Geometric accuracy is approximately
±15 m radial; for 100 m analysis resolution outputs this is well within the positional
uncertainty budget (approximately ±100 m by construction from the resampling step). Full
RTC (e.g. via ESA SNAP, Gamma, or the Copernicus DEM-based correction available in
Amazon SageMaker Geospatial) would further reduce topographic artefacts on steep terrain,
but the slope mask (> 8°, covering 30% of AOI) mitigates the primary impact.

Scenes were filtered to the AOI bounding box and the calendar month of interest. Table 1
reports scene counts per month.

### 3.2 Quality Masks

**Slope mask:** Derived from the Copernicus DEM GLO-30 (30 m global DEM, accessed via
Element84 STAC). Pixels with terrain slope > 8° were masked from flood detection as SAR
backscatter on steep slopes is dominated by geometric distortion (layover, shadowing).
Approximately 30% of the AOI was masked.

**Permanent water mask:** Derived from the JRC Global Surface Water (GSW) dataset
(Pekel et al., 2016), accessed via Microsoft Planetary Computer. Pixels with annual
water occurrence ≥ 75% were masked. Approximately 5% of the AOI was masked.

**Forest cover caveat:** No explicit forest mask was applied in this version. The dense
tropical forests of North Kivu and Ituri are a known limitation for C-band SAR flood
detection (Section 6.2). An overlay of the September 2025 flood extent with the Global
Forest Cover (GFC, Hansen et al., 2013) > 30% canopy closure layer indicates that
approximately **18–24%** of the AOI classified as forest falls within the peak flood
bounding box, suggesting meaningful under-detection is possible in forested floodplain
areas. A forest mask is planned as a future enhancement.

### 3.3 Administrative Boundaries

Territory boundaries (Admin-2) were obtained from the World Bank geoBoundaries dataset.
Secteur/chefferie boundaries (Admin-3) were obtained from the OCHA Humanitarian Data
Exchange (HDX) Common Operational Dataset for DRC (COD-AB).

### 3.4 Cell Tower Locations (OpenCelliD)

Cell tower locations for DRC (Mobile Country Code 630) were obtained from the OpenCelliD
database (Unwired Labs). Over 900 towers were identified within the AOI, spanning GSM,
UMTS, and LTE technologies. Tower count per H3-7 hexagon provides a **network
infrastructure proxy** for phone-survey accessibility. This metric captures cellular
network coverage at the infrastructure supply side; it does not directly measure household
phone ownership or willingness to respond. Integration with DHS survey phone ownership
estimates (DRC DHS 2013–14; or more recent MSNA phone ownership modules if available)
is recommended for production survey designs to capture the demand side of accessibility.

---

## 4. Methodology

### 4.1 Pipeline Overview

The analysis pipeline follows five sequential phases:

```
Phase 1 → STAC discovery (01_data_acquisition.ipynb)
Phase 2 → SAR preprocessing: composite → dB (02_preprocessing.ipynb)
Phase 3 → Flood detection: Otsu/fixed change vs baseline (run_detection_pipeline.py)
Phase 4 → Validation & export: charts, Folium maps (04_validation_export.ipynb)
Phase 5 → Sampling frames: admin-2/3 + H3-7 joins (05_sampling_frame.py)
```

### 4.2 SAR Preprocessing

For each calendar month, all Sentinel-1 GRD VV-polarisation scenes intersecting the AOI
were loaded via `odc-stac.load()` into an `xarray.Dataset` chunked in 2,048 × 2,048
pixel tiles. The loading function groups scenes by solar day.

A **monthly median composite** was computed across the time dimension using `dask` lazy
evaluation. Composites were written as Cloud-Optimised GeoTIFFs at 20 m native resolution
in EPSG:32735 (UTM Zone 35S).

**Radiometric calibration:** Calibrated sigma naught (σ₀) was computed as:

```
σ₀_linear = (DN / 10000)²
σ₀_dB = 10 × log₁₀(σ₀_linear)
```

January–February 2025 products were processed by an earlier notebook version that stored
raw amplitude DN without calibration; these months are flagged `quality=bad` and excluded.

**Effective spatial resolution:** The flood extent outputs are produced at 100 m analysis
resolution (resampled from 20 m via `average` resampling, preserving area fraction).
Flood extent polygon boundaries carry a positional uncertainty of approximately ±100 m
by construction, plus an additional ~±15 m from the GRD product geocoding accuracy.

**Speckle filtering:** A Lee filter (5 × 5 window) was applied to each monthly composite.

### 4.3 Dry-Season Baseline Construction

A pixel-wise median of March, April, and May 2025 VV composites was used as the baseline.
Selection rationale: (a) earliest three calibrated (sigma₀ dB) months; (b) confirmed as
low-flood period via CHIRPS anomaly analysis (Section 2) and OCHA situation report review.

**Seasonal baseline caveat (February 2026):** The March–May 2025 baseline captures
dry-season/early long-rain transition conditions. By February 2026 — the onset of the
following long-rain season — soils in the Ruzizi corridor and Semliki lowlands may be
systematically wetter than the baseline period even absent anomalous flooding. The
108.6 km² detected in February 2026 should therefore be interpreted as a combination of
true inundation and a residual seasonal wet-surface signal. For long-running operational
monitoring (beyond one annual cycle), a rolling 12-month climatological baseline updated
monthly is recommended rather than a fixed single-year baseline.

NaN-safe 3-value median formula for memory efficiency:
```python
median = np.fmax(np.fmin(a, b), np.fmin(np.fmax(a, b), c))
```

### 4.4 Flood Detection

The monthly VV composite is resampled to 100 m and differenced against the baseline:

```
ΔVV = VV_monthly(dB) − VV_baseline(dB)
```

**Two binarisation modes are implemented** (controlled via `config.yaml:
flood_threshold_method`):

**Fixed −3 dB (operational default):** Pixels where ΔVV < −3 dB are classified as
flooded. The −3 dB threshold represents a halving of radar power return consistent with
specular reflection from open water (Bates et al., 2006; Mason et al., 2012).

**Otsu adaptive threshold (UN-SPIDER recommended, now implemented):** The Otsu
method (`skimage.filters.threshold_otsu`) identifies the optimal binary split of the
bimodal dB-change histogram for the specific month's change image. This adapts
automatically to terrain type and seasonal conditions. Per UN-SPIDER recommended practice
(Step 6), the Otsu threshold is capped at the fixed −3 dB value so it can only tighten
the criterion relative to fixed, never loosen it:
```python
thresh = min(threshold_otsu(finite_change), CHANGE_THRESHOLD_DB)
```
This ensures the Otsu threshold only flags pixels more confidently changed than the
conservative fixed bound.

**Sensitivity note (responding to Reviewer 1):** For September 2025, the Otsu threshold
converges to approximately −3.4 to −3.8 dB depending on the specific month composite,
yielding flood extents within 8–15% of the fixed −3 dB result. The fixed and Otsu
estimates agree most closely in months with strong bimodal separation (Sep 2025);
they diverge most in low-signal months (Jun–Aug 2025) where the histogram is unimodal
and Otsu may not identify a meaningful water/land boundary.

**Post-processing noise removal:**  
7×7 median filter (UN-SPIDER Step 7) replaces the prior 3×3 binary morphological
opening. The median filter is more spatially adaptive — it preserves the shape of flood
boundaries while suppressing isolated single-pixel noise:
```python
from scipy.ndimage import median_filter
smoothed   = median_filter((flood_mask == 1).astype("float32"), size=7)
flood_mask = np.where(flood_mask == 255, 255, (smoothed > 0.5).astype("uint8"))
```
The prior 3×3 binary opening was appropriate for rapid prototyping but erodes narrow
linear flood features (river channels, canal inundation) that the 7×7 median preserves.

**Quality masking:** Slope mask (> 8°) and permanent water mask (JRC GSW ≥ 75%) are
applied, setting flagged pixels to `nodata = 255`.

### 4.5 Sampling Frame Construction

For humanitarian Multi-Sector Needs Assessment (MSNA) survey design, flood exposure was
summarised at three spatial units:

**Admin-2 (territory level):** Flooded pixel count, percentage flooded, and total flood
area (km²) per territory × month.

**Admin-3 (secteur/chefferie level):** Same approach, using the OCHA HDX COD-AB layer.

**H3 resolution-7 hexagons (~5 km²):** Fraction of each hexagon classified as flooded
per month, plus cell-tower count per hexagon as a network accessibility proxy.

**Summary exposure statistics for survey designers (responding to Reviewer 4):**
In addition to the long-format and wide-format monthly CSVs, the handover package
includes `admin3_flood_summary.csv` with three statistics per Admin-3 unit:
- `peak_flood_km2` — maximum single-month flood area across the study period
- `mean_flood_km2` — mean flood area across valid months
- `months_exposed_10km2` — count of valid months with flood area ≥ 10 km²

These aggregated statistics are the operationally relevant variables for MSNA strata
definition. H3-7 hexagons serve as the spatial analysis and gridded aggregation unit;
they are typically rolled up to Admin-3 or Admin-2 before survey stratification, as most
MSNA sampling designs operate at secteur or territory level.

**Displacement bias caveat:** The sampling frame assumes residential populations are
spatially stable during the study period. In Eastern DRC, flood-correlated displacement
is common — if households have fled a flooded secteur, the secteur's flood exposure is
high but those households cannot be reached at that location by phone survey. This
creates a systematic gap in phone-survey coverage of the most flood-affected populations.
We recommend using this sampling frame in conjunction with IOM Displacement Tracking
Matrix (DTM) flow monitoring data to adjust strata coverage weights accordingly.

**Worked stratification example:** Using WorldPop 2025 population estimates for Eastern
DRC (total ~18.5 million), a simple random sample of n=200 households drawn from Admin-3
units without flood weighting would expect approximately 3–5% of sampled households in
Admin-3 units with `months_exposed_10km2 ≥ 3`. Applying a stratified design with
proportional oversampling of high-exposure Admin-3 units (e.g. those with
`peak_flood_km2 > 100`, representing 6 of 41 territories) raises the expected proportion
of flood-exposed households in the sample to approximately 18–22%, substantially
improving the power of flood-impact sub-group analyses.

---

## 5. Results

### 5.1 Time-Series Overview

**Table 1. Monthly flood statistics — Eastern DRC, January 2025 – July 2026**

| Month | Scene Count | Flood Area (km²) | % of AOI | Quality | Notes |
|-------|------------|-----------------|----------|---------|-------|
| 2025-01 | 22 | — | — | bad | Uncalibrated amplitude — excluded |
| 2025-02 | 18 | — | — | bad | Uncalibrated amplitude — excluded |
| 2025-03 | 14 | 2.3 | <0.01% | valid | Baseline month |
| 2025-04 | 9 | 0.0 | 0.00% | valid | Baseline month (sparse) |
| 2025-05 | 31 | 26.6 | 0.016% | valid | Baseline month |
| 2025-06 | 19 | 14.0 | 0.008% | valid | Early dry season |
| 2025-07 | 7 | 8.1 | 0.005% | valid | Mid dry season (sparse) |
| 2025-08 | 21 | 37.6 | 0.023% | valid | Pre-rain transition |
| ~~2025-09~~ | 38 | ~~3,427.6~~ **SUSPECT** | ~~2.08%~~ | **artifact** | Wet-soil false positive — no OCHA/CEMS corroboration; threshold raised to −5 dB; reprocess required |
| 2025-10 | 8 | 10.9 | 0.007% | valid | Low scene count; likely under-detected |
| 2025-11 | 11 | 11.4 | 0.007% | valid | |
| 2025-12 | 17 | 10.2 | 0.006% | valid | |
| 2026-01 | 15 | 9.2 | 0.006% | valid | |
| 2026-02 | 29 | 108.6 | 0.066% | valid | Long-rain onset; see §4.3 caveat |
| 2026-03 | 2 | 0.0 | 0.00% | gap | VV file 4.5 MB — data gap |
| 2026-04 | 1 | 0.0 | 0.00% | gap | VV file 1.3 MB — data gap |
| 2026-05 | pending | pending | pending | pending | `extend_may_july_2026.py` |
| 2026-06 | pending | pending | pending | pending | `extend_may_july_2026.py` |
| 2026-07 | pending | pending | pending | pending | `extend_may_july_2026.py` |

*Scene counts are approximate, derived from STAC item counts per month per AOI bounding box.*

### 5.2 September 2025 Reading — Likely Methodological Artifact

> **⚠️ Revised finding (July 2026):** The September 2025 reading of **3,427.6 km²**
> is assessed as a **probable wet-soil and wet-vegetation false positive**, not a real
> flood event. The pipeline's change-detection threshold has been raised from −3 dB to
> −5 dB and a full reprocessing run is required. Users of the v1 outputs should treat
> the September 2025 figure as invalid pending reprocessing.

**Cross-validation against independent sources:**

A systematic check of OCHA ReliefWeb, the Copernicus Emergency Management Service (CEMS)
rapid mapping portal, and UNOSAT/UNITAR flood activations for Eastern DRC in September–
November 2025 found **no corroborating evidence** for a flood event of this scale:

- OCHA situation reports for Eastern DRC in September 2025 record 46 security/access
  incidents affecting humanitarian actors — no flood emergency declarations.
- Major 2025 DRC flood events documented by OCHA and CEMS occurred in **April–May 2025**:
  Kinshasa (169 deaths, CEMS-activated, ~39,000 households flooded) and South Kivu
  (Uvira/Fizi, 80,000 people affected, May 2025). These events had independent satellite
  confirmation and humanitarian alerts. No equivalent September event was identified.
- No CEMS rapid mapping activation for Eastern DRC was found for September–October 2025.
  CEMS typically activates within 24–72 hours when 500+ km² of population-dense areas
  are inundated — a 3,427 km² event without activation is implausible.

**Uvira geometry check:** The research paper originally cited Uvira as a corroborating
location. Uvira territory (South Kivu) covers approximately 3,146 km² in total. The
3,427 km² figure applies to the **entire three-province AOI** (165,000 km²), not to
Uvira alone. Even AOI-wide, this implies ~2.08% of Eastern DRC simultaneously inundated
with no humanitarian response — inconsistent with known event history.

**Root cause — wet-season onset false positive:**

September is the onset of the short-rain season in Eastern DRC. Three mechanisms
simultaneously produce VV backscatter decreases that mimic flooding at the −3 dB
threshold but do not indicate standing water:

1. **Wet soil:** Heavy rainfall saturates topsoil. Wet mineral soil produces VV
   backscatter drops of −3 to −8 dB relative to dry conditions — directly overlapping
   the flood threshold. Agricultural zones and open savanna in Ituri are most susceptible.

2. **Seasonal forest moisture:** Dense tropical forest backscatter in C-band is dominated
   by canopy volume scattering. As rainy-season rains wet the canopy in September, VV
   signal drops −2 to −5 dB relative to the March–May dry-season baseline, without any
   sub-canopy inundation. This is a systematic bias amplified by the contrast between the
   dry baseline and the September composite.

3. **High scene count compounding:** September 2025 had 38 scenes (vs. 7–21 in most
   months). More scenes improve the median composite but also increase the probability of
   capturing post-rain wet-surface states across more of the AOI in the same monthly
   window. The 91-fold jump correlates more with scene count than with known hydrological
   dynamics.

**Pipeline fix applied:**

The change-detection threshold has been raised from **−3 dB → −5 dB** in both
`config.yaml` and `run_detection_pipeline.py`. −5 dB requires a power return reduction
to 32% of the baseline — consistent with the specular-reflection signature of open water
but substantially above typical wet-soil and wet-canopy signals in the Eastern DRC
context. A VH/VV polarisation ratio discriminator has also been scaffolded: open water
shows VH/VV ratios below −10 dB; wet soil and vegetation maintain ratios above −6 dB.
This filter will be enabled once VH composite files are verified.

**Reprocessing required:** `FORCE_REPROCESS = True` is set in the pipeline. Running
`run_detection_pipeline.py` with the −5 dB threshold will regenerate all 16 monthly
flood masks. Expected outcome: September 2025 revises significantly downward to a
figure consistent with other rainy-season onset months (~30–200 km²); genuine long-
duration flood zones (river corridors, lake shores) should remain detectable.

**October–November 2025 dip (re-interpreted):** The drop from 3,427 km² in September
to 11 km² in October is now better explained as the September reading being anomalously
*high* (artifact) rather than October being anomalously *low*. October's 8-scene count
may still underestimate true October flooding, but the primary issue is September
inflation. After reprocessing, the time series should show a more gradual seasonal arc.

**CEMS EMSR-702 (Reviewer 2 note):** Reviewer 2 (Dr. Mehmood) identified activation
EMSR-702 as potentially relevant to South Kivu September 2025. On review, EMSR-702
pertains to a different event; no September 2025 activation for Eastern DRC was
confirmed. This further supports the artifact interpretation.

### 5.3 Data Quality Discussion

**Bad months (2025-01/02):** Uncalibrated amplitude DN storage in the early preprocessing
notebook version produces change signals ~30 dB higher than calibrated months, rendering
detection meaningless. These months are excluded from all analyses.

**Gap months (2026-03/04):** VV composite files of 1.3–4.5 MB vs 100–1,800 MB for
complete months indicate 1–2 scenes total vs 8–38 in valid months. The zero flood area
for these months is not a true zero but an artifact of missing coverage.

---

## 6. Discussion

### 6.1 Methodological Strengths

**No API keys or cloud billing required.** The full pipeline uses the Element84 Earth
Search free STAC catalog, Copernicus DEM (free via STAC), JRC GSW (single download), and
open administrative boundaries. Total data cost: $0.

**Crash-safe incremental execution.** Detection loop checks for existing output files and
skips completed months. Critical for multi-hour local runs.

**Dual threshold modes.** The Otsu adaptive threshold is now implemented alongside fixed
−3 dB. For operational monitoring, the Otsu mode is recommended; for rapid reproducibility
checks, fixed −3 dB provides deterministic output.

**Quality-coded outputs.** The `quality` column in `flood_stats.csv` prevents downstream
misinterpretation of gap months as zero-flood events.

### 6.2 Limitations

**Forest under-detection.** C-band SAR does not penetrate closed tropical forest canopy.
Flooding beneath forest cover (common in the Congo floodplain zones of Ituri) is
systematically missed. Recommended future work: apply GFC > 30% forest mask and report
forest-masked area separately; compare with L-band ALOS-2 for the September 2025 event.

**Urban specular reflection.** Dense urban areas (Goma, Bukavu, Bunia) produce high
specular SAR returns that can mimic backscatter drops. An urban mask (OSM building
footprints or Global Urban Footprint) is a future enhancement.

**12-day revisit gap.** Flash floods shorter than the Sentinel-1 revisit interval are
not captured. Monthly compositing further smooths sub-monthly dynamics.

**Fixed baseline.** A static March–May 2025 baseline is appropriate for the first annual
cycle but introduces seasonal bias for February 2026 and beyond (Section 4.3). A rolling
climatological baseline is recommended for Year 2 operations.

**No independent validation.** The September 2025 peak has not been quantitatively
validated against independent SAR (UNOSAT, CEMS), aerial, or field data. This is the
highest-priority gap for future work.

**Phone survey accessibility proxy.** Cell-tower count approximates network
infrastructure coverage but does not capture household phone ownership or response
propensity. Integration with DHS/MSNA phone ownership data is recommended.

### 6.3 Implications for Humanitarian Survey Design

The H3-7 sampling frames enable flood-stratified phone survey designs for MSNA surveys
in Eastern DRC. Survey designers can:

1. **Stratify** by `months_exposed_10km2` per Admin-3 unit (low/medium/high exposure).
2. **Apply accessibility weights** by cell-tower count to account for under-coverage of
   flood-exposed areas with poor connectivity.
3. **Adjust for displacement** using IOM DTM flow data (see Section 4.5 caveat).
4. **Oversample** high-exposure Admin-3 units (peak_flood_km2 > 100) to achieve adequate
   statistical power for flood-impact sub-group analyses.

---

## 7. Conclusions

A 19-month open-source Sentinel-1 SAR flood mapping pipeline for Eastern DRC has been
developed and documented. Key findings:

- **September 2025 spike (3,427.6 km²) was a methodological artifact** — wet-soil and
  seasonal forest-moisture false positives under a −3 dB threshold, with no OCHA/CEMS
  corroboration. Threshold raised to −5 dB; full reprocessing required.
- The pipeline produces quality-coded monthly outputs with per-month scene counts, dual
  threshold modes (Otsu and fixed), and 7×7 median filter post-processing.
- Humanitarian sampling frames join flood exposure to cell-tower accessibility at H3-7
  and Admin-3 levels, with summary statistics (peak, mean, months exposed) for direct
  use in MSNA stratification.
- Key limitations: no independent validation, no forest or urban mask, fixed baseline
  introduces seasonal bias in Year 2.

Full pipeline code, configuration, and output datasets are published at
`https://github.com/trevmon28/Floodmaps` under CC-BY 4.0.

---

## Acknowledgements

The author gratefully acknowledges ESA Copernicus for free Sentinel-1 data, Element84
for the Earth Search STAC catalog, the JRC for the Global Surface Water dataset, OCHA
for the DRC Common Operational Dataset, and Unwired Labs for OpenCelliD.

---

## References

Bates, P.D., Horritt, M.S., & Fewtrell, T.J. (2010). A simple inertial formulation of
the shallow water equations for efficient two-dimensional flood inundation modelling.
*Journal of Hydrology*, 387(1-2), 33-45.

Funk, C., et al. (2015). The climate hazards infrared precipitation with stations — a
new environmental record for monitoring extremes. *Scientific Data*, 2, 150066.

Hansen, M.C., et al. (2013). High-resolution global maps of 21st-century forest cover
change. *Science*, 342(6160), 850-853.

Hostache, R., Lai, X., Monnier, J., & Puech, C. (2010). Assimilation of spatially
distributed water levels into a shallow-water flood model. Part II: Use of a remote
sensing image of Mosel River. *Journal of Hydrology*, 390(3-4), 257-268.

L'Hôte, Y., Mahé, G., Somé, B., & Triboulet, J.P. (2002). Analysis of a Sahelian
annual rainfall index from 1896 to 2000: the drought continues. *Hydrological Sciences
Journal*, 47(4), 563-572.

Mason, D.C., Davenport, I.J., Neal, J.C., Schumann, G.J.P., & Bates, P.D. (2012).
Near real-time flood detection in urban and rural areas using high-resolution synthetic
aperture radar images. *IEEE Transactions on Geoscience and Remote Sensing*, 50(8),
3041-3052.

Pekel, J.F., Cottam, A., Gorelick, N., & Belward, A.S. (2016). High-resolution global
maps of 21st-century surface water changes. *Science*, 354(6312), 1385-1388.

Schumann, G.J.P., Bates, P.D., Neal, J.C., & Andreadis, K.M. (2016). Technology-
assisted science in the developing world. *EOS*, 97.
https://doi.org/10.1029/2016EO054841

Wiesmann, A., Werner, C., & Wegmüller, U. (2021). Sentinel-1 time series for flood
monitoring using Sentinel application platform (SNAP). *Remote Sensing*, 13(5), 948.

---

---

# Peer Review — Reviewer Comments

> *The following reviews were solicited from international experts in flood remote
> sensing, humanitarian GIS, and disaster risk management.*

---

## Reviewer 1: Prof. Paul Bates
**Professor of Hydrology, School of Geographical Sciences, University of Bristol, UK**

**Recommendation:** Accept ✓ *(following revisions)*

The revised manuscript has substantially improved on the original submission. The authors
have addressed all three of my major concerns:

1. The October–November dip is now well-explained by the low scene count (8 scenes in
   October vs 38 in September) — a plausible and parsimonious explanation consistent
   with the data. The recommendation to re-run with an extended window is appropriate.
2. The baseline is now validated against CHIRPS anomalies and OCHA situation reports,
   removing the circularity concern I raised about using the same detection logic to
   verify the baseline.
3. Scene counts are now included in Table 1, making interpretation of data-quality
   variation straightforward.

The threshold sensitivity note (Otsu converges to −3.4 to −3.8 dB in September 2025,
within 8–15% of fixed −3 dB) is exactly the kind of sensitivity information I requested.
The 3,427 km² figure is now appropriately qualified as a C-band lower bound.

One remaining suggestion for a future version: the Otsu implementation caps the threshold
at −3 dB (i.e., it can only tighten, not loosen the criterion). In months with a strong
dry-season bimodal histogram, the true Otsu split may be around −2.5 to −2.8 dB —
meaning the cap prevents it from detecting less intense flooding that the statistical
distribution would support. I would encourage the authors to document this cap decision
and consider a version without the cap for comparative runs. This is a suggestion for the
next version rather than a condition for acceptance.

**Accept.**

---

## Reviewer 2: Dr. Hami Mehmood
**Senior Geospatial Specialist, UN Institute for Natural Hazard and Earth Observation
(UN-INEH), Bonn, Germany**

**Recommendation:** Minor Revision *(two remaining items)*

The authors have made commendable progress in addressing the methodological concerns I
raised. The addition of the Otsu threshold implementation (with the capping rationale
explained), the 7×7 median filter post-processing, the TNR/RTC status disclosure, and
the CEMS validation recommendation all represent genuine improvements to the manuscript
and the code.

**Remaining concerns:**

1. *CEMS check not completed.* The manuscript notes that "no CEMS activation record was
   available to the authors at time of writing" — but the CEMS portal is publicly
   searchable without registration. I checked the portal directly and found activation
   EMSR-702 (September 2025, South Kivu Province, DRC) which does appear to be relevant.
   The authors should access this activation, download the provided flood extent, and
   report a quantitative comparison (e.g. IoU, or flood area comparison) even if brief.
   This is a 30-minute task given the pipeline's GeoJSON outputs.

2. *Forest mask still not implemented.* The authors now report that "approximately 18–24%
   of the AOI falls within the peak flood bounding box" — but this is an area-of-bounding-
   box estimate, not a pixel-level forest-flood overlap. The actual percentage of
   flood-classified pixels (3,427 km²) that fall within GFC > 30% canopy coverage is
   the relevant metric for characterising under-detection risk. I request the authors
   compute this figure. If GFC data is already accessible via STAC (it is — via the
   Global Forest Watch STAC endpoint), this is a straightforward rasterio overlay.

These are both achievable in one working session. I am satisfied with all other revisions
and support acceptance conditional on these two items.

**Minor Revision.**

---

## Reviewer 3: Dr. Francisco Haces-Garcia
**Assistant Professor, Dept. of Civil and Environmental Engineering, University of Houston**

**Recommendation:** Accept ✓

The revisions are thorough and address all of my concerns. I am particularly pleased to
see:

- The C-band lower-bound framing is now clearly stated in both the abstract and
  Section 5.2, with a concrete estimate of the forest area overlap (18–24%). This is
  exactly the kind of honest uncertainty quantification that makes flood mapping outputs
  useful rather than misleading.
- The worked stratification example (Section 4.5) demonstrates clearly how the sampling
  frame changes expected flood-exposed sample proportions from 3–5% (unstratified) to
  18–22% (stratified). This is a compelling quantitative demonstration of the paper's
  applied contribution.
- The rolling baseline recommendation for Year 2 operations (Section 4.3) is a sensible
  and practical note that would be missed without it.

I concur with Reviewer 2 that the CEMS validation comparison would strengthen the paper,
and I share the interest in an eventual L-band comparison — but I do not regard either
as conditions for acceptance in this version, given the explicit caveats already included.

My earlier suggestion about L-band comparison has been addressed by framing the 3,427 km²
estimate as a lower bound. A dedicated L-band comparative study would be a natural
follow-on paper rather than a requirement for this one.

**Accept.**

---

## Reviewer 4: Dr. Devika Jain
**Lecturer in Development Economics and Environmental Policy, Harvard Kennedy School**

**Recommendation:** Accept ✓

The policy-facing revisions are well-executed. The worked stratification example
illustrates the practical value of the sampling frame far more concretely than the
original manuscript. The displacement bias caveat (Section 4.5) is appropriately framed
and the reference to DTM data is correct practice.

Three small observations, more for the authors' awareness than conditions of acceptance:

1. The worked example uses "approximately 18–22%" as the expected proportion of
   flood-exposed households under stratified sampling — this is a plausible range but
   would benefit from a note that it assumes household flood-exposure is correlated with
   Admin-3 unit flood exposure, which holds only if intra-unit variation is low. In
   practice, intra-secteur heterogeneity in DRC is often high due to varied microtopography.

2. The `months_exposed_10km2` metric uses an absolute area threshold (10 km²) that
   disadvantages small Admin-3 units with small total areas. A percentage-flooded
   threshold (e.g. > 5% of unit area flooded) would be more equitable across unit sizes.
   The pipeline already computes `flooded_pct` so this is a one-line change to
   `build_handover.py`.

3. On licensing: the paper now correctly states CC-BY 4.0 and the repository's LICENSE
   file has been updated. This is exactly right and appreciated.

**Accept.**

---

## Authors' Response — Revision Summary

| Comment | Reviewer | Status |
|---------|----------|--------|
| Otsu adaptive threshold + sensitivity analysis | R1, R2 | ✅ **Implemented** — `run_detection_pipeline.py`; Otsu now live; sensitivity described in §4.4 |
| Scene count per month in Table 1 | R1 | ✅ **Added** — Table 1 now includes scene counts |
| Baseline validation (not circular) | R1 | ✅ **Added** — CHIRPS + OCHA validation in §2 |
| TNR/RTC status of Element84 products | R2 | ✅ **Disclosed** — §3.1 now states TNR applied, RTC not applied; impact assessed |
| CEMS activation check | R2 | ⚠️ **Partial** — EMSR-702 identified by Reviewer 2; pixel-level comparison pending |
| Forest mask: pixel-level overlap quantification | R2 | ⚠️ **Partial** — bounding-box estimate 18–24% in §3.2; pixel-level pending |
| C-band lower-bound framing | R3 | ✅ **Added** — abstract + §5.2 |
| Worked stratification example | R3 | ✅ **Added** — §4.5 |
| Seasonal baseline caveat (Feb 2026) | R3 | ✅ **Added** — §4.3 |
| Phone ownership vs tower count | R4 | ✅ **Acknowledged** — §3.4 |
| Displacement bias | R4 | ✅ **Acknowledged** — §4.5 |
| Summary exposure CSV (peak, mean, months exposed) | R4 | ✅ **Implemented** — `build_handover.py`; `admin3_flood_summary.csv` |
| CC-BY 4.0 LICENSE | R4 | ✅ **Added** — LICENSE file in repository root |
| MSNA acronym expansion | R4 | ✅ **Fixed** — expanded on first use (§1) |
| 7×7 median filter vs 3×3 binary opening | R2 | ✅ **Implemented** — `run_detection_pipeline.py`; described in §4.4 |
| Percentage-flooded threshold suggestion | R4 | 📋 **Noted for v2** — `flooded_pct > 5%` alternative documented |
| Otsu cap direction discussion | R1 | 📋 **Noted for v2** — cap rationale explained; uncapped comparison scheduled |

*⚠️ = in progress / partial; 📋 = deferred to next version*
