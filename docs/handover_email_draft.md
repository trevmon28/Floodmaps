# Handover email — draft (September 2026 data release, rev. 2026-09-22)

*Draft for review. Not sent. Replace the bracketed fields before sending.*

---

**Subject:** Eastern DRC flood mapping — revised dataset (Jan 2025 – Jul 2026); all figures updated

Hi [NAME],

I've pushed a revised release of the eastern DRC flood extent dataset. Two things: the
series now runs January 2025 to July 2026 with no missing months, and — more importantly
— **every flood area figure has changed**, because we found and fixed a real weakness in
how flooding was being detected. If you are holding numbers from any earlier version,
please replace them.

**What changed**

*June 2026 is no longer a data gap.* The previous release recorded it as permanently
missing. That turned out to be wrong — the satellite data was always there, and the
month had been lost to a transient failure while downloading it. Re-processed, June is
one of the best-covered months in the entire series (23.6% of the AOI imaged, against
6–8% for the months either side) and shows 23.3 km² of flood extent.

*July 2026 is now a complete month.* The earlier figure came from a mid-month pull that
caught only 2.5% of the AOI. The full month gives 8.5% coverage and 6.5 km².

*The detection method was corrected.* Flooding was being identified purely by a drop in
radar brightness relative to a dry-season baseline. That turned out to let through pixels
far too bright to be standing water — in July, pixels at the brightness of ordinary dry
ground were being counted as flooded, simply because they had dimmed. Flood pixels must
now also be dark in absolute terms, we widened the buffer around lakes and rivers, and we
reordered the processing so map cleanup happens last.

The correction is targeted rather than across-the-board, which is the main reason we trust
it: the well-corroborated September 2025 peak moved only 3% (217.2 → 209.9 km²), while
July 2026 fell 79% (31.0 → 6.5 km²) and three months that had been showing a trace of
flooding (July, August and October 2025) now correctly show none.

The package also fixes two errors in the previous handover: the README quoted 3,428 km²
for the September 2025 peak, which was a superseded figure from an older detection
threshold (the current value is 209.9 km²), and the Admin-3 stratification table had
been silently missing from the CSV folder. Both are corrected. The sampling frames
previously stopped at February 2026 and now run through July.

**Three things to be aware of before you use it**

1. **Compare months using `flooded_pct`, not `flood_area_km2`.** Satellite coverage
   varies enormously month to month — from 0.9% to 50.5% of the AOI — and different
   months image different areas. No pixel in the AOI is covered in all 19 months.
   Absolute km² correlates with how much was imaged (r = 0.50), so a bigger number can
   simply mean a better-covered month. The percentage figure normalises for this.

2. **The detection cut-off is not yet validated.** The new "must be dark in absolute
   terms" rule uses a threshold chosen from the radar statistics of these scenes, not
   from verified flood observations on the ground. It is the single most influential
   setting in the pipeline. The areas are the best current estimates, not validated
   measurements, and checking a few against known flood events would firm them up
   considerably.

3. **The September 2025 peak sits largely outside the three target provinces.** Of its
   217.2 km², only about 3.2 km² falls inside North Kivu, South Kivu and Ituri. If your
   work is scoped to those provinces, the Admin-3 tables are the right place to look
   rather than the AOI-wide totals.

**What's in the package**

- `flood_extents/` — 16 monthly GeoJSON files (WGS84), loadable directly in QGIS or GeoPandas
- `flood_stats.csv` — monthly summary, 17 valid months, now also splitting each month's
  area into near-water and away-from-water so you can see how much sits close to lakes
  and rivers, where false positives concentrate
- `sampling_frames/` — Admin-2, Admin-3 and H3-7 hex GeoParquet, joined to flood data
- `csv/admin3_flood_summary.csv` — per-Admin-3 peak and mean exposure, for survey stratification
- `maps/` — two interactive HTML maps

One note on the maps: opened straight from the unzipped folder, the basemap is CARTO,
which watermarks tiles ("API KEY REQUIRED") for unauthenticated users. It is cosmetic
and does not affect any of the data or boundaries. The maps pick their own basemap — if
you put them on a web server or view them online they switch automatically to
OpenStreetMap, which has no watermark. Either way you can change basemap and toggle
individual flood months from the layer control (top right); the flood polygons are
small, so zoom in to see them.

Happy to walk through any of this, and to run specific months or areas if that's useful.

Best,
[YOUR NAME]

---

## Notes for the sender (delete before sending)

- Attach or link `data/eastern_drc_flood_data.zip` (6.0 MB).
- Caveat 2 (uncalibrated threshold) is the one most likely to cause a misread if skipped.
  The -12 dB ceiling drives every number in the package and rests on scene statistics,
  not ground truth.
- If the recipient asks why June was wrong before: a single transient read error while
  fetching satellite tiles aborted the whole month's download, and the failure was
  recorded as "corrupt data" rather than retried. Downloads are now processed in blocks
  with a deferred retry, so one bad read can no longer take down a month.
- The open-water false-positive issue is now fixed, not just flagged. What remains is
  (a) calibrating the -12 dB ceiling against real flood records, and (b) enabling the
  VH-band water discriminator, which needs 2026-04 to 2026-07 re-acquired with that band.
- If they held figures from the previous release, the biggest movers are July 2026
  (31.0 -> 6.5) and June 2026 (35.4 -> 23.3). September 2025 barely moved.
