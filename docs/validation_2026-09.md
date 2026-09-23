# External Validation Cross-Check — September 2026

**Status: PRELIMINARY.** This is a desk cross-check against public disaster registries.
It is not ground truth and no field or in-situ observation was used. Treat the verdicts
as indicative.

**Scope:** the 19-month flood series (Jan 2025 – Jul 2026) as published after the
absolute-backscatter revision (research paper §5.4).

---

## Sources queried

| Source | How queried | Coverage returned |
|--------|-------------|-------------------|
| Copernicus EMS | `rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations-info/` | 265 activations, 2023-03-24 → 2026-09-15 |
| International Charter | Activation archive (`disasterscharter.org/activations`) | Searched for DRC flood calls |
| GDACS | `gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventlist=FL` | 37 flood events globally, 2025-01 → 2026-09 |
| UN-SPIDER | Knowledge portal | Recommended Practices only — no activation registry |
| Copernicus GFM | News archive | DRC April 2025 reporting |

### Why CEMS turned out to be uninformative here

CEMS returned **zero activations of any category for the DRC across the full 2023–2026
window**. Activation requires an authorised user to request the service, so for this
country the absence of an activation says nothing about whether flooding occurred.

This matters beyond bookkeeping: the July 2026 revision (§5.2) used "no CEMS activation"
as part of its evidence that the September 2025 reading was an artifact. That inference
is withdrawn — see the correction note in §5.2. The wet-soil physical argument is
unaffected and stands on its own.

