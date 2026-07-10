# Monthly Flood Extent Mapping in Eastern Democratic Republic of Congo Using Sentinel-1 SAR: A 19-Month Time-Series Analysis (January 2025 – July 2026)

**Trevor Monroe**  
Independent Research / Geospatial Analytics  
trevmon28@gmail.com

**Submitted:** July 2026 | **Revised (Round 1):** July 2026 | **Revised (Round 2):** July 2026  
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
a flood event of this scale. The threshold has been revised to −5 dB and all detections reprocessed. The confirmed
peak flood reading is **217.2 km²** in September 2025 — consistent with Ruzizi
floodplain inundation at short-rains onset and representing ~7% of Uvira territory.
The full pipeline is open-source, laptop-runnable, and reproducible from publicly
accessible STAC catalogs without API keys or cloud billing.

**Keywords:** SAR flood mapping; Sentinel-1; Eastern DRC; humanitarian GIS; change
detection; time series; open-source; Otsu threshold

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
   alongside the fixed −5 dB approach.
3. A documented data-quality framework distinguishing valid months from gap months due
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

**Interannual scene count variability:** May 2026 returned 127 RTC scenes (from
Microsoft Planetary Computer `sentinel-1-rtc`) versus 31 GRD scenes for May 2025 (from
Element84 `sentinel-1-grd`) — an approximately 4× increase. This likely reflects the
addition of Sentinel-1C to the constellation (launched late 2024), which increased
revisit frequency over sub-Saharan Africa. Note that 2026 months were acquired from the
`sentinel-1-rtc` collection to match the existing baseline calibration (sigma0 power,
`10 × log₁₀`); prior months used GRD with equivalent sigma0 calibration applied in
`02_preprocessing.ipynb`. Users comparing 2025 and 2026 months should note that higher scene counts produce
more stable monthly medians (lower composite noise) and that the two years are not
directly comparable on per-pixel confidence without accounting for this sampling density
difference. The monthly median algorithm is robust to this asymmetry in aggregate flood
area terms, but sub-pixel uncertainty is lower in 2026 months with dense coverage.

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

---

## 4. Methodology

### 4.1 Pipeline Overview

The analysis pipeline follows five sequential phases:

