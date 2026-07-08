# Project Constitution — DRC Flood Mapping

## Purpose
Produce monthly, calibrated, open-access flood extent maps for Eastern DRC using
Sentinel-1 SAR data. Primary consumers: humanitarian researchers designing phone
surveys on flood impact; UN/NGO situation-report authors.

## Core Principles

1. **Reproducibility first.** Every step from raw STAC item to final GeoJSON must be
   re-runnable from a fresh clone with only publicly accessible data.

2. **Fail loud, skip gracefully.** Detection loops log data-quality flags (gap / bad /
   valid) rather than silently writing zero-flood outputs.  Callers must check the
   `quality` column in flood_stats.csv before interpreting area values.

3. **One source of truth per artefact.** Processed SAR lives in `data/processed/sar/`.
   Flood outputs live in `data/outputs/flood_extent/`.  Researcher-facing assets live
   in `data/handover/`.  Do not duplicate outputs across directories.

4. **No cloud costs by default.** Data access via Element84 Earth Search (free STAC)
   and open raster libraries.  Optional BigQuery/PostGIS paths (GeoSQL integration)
   are additive and cost-gated.

5. **Calibrated data only.** 2025-01 and 2025-02 VV composites are raw amplitude DN —
   exclude them from any baseline or change-detection.  See PIPELINE_STATUS.md.

6. **Document data gaps explicitly.** Months with VV files < 2 MB receive `quality=gap`
   and are excluded from the researcher handover package.

## Quality Gates
- VV file size ≥ 2 MB → processable
- Baseline must use ≥ 3 calibrated months (currently 2025-03/04/05)
- All detection outputs must carry a `quality` label (valid / gap / bad)
- All GeoJSONs must be in EPSG:4326 before export

## Non-Goals
- Real-time or sub-monthly monitoring (cadence limited by Sentinel-1 revisit ~12 days)
- Urban damage assessment (urban specular reflection → false positives; not masked yet)
- ML-based flood classification (threshold-based only; see CLAUDE.md pending items)