The International Charter is requestable by the affected state and does show DRC
activity, but its only recent flood call (#961, 10 April 2025) is for **Kinshasa**,
roughly 1,500 km west of this AOI.

**Practical consequence:** GDACS is the only one of these registries that is
impact-driven rather than request-driven, and therefore the only usable corroboration
source for eastern DRC.

---

## GDACS events vs. the detected series

Four DRC flood events fall in the study window. Two are inside the AOI bounding box
(26.8, −5.9, 30.8, 3.0).

| GDACS event | Centroid | In AOI | Detected month(s) | Detected km² |
|-------------|----------|--------|-------------------|--------------|
| 2025-03-28 → 04-17 | 29.18, −5.90 | boundary (Tanganyika) | 2025-03 / 04 — *baseline months* | 0.0 |
| 2025-05-01 → 05-14 | 27.87, −3.27 | ✅ South Kivu | 2025-05 | 6.1 |
| 2025-06-13 → 06-18 | 18.03, −0.79 | ❌ Équateur | 2025-06 | 0.8 |
| 2026-02-11 → 03-05 | 28.71, −0.56 | ✅ North Kivu | 2026-02 + 2026-03 | 11.1 + 5.6 |

### Agreements

- **Both in-AOI events are detected.** Neither is missed.
- **Event duration matches.** The 2026 event runs 11 Feb → 5 Mar and the pipeline reports
  signal in both calendar months, at the two largest magnitudes of that period.
- **True negatives agree.** Months the pipeline now reports as 0.0 km² (2025-07, 2025-08,
  2025-10) have no corresponding GDACS event.

### Disagreements

- **2025-09 (209.9 km², the series peak) has no GDACS event anywhere in DRC.**
- **2026-06 (23.3 km²) has no GDACS event.**

The two largest months in the series are the two without independent corroboration, while
the corroborated events produce comparatively modest areas. This is the inverse of the
desired pattern and is the main open question in the dataset.

**Counter-consideration.** GDACS alerting is driven by modelled population impact. A large
inundation in a sparsely populated floodplain can fail to raise an alert, so absence of a
GDACS event is not evidence of absence of flooding. The September 2025 signal is also
spatially coherent (262 patches, median 17 px, 98.6% of area in patches ≥10 px) and moved
only −3% under a revision that cut July 2026 by 79% — both consistent with real signal.
The finding is *unresolved*, not *refuted*.

---

## Baseline contamination — now externally confirmed

The dry-season baseline is the median of **2025-03, 2025-04 and 2025-05**.

GDACS places an in-AOI flood event at **2025-05-01 → 2025-05-14**, and a second event on
the AOI's southern boundary at 2025-03-28 → 2025-04-17. The baseline therefore
incorporates at least one documented in-AOI flood period.

Consequences:

1. Where the May 2025 flood stood, the baseline is artificially dark, so the apparent
   change in later months is reduced and **detection is suppressed** in exactly the
   locations most prone to flooding.
2. 2025-05 is compared against a baseline that contains 2025-05. A documented flood month
   yielding only 6.1 km² is the expected result of that self-comparison.
3. This compounds the observation-depth problem: **45.6%** of baseline pixels rest on a
   single observation, and only 4.3% have all three, so a single wet scene can set the
   baseline outright for nearly half the area.

This was previously a speculative caveat in `CLAUDE.md`. It is now supported by external
evidence and should be treated as a defect rather than a caveat.

**Suggested remedy (not implemented).** Move the baseline to a window with no in-AOI GDACS
events. The 2025 dry season (Jun–Aug) qualifies, but its coverage is poor (2025-07: 0.9%,
2025-08: 4.1%), so a longer window or a per-pixel low percentile across many months is
likely to be more robust than a 3-month median.

---

## Effect of the September 2026 revision on rankings

### Months

| Rank | Before | After |
|------|--------|-------|
| 1 | 2025-09 — 217.2 | 2025-09 — 209.9 (−3%) |
| 2 | 2026-06 — 35.4 | 2026-06 — 23.3 (−34%) |
| 3 | 2026-07 — 31.0 | 2026-02 — 11.1 |
| 4 | 2026-02 — 17.4 | 2026-07 — 6.5 (−79%) |
| 5 | 2026-03 — 12.0 | 2025-05 — 6.1 (0%) |

The top two are unchanged. The series concentrates: the top month now holds **77.3%** of
all detected area (was 63.4%) and the top three hold **90.0%** (was 82.8%). That
concentration falls on the one month lacking corroboration.

### Regions (Admin-3, peak single-month area)

| Rank | Before | After |
|------|--------|-------|
| 1 | Irumu 10.27 | Irumu 7.25 (−29%) |
| 2 | Uvira 8.82 | Mambasa 4.04 (−2%) |
| 3 | Kabare 5.33 | Rutshuru 3.06 (−2%) |
| 4 | Mambasa 4.12 | Uvira 1.29 (**−85%**) |
| 5 | Bukavu 3.28 | — (nothing remains) |

Only Irumu and Mambasa survive in the top five, and after the revision only **four
Admin-3 units in the entire AOI report any flooding**. Admin-2 behaves identically.

**The pattern is physically coherent.** The units that collapsed — Uvira (−85%), Bukavu
(−100%), Kabare (−100%) — are all lakeshore: Uvira on Lake Tanganyika, Bukavu and Kabare
on Lake Kivu. The units that barely moved — Irumu, Mambasa (inland Ituri) and Rutshuru
(inland North Kivu) — are away from large water bodies. That is the signature expected if
the revision removes open-water false positives rather than real flooding.

**⚠️ But it is also the risk.** Uvira is the most documented flood-prone populated place
in this AOI (recurrent Mulongwe river flooding; ~80,000 people affected in the 2020
event). Its flooding is by nature near-shore and river-mouth — precisely what a 300 m
permanent-water buffer removes. An 85% reduction there may be over-correction in the
place where humanitarian need is highest, and should be examined before these figures are
used for targeting.

---

## Uvira investigation (23 Sep) — resolved

The Admin-3 shift flagged Uvira as a possible over-correction. It is not.

Uvira's entire pre-revision 8.82 km² came from **2026-07 alone**. It records ~0.00 km² in
every other month of the series, including months with externally documented flood events.
Its "peak" was therefore one reading from the single most contaminated month in the series
(2026-07: 99.4% of raw detection on permanent water, 610 fragments at median 1 px).

Decomposition of the 884 pre-revision pixels:

| Removed by | Pixels |
|------------|--------|
| Absolute gate (VV ≥ −12 dB, too bright for water) | 143 |
| Water buffer alone (≤300 m, but dark enough to be water) | 249 |
| Mask-before-smooth reordering | ~363 |
| **Surviving** | **129** |

Two independent lines support the removal:

- **No GDACS event anywhere in DR Congo in July 2026**, so there is nothing to corroborate
  an Uvira flood that month.
- The removed pixels have a **median of −16.7 dB** — darker than typical flood detections
  across this series (−13 to −14 dB) and closer to open water (−23 dB). They look like lake
  and river surface, not inundated land.

**Residual uncertainty.** The 249 pixels (2.49 km²) removed by the buffer alone are dark
*and* near-shore, which describes both a calm-water artifact and genuine riparian flooding.
With no corroborating event and the month being the worst in the series, removal is
defensible — but Uvira figures merit a second look before targeting. The earlier "do not
use for targeting" warning is withdrawn.

---

## Threshold sensitivity (23 Sep)

The −12 dB absolute ceiling is the pipeline's most influential free parameter and is not
ground-truth calibrated, so its effect was swept across −10 to −14 dB on six key months.
Read-only; no outputs were changed.

Flood area (km²) by ceiling:

| Month | Corroborated? | −10 | −11 | **−12** | −13 | −14 |
|-------|---------------|-----|-----|---------|-----|-----|
| 2025-05 | yes | 6.1 | 6.1 | **6.1** | 6.0 | 3.3 |
| 2025-09 | **no** (peak) | 215.6 | 214.6 | **209.8** | 177.9 | 107.4 |
| 2026-02 | yes | 16.9 | 15.2 | **11.1** | 7.4 | 2.8 |
| 2026-03 | yes | 6.0 | 5.9 | **5.6** | 3.5 | 1.6 |
| 2026-06 | **no** | 31.0 | 30.0 | **23.4** | 15.2 | 5.2 |
| 2026-07 | **no** | 6.8 | 6.5 | **6.5** | 6.1 | 4.8 |

Findings:

1. **Not knife-edge between −10 and −12 dB.** The corroborated anchor 2025-05 is unchanged
   (6.1 → 6.1) and the peak moves 3% (215.6 → 209.8). The most sensitive month in that
   band is 2026-02 at 1.51×.
2. **Steep collapse below −12 dB.** At −14 dB, 2026-02 loses 75%, 2026-03 71%, 2026-06 78%.
   −12 dB sits at the knee of the curve, which supports it as the operational value.
3. **No threshold reverses the corroborated/uncorroborated contrast.** The September 2025
   peak is 10–30× larger than any other month at *every* setting tested. The open question
   about that month is therefore a property of the data, not an artifact of this parameter.

This does not remove the need for ground-truth calibration, but it does mean the published
conclusions do not hinge on the exact value within −10…−12 dB.

---

## Recommended next steps

1. **Test the VH/VV ratio discriminator.** VH composites now exist for 2026-01 onward
   (2026-04…07 acquired 2026-09-22). VH is a better open-water discriminator than a
   geometric buffer, so enabling it may permit a **smaller** buffer and recover genuine
   near-shore signal in Uvira. Test VH before revisiting the buffer.
2. ~~Examine Uvira specifically~~ — **done 23 Sep, resolved** (see above). Any further
   work there would target only the 2.49 km² buffer-removed residual.
3. **Rebuild the baseline** from a window with no documented in-AOI flooding.
4. **Calibrate the −12 dB ceiling.** It remains the single most influential free parameter
   and rests on scene statistics, not ground truth.

---

## Reproducing this check

```bash
# CEMS activations (JSON)
curl "https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations-info/?limit=2000"

# GDACS flood events
curl "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventlist=FL&fromDate=2025-01-01&toDate=2026-09-30&countrylist=COD"
```

Note: the ReliefWeb API v1 is decommissioned and v2 requires a registered `appname`, so
ReliefWeb was not queried programmatically for this check.
