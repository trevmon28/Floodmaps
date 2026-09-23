# Handover — what changed, September 2026

**Status: preliminary.** The figures below supersede all earlier releases, but the
detection cut-off behind them is not yet validated against ground observation. Use them
as best current estimates, not settled measurements.

---

## In one paragraph

Two months that were previously unusable are now in the dataset, and the way flooding is
detected was corrected. Every flood area figure has changed. If you hold numbers from any
earlier version, replace them.

---

## 1. June 2026 was never a data gap

It had been recorded as permanently missing, blamed on corrupt satellite files. That was
wrong. The data was always there; a single transient download error aborted the whole
month's processing and the failure was logged as corrupt data instead of retried.

Re-processed, June 2026 has the **second-best satellite coverage in the entire 19-month
series** (23.6% of the area imaged, against 6–8% either side). Downloads are now processed
in blocks with a deferred retry, so one bad read can no longer take down a month.

July 2026 was also re-pulled as a complete month, having previously been captured
mid-month at 2.5% coverage.

## 2. Flood detection was too permissive

Flooding was being identified purely by a *drop* in radar brightness against a dry-season
baseline. That let through pixels far too bright to be standing water — in July 2026,
pixels at the brightness of ordinary dry ground were counted as flooded simply because
they had dimmed.

Three corrections: a pixel must now also be dark in absolute terms; the exclusion zone
around permanent lakes and rivers was widened by 300 m; and map cleanup now runs last
instead of midway, so surviving patches hold together.

## 3. What the numbers do

| Month | Before | After | |
|-------|--------|-------|---|
| Sep 2025 (peak) | 217.2 | **209.9** | −3% |
| Jun 2026 | 35.4 | **23.3** | −34% |
| Feb 2026 | 17.4 | 11.1 | −36% |
| Jul 2026 | 31.0 | **6.5** | −79% |
| Jul / Aug / Oct 2025 | 0.2 / 0.4 / 0.9 | 0.0 | −100% |

Series total: 342.6 → **271.4 km²** across 17 valid months.

The correction is targeted, not across-the-board — which is the main reason to trust it.
The well-corroborated September 2025 peak barely moved, while the most contaminated month
lost four-fifths, and three months that showed a trace of flooding now correctly show
none. Spatial quality improved in step: July 2026 went from 610 scattered fragments
(typically a single pixel each) to 23 coherent patches.

## 4. Independent cross-check

Checked against Copernicus EMS, the International Charter, GDACS and UN-SPIDER. Full
detail in `validation_2026-09.md`. Three things to know:

- **Both documented in-area flood events were detected** — May 2025 in South Kivu, and
  February–March 2026 in North Kivu. The 2026 event ran 11 Feb – 5 Mar and the data shows
  it across both months, matching its duration.
- **The two largest months have no independent corroboration** — September 2025 and June
  2026. This does not mean they are wrong: the alerting systems used are driven by
  population impact, and a large flood in a sparsely populated floodplain may raise no
  alert. But it is the main open question in the dataset.
- **The dry-season baseline contains a documented flood.** The baseline is built from
  March–May 2025, and an in-area flood is recorded 1–14 May 2025. Where that flood stood,
  the baseline is wetter than it should be, which *suppresses* later detection in exactly
  the places most prone to flooding. This needs fixing and is not fixed yet.

## 5. Where flooding is reported has shifted

| Rank | Before | After |
|------|--------|-------|
| 1 | Irumu 10.27 | Irumu 7.25 |
| 2 | Uvira 8.82 | Mambasa 4.04 |
| 3 | Kabare 5.33 | Rutshuru 3.06 |
| 4 | Mambasa 4.12 | **Uvira 1.29 (−85%)** |
| 5 | Bukavu 3.28 | — |

Only four Admin-3 units in the whole area now report any flooding at all.

The pattern makes physical sense: the units that collapsed (Uvira, Bukavu, Kabare) sit on
Lake Tanganyika and Lake Kivu, where the false positives were concentrated; the units that
held steady (Irumu, Mambasa, Rutshuru) are inland.

**Uvira was investigated specifically** (23 Sep), because it is the most documented
flood-prone populated place in the area and its flooding is by nature close to the shore —
exactly what the new exclusion zone removes. The check clears the change: Uvira's entire
previous figure came from **July 2026 alone**, the single most contaminated month, and it
shows essentially nothing in every other month including ones with documented flood events.
No flood event is recorded anywhere in DR Congo for July 2026, and the removed pixels are
radar-darker than typical flooding — they look like lake and river surface, not flooded
land. A small residual (about 2.5 km²) sits close enough to the shore to be genuinely
ambiguous, so Uvira figures still warrant a second look before targeting, but the earlier
"do not use" warning is withdrawn.

---

## Reading the data

- Compare months using `flooded_pct`, not `flood_area_km2`. Satellite coverage ranges from
  0.9% to 50.5% of the area between months, and different months image different places —
  no location is covered in all 19 months. A bigger area can simply mean a better-covered
  month.
- `near_water_km2` / `away_water_km2` split each month by distance to permanent water, so
  you can see how much sits close to lakes and rivers where false positives concentrate.
- The September 2025 peak is largely **outside** the three target provinces: of 209.9 km²,
  only a few km² falls inside North Kivu, South Kivu and Ituri. If your work is scoped to
  those provinces, use the Admin-3 tables rather than the area-wide totals.

## What is not done

1. The −12 dB detection cut-off is not calibrated against ground truth. It remains the
   single most influential setting — though testing it across a range (−10 to −14 dB)
   shows the published figures are not finely balanced on it: between −10 and −12 the
   corroborated months barely move and the ranking of months never changes.
2. The contaminated baseline is identified but not rebuilt.
3. The VH radar band — a better water discriminator than the geometric exclusion zone —
   has now been acquired for all months from 2026-01 but is **not yet switched on**.
   Enabling it may allow a smaller exclusion zone and recover genuine near-shore signal in
   Uvira. That is the next thing worth doing, and it should be done before the exclusion
   zone is revisited.