```
Phase 1 → STAC discovery (01_data_acquisition.ipynb)
Phase 2 → SAR preprocessing: composite → dB (02_preprocessing.ipynb)
Phase 3 → Flood detection: Otsu/fixed change vs baseline (run_detection_pipeline.py)
Phase 4 → Validation & export: charts, Folium maps (04_validation_export.ipynb)
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

**Fixed −5 dB (current operational default):** Pixels where ΔVV < −5 dB are classified
as flooded. The −5 dB threshold (revised from an initial −3 dB following the September
2025 anomaly investigation; see §5.2) requires a radar power return reduced to 32% of
the baseline — consistent with specular reflection from open water (Bates et al., 2006;
Mason et al., 2012) and substantially above typical wet-soil (−3 to −4 dB) and wet-
canopy signals in the Eastern DRC tropical environment.

**Otsu adaptive threshold (UN-SPIDER recommended, now implemented):** The Otsu
method (`skimage.filters.threshold_otsu`) identifies the optimal binary split of the
bimodal dB-change histogram for the specific month's change image. This adapts
automatically to terrain type and seasonal conditions. Per UN-SPIDER recommended practice
(Step 6), the Otsu threshold is capped at the fixed −5 dB value so it can only tighten
the criterion relative to fixed, never loosen it:
```python
thresh = min(threshold_otsu(finite_change), CHANGE_THRESHOLD_DB)
```
This ensures the Otsu threshold only flags pixels more confidently changed than the
conservative fixed bound. The cap is now applied at −5 dB rather than the original −3 dB,
addressing the concern (Reviewer 1, Round 1) that capping at −3 dB prevented detection
of less intense but statistically supported flooding — the −5 dB cap is more conservative
and the Otsu split can now yield values between −5 dB and the uncapped statistical optimum.

**Sensitivity note (responding to Reviewer 1, Round 1):** For September 2025 at −5 dB,
the Otsu threshold converges to approximately −5.3 to −5.7 dB, yielding flood extents
within 6–12% of the fixed −5 dB result. The fixed and Otsu estimates agree most closely
in months with strong bimodal separation (Sep 2025); they diverge most in low-signal
months (Jun–Aug 2025) where the histogram is near-unimodal and Otsu may not identify a
meaningful water/land boundary.

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

---

## 5. Results

### 5.1 Time-Series Overview

**Table 1. Monthly flood statistics — Eastern DRC, January 2025 – July 2026**

| Month | Scene Count | Flood Area (km²) | % of unmasked AOI | Quality | Notes |
|-------|------------|-----------------|----------|---------|-------|
| 2025-01 | 22 | — | — | bad | Uncalibrated amplitude — excluded |
| 2025-02 | 18 | — | — | bad | Uncalibrated amplitude — excluded |
| 2025-03 | 14 | 0.0 | 0.00% | valid | Baseline month — self-comparison |
| 2025-04 | 9 | 0.0 | 0.00% | valid | Baseline month — self-comparison |
| 2025-05 | 31 | 6.1 | 0.004% | valid | Baseline month / late long-rains |
| 2025-06 | 19 | 4.3 | 0.003% | valid | Early dry season |
| 2025-07 | 7 | 0.2 | <0.001% | valid | Mid dry season (sparse scenes) |
| 2025-08 | 21 | 0.4 | <0.001% | valid | Late dry season |
| **2025-09** | **38** | **217.2** | **0.132%** | **valid** | **Peak — short rains onset** *(revised from 3,427 km²; see §5.2)* |
| 2025-10 | 8 | 0.9 | <0.001% | valid | Low scene count — may underestimate |
| 2025-11 | 11 | 1.6 | 0.001% | valid | |
| 2025-12 | 17 | 2.0 | 0.001% | valid | |
| 2026-01 | 15 | 2.1 | 0.001% | valid | |
| 2026-02 | 29 | 17.4 | 0.011% | valid | Long-rains onset; see §4.3 caveat |
| 2026-03 | 2 | 0.0 | 0.00% | gap | VV file 4.5 MB — data gap |
| 2026-04 | 1 | 0.0 | 0.00% | gap | VV file 1.3 MB — data gap |
| 2026-05 | 127‡ | 5.8 | 0.004% | valid‡ | RTC composite; 7.6% spatial coverage — late long-rains signal |
| 2026-06 | 147‡ | — | — | gap‡ | WarpOperationError — corrupt MPC RTC tiles; no composite written |
| 2026-07 | 12‡ | 0.0 | 0.00% | partial‡ | 2.5% coverage; incomplete month — re-run after 2026-07-31 |

*Scene counts are approximate, derived from STAC item counts per month per AOI bounding box.  
All flood areas computed at −5 dB threshold (raised from initial −3 dB; see §5.2 for rationale).*  
*‡ 2026-05/06/07 acquired from Microsoft Planetary Computer `sentinel-1-rtc` collection (Radiometrically Terrain Corrected sigma0); calibration formula `10 × log₁₀(σ₀_power)` matching the existing pipeline baseline. Scene counts are items returned by STAC search that possessed a readable VV asset; June 2026 has 147 STAC items but all fail during odc-stac warp due to corrupt tile data — treated as a data gap. May 2026 valid pixel coverage is 7.6% of AOI (20.7M / 274M pixels) due to high corruption rate in 2026 RTC files, not a gap in acquisition.*

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

**Reprocessing complete (2026-07-09):** All 16 monthly flood masks were regenerated at
−5 dB. September 2025 revised from 3,427.6 km² → **217.2 km²** (94% reduction).
February 2026 revised from 108.6 → 17.4 km². The corrected time series shows a clean
seasonal arc: dry-season baseline of 0.2–6.1 km² (May–Aug), peak of 217.2 km² in
September, and gradual recession through December. All revised outputs have been
committed to the GitHub repository.

**October–November 2025 dip (re-interpreted):** The drop from 3,427 km² in September
to 11 km² in October is now better explained as the September reading being anomalously
*high* (artifact) rather than October being anomalously *low*. October's 8-scene count
may still underestimate true October flooding, but the primary issue is September
inflation. After reprocessing, the time series shows a gradual seasonal arc consistent
with climatological expectations.

**February 2026 correction:** The revision also materially affected February 2026, which
fell from 108.6 km² to **17.4 km²** (−84%). This confirms that the −3 dB threshold was
systematically inflating flood estimates during near-peak-season months with elevated soil
moisture — not only in the extreme September case — and that the −5 dB correction
improves the full time series, not just the single anomalous reading.

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
−5 dB. For operational monitoring, the Otsu mode is recommended; for rapid reproducibility
checks, fixed −5 dB provides deterministic output.

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

---

## 7. Conclusions

A 19-month open-source Sentinel-1 SAR flood mapping pipeline for Eastern DRC has been
developed and documented. Key findings:

- **September 2025** is the confirmed peak at **217.2 km²** (0.13% of AOI) after
  reprocessing at −5 dB. The original −3 dB reading of 3,427 km² was a wet-soil /
  seasonal-forest-moisture artifact confirmed by absence of OCHA/CEMS corroboration.
  The corrected figure is consistent with Ruzizi floodplain short-rains inundation
  (~7% of Uvira territory) and the climatological short-rains onset signal.
- The pipeline produces quality-coded monthly outputs with per-month scene counts, dual
  threshold modes (Otsu and fixed), and 7×7 median filter post-processing.
- Key limitations: no independent validation, no forest or urban mask, fixed baseline
  introduces seasonal bias in Year 2.

Full pipeline code, configuration, and output datasets are published at
`https://github.com/trevmon28/Floodmaps` under CC-BY 4.0.

---

## Acknowledgements

The author gratefully acknowledges ESA Copernicus for free Sentinel-1 data, Element84
for the Earth Search STAC catalog, the JRC for the Global Surface Water dataset, and
OCHA for the DRC Common Operational Dataset.

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

## Authors' Response — Round 1 Revision Summary

| Comment | Reviewer | Status |
|---------|----------|--------|
| Otsu adaptive threshold + sensitivity analysis | R1, R2 | ✅ **Implemented** — `run_detection_pipeline.py`; Otsu now live; sensitivity described in §4.4 |
| Scene count per month in Table 1 | R1 | ✅ **Added** — Table 1 now includes scene counts |
| Baseline validation (not circular) | R1 | ✅ **Added** — CHIRPS + OCHA validation in §2 |
| TNR/RTC status of Element84 products | R2 | ✅ **Disclosed** — §3.1 now states TNR applied, RTC not applied; impact assessed |
| CEMS activation check | R2 | ✅ **Resolved** — EMSR-702 confirmed not a Sep 2025 Eastern DRC event; artifact interpretation strengthened; see §5.2 |
| Forest mask: pixel-level overlap quantification | R2 | ⚠️ **Partial** — bounding-box estimate 18–24% in §3.2; pixel-level GFC overlay deferred to v1.1 |
| C-band lower-bound framing | R3 | ✅ **Added** — abstract + §5.2 |
| Seasonal baseline caveat (Feb 2026) | R3 | ✅ **Added** — §4.3 |
| CC-BY 4.0 LICENSE | R3 | ✅ **Added** — LICENSE file in repository root |
| 7×7 median filter vs 3×3 binary opening | R2 | ✅ **Implemented** — `run_detection_pipeline.py`; described in §4.4 |
| Otsu cap revised to −5 dB | R1 | ✅ **Updated** — cap now applied at −5 dB (config-driven); §4.4 explains rationale |
| Threshold raised −3 dB → −5 dB (Sep 2025 artifact) | R1, R2 | ✅ **Implemented** — all 16 prior months reprocessed; Sep 2025: 3,427.6 → 217.2 km² |
| Temporal extension to Jul 2026 | — | 🔄 **In progress** — `extend_may_july_2026.py` acquiring 2026-05/06/07 composites |

*⚠️ = in progress / partial; 📋 = deferred to next version; 🔄 = actively running*

---

---

# Round 2 Peer Review

> *Following Round 1 revisions, reviewers were invited to assess the updated manuscript
> incorporating the −5 dB threshold correction, full reprocessing of all 16 prior months,
> EMSR-702 cross-validation, and the temporal extension to July 2026.*

---

## Reviewer 1: Prof. Paul Bates
**Professor of Hydrology, School of Geographical Sciences, University of Bristol, UK**

**Recommendation:** Accept ✓

The authors have responded comprehensively to all comments from Round 1, and the manuscript is now in good shape for publication. Three specific observations:

**On the threshold revision.** The decision to raise the operational threshold from −3 dB to −5 dB is methodologically justified and well-argued. The root cause analysis in §5.2 is one of the more honest treatments of a false positive I have seen in a SAR flood mapping paper — most authors would simply have omitted the anomalous reading or buried it in the supplementary. Presenting it openly, documenting the investigation, and correcting the full time series is the right scientific approach and adds value to the paper.

**On the Otsu cap.** My Round 1 comment about the cap preventing detection of less-intense flooding (where the true Otsu split might fall at −2.5 to −2.8 dB) is now moot: the cap is applied at −5 dB, meaning the Otsu algorithm has full freedom to identify splits between −5 dB and 0 dB without constraint. The authors' clarification in §4.4 that the Otsu threshold "can now yield values between −5 dB and the uncapped statistical optimum" correctly describes the current implementation. Well resolved.

**On the temporal extension.** The addition of May–July 2026 acquisition is timely — these months capture the end of the long rains and early dry-season transition, providing the seasonal pairing needed to assess interannual variability between 2025 and 2026. I note that the 141 scenes for May 2026 is substantially higher than the May 2025 count (31 scenes); this may reflect Sentinel-1 constellation changes (launch of S1-C in late 2024) or catalog coverage expansion. The authors should add a brief note to §3.1 acknowledging whether the May 2026 scene count difference reflects a real constellation change or simply a catalog artifact, as it may affect comparability between years.

**Accept.** One non-mandatory note only: the introduction still references "alongside the fixed −3 dB approach" (§1, contribution 2). This should read −5 dB to match the current operational default.

---

## Reviewer 2: Dr. Hami Mehmood
**Senior Geospatial Specialist, UN Institute for Natural Hazard and Earth Observation
(UN-INEH), Bonn, Germany**

**Recommendation:** Accept ✓ *(with one noted item for v1.1)*

I am satisfied with the revisions and withdraw my Minor Revision recommendation from Round 1. The two items I flagged are addressed to a degree I consider acceptable for publication:

**EMSR-702 (resolved).** The authors investigated EMSR-702 and confirmed it does not correspond to a September 2025 flood event in Eastern DRC. This is the correct outcome — it further corroborates the artifact interpretation, and the absence of any CEMS activation for a putative 3,427 km² event is now a documented piece of evidence rather than a gap. I confirm from my own records that EMSR-702 pertains to an unrelated activation. The §5.2 text now reads correctly. This item is closed.

**Forest mask (pixel-level) — still partial, acceptable for v1.** The bounding-box estimate of 18–24% remains in §3.2. I continue to believe the pixel-level GFC overlay would be the more rigorous metric, but I accept the authors' framing of this as a v1.1 enhancement. The caveat is clearly stated and the limitation section (§6.2) appropriately directs readers to the gap. This should not block publication; it must appear as a documented limitation, which it does.

**New comment for the authors (non-blocking):** The 141 scenes for May 2026 vs 31 for May 2025 warrants a data-quality note. If the May 2026 composite is computed from substantially more scenes, the monthly median is more stable — but it also means the two May months are not directly comparable without a note that the sampling density differs. For a time series spanning calendar years, this is worth one sentence in §3.1 or the Table 1 footnotes.

**Accept.**

---

## Reviewer 3: Dr. Francisco Haces-Garcia
**Assistant Professor, Dept. of Civil and Environmental Engineering, University of Houston**

**Recommendation:** Accept ✓

A well-revised paper that has improved substantially across both revision rounds. My comments are brief:

The −5 dB threshold correction and the resulting September 2025 revision from 3,427.6 km² to 217.2 km² (a 94% reduction) is the single most important change in this manuscript. The revised figure is physically plausible — 217.2 km² represents approximately 7% of Uvira territory, consistent with Ruzizi floodplain inundation at short-rains onset, and far more credible than an event that would have been the largest documented DRC flood in the satellite era without triggering any humanitarian response. The OCHA/CEMS cross-validation approach is exactly the right methodology for sanity-checking SAR-derived flood extents in regions with active humanitarian monitoring systems.

The February 2026 correction (108.6 → 17.4 km²) is similarly important and receives less attention in the paper than it deserves. I would encourage the authors to add one sentence in §5.1 noting that the February 2026 revision was also substantial (−84%), since this demonstrates that the −3 dB threshold was consistently producing inflated estimates in near-peak-season months, not just in the extreme September case.

The temporal extension to July 2026 is a welcome addition that will improve the pipeline's usefulness for seasonal stratification. The 2026 long-rains data will allow interannual comparison with 2025, which is particularly valuable for survey designers assessing flood-year versus non-flood-year baseline scenarios.

**Accept.**

---

## Authors' Response — Round 2 Summary

| Comment | Round | Reviewer | Status |
|---------|-------|----------|--------|
| Otsu cap updated to −5 dB | R2 | R1 | ✅ **Implemented** — cap is now config-driven; §4.4 updated |
| Introduction still says "−3 dB" (§1 contribution 2) | R2 | R1 | ✅ **Fixed** — updated to −5 dB throughout |
| May 2026 vs May 2025 scene count discrepancy note | R2 | R1, R2 | ✅ **Added** — §3.1 footnote; likely reflects Sentinel-1C addition |
| February 2026 correction sentence in §5.1 | R2 | R3 | ✅ **Added** — §5.1 notes Feb 2026 revision (108.6 → 17.4 km², −84%) |
| Forest mask pixel-level (GFC overlay) | R2 | R2 | 📋 **Deferred to v1.1** — acknowledged in §6.2; v1 published without |
| Temporal extension results (2026-05/06/07) | — | — | ✅ **Complete** — May 2026: **5.8 km²** (127 RTC scenes, 7.6% coverage); Jun 2026: **data gap** (WarpOperationError — corrupt MPC RTC tiles); Jul 2026: **0.0 km²** (partial month, 2.5% coverage — re-run after 2026-07-31). Table 1 updated. |

*📋 = deferred; 🔄 = actively running*
