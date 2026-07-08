"""
update_nb04.py
Rewrites 04_validation_export.ipynb to:
 - Handle extended temporal range (Jan 2025 – Jul 2026, 19 months)
 - Display scene counts per month in the summary table
 - Mark 2026-05/06/07 as pending in legend and stats
 - Use the updated NO_DATA_MONTHS set including new gap months
"""
import json
from pathlib import Path

ROOT = Path(r'c:\Users\trevm\Projects\Floodmaps')
NB_PATH = ROOT / 'notebooks' / '04_validation_export.ipynb'

with open(NB_PATH, encoding='utf-8') as f:
    nb = json.load(f)


def code_cell(src):
    return {"cell_type": "code", "execution_count": None,
            "metadata": {}, "outputs": [], "source": src}


def md_cell(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src}


# ── Rebuild cells ──────────────────────────────────────────────────────────────

cells = [

    md_cell("""\
# Notebook 4 — Validation & Export
**Inputs:**
- `data/outputs/flood_extent/flood_stats.csv` — monthly flood area table
- `data/outputs/flood_extent/flood_extent_YYYY-MM.geojson` — flood polygons (WGS84)

**Outputs:**
- Annotated time-series chart (PNG)
- Interactive Folium map (`docs/flood_map_interactive.html`)
- Export inventory table

**AOI:** Eastern DRC — North Kivu, South Kivu, Ituri
**Period:** Jan 2025 – Jul 2026 (19 months; May–Jul 2026 pending acquisition)
**Resolution:** 100 m | **CRS output:** EPSG:32735 (UTM 35S) → reprojected to WGS84
**Detection threshold:** Otsu adaptive (capped at −3 dB) or fixed −3 dB change from baseline (2025-03/04/05)
**Post-processing:** 7×7 median filter (UN-SPIDER recommended practice)

### Data-quality flags
| Flag | Months | Reason |
|------|--------|--------|
| ⚠️ Unreliable | 2025-01, 2025-02 | NB02 stored raw amplitude DN (not dB) — change signal meaningless |
| ⬜ Data gap | 2026-03, 2026-04 | Source VV files < 5 MB — insufficient S1 coverage |
| ⏳ Pending | 2026-05, 2026-06, 2026-07 | SAR acquisition not yet run — execute `extend_may_july_2026.py` |
| ✅ Valid | All other months | Calibrated sigma₀ dB, quality masks applied |
"""),

    code_cell("""\
from pathlib import Path
import os

def _find_project_root():
    in_colab = 'COLAB_GPU' in os.environ or 'COLAB_RELEASE_TAG' in os.environ
    if in_colab:
        import subprocess
        if not Path('Floodmaps').exists():
            subprocess.run(['git', 'clone', 'https://github.com/trevmon28/Floodmaps.git'], check=True)
        return Path('Floodmaps').resolve()
    for candidate in [Path(os.path.abspath('')), Path(os.path.abspath('')).parent]:
        if (candidate / 'config' / 'config.yaml').exists():
            return candidate
    raise FileNotFoundError(
        'Cannot locate config/config.yaml.\\n'
        'Run from the project root or the notebooks/ directory.'
    )

PROJECT_ROOT = _find_project_root()
os.chdir(PROJECT_ROOT)
print('Project root:', PROJECT_ROOT)
"""),

    code_cell("""\
import subprocess, sys, importlib
packages = ["pandas", "geopandas", "shapely", "folium", "matplotlib", "rasterio", "pyyaml"]
missing = [p for p in packages if importlib.util.find_spec(p) is None]
if missing:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet"] + missing)
    print(f"Installed: {missing}")
else:
    print("All packages already present.")
"""),

    code_cell("""\
import json, warnings
import numpy as np
import pandas as pd
import geopandas as gpd
import folium
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import rasterio
warnings.filterwarnings("ignore")

OUTPUT_DIR = Path("data/outputs/flood_extent")
DOCS_DIR   = Path("docs")
DOCS_DIR.mkdir(exist_ok=True)

# Quality flags — update these as new months are confirmed
BAD_MONTHS     = {"2025-01", "2025-02"}               # uncalibrated
NO_DATA_MONTHS = {"2026-03", "2026-04"}               # data gaps
PENDING_MONTHS = {"2026-05", "2026-06", "2026-07"}    # not yet acquired

# Approximate scene counts per month (from STAC searches)
SCENE_COUNTS = {
    "2025-01": 22, "2025-02": 18, "2025-03": 14, "2025-04": 9,
    "2025-05": 31, "2025-06": 19, "2025-07": 7,  "2025-08": 21,
    "2025-09": 38, "2025-10": 8,  "2025-11": 11, "2025-12": 17,
    "2026-01": 15, "2026-02": 29, "2026-03": 2,  "2026-04": 1,
    "2026-05": None, "2026-06": None, "2026-07": None,
}

df = pd.read_csv(OUTPUT_DIR / "flood_stats.csv", index_col="month").sort_index()

# Add any pending months that aren't in the CSV yet
for m in sorted(PENDING_MONTHS):
    if m not in df.index:
        df.loc[m] = {"flooded_pct": None, "flooded_px": 0, "flood_area_km2": None}
df = df.sort_index()

df["quality"] = "valid"
df.loc[df.index.isin(BAD_MONTHS),     "quality"] = "bad"
df.loc[df.index.isin(NO_DATA_MONTHS), "quality"] = "gap"
df.loc[df.index.isin(PENDING_MONTHS), "quality"] = "pending"
df["scene_count"] = df.index.map(SCENE_COUNTS)

print(df[["flood_area_km2", "flooded_pct", "scene_count", "quality"]].to_string())
"""),

    md_cell("## Time-series chart"),

    code_cell("""\
color_map = {
    "valid":   "#1a6faf",
    "bad":     "#cc4444",
    "gap":     "#aaaaaa",
    "pending": "#f0a500",
}
bar_colors = [color_map[q] for q in df["quality"]]

# Use 0 for None values so bars render correctly
plot_areas = df["flood_area_km2"].fillna(0)

fig, ax = plt.subplots(figsize=(15, 5))
bars = ax.bar(df.index, plot_areas, color=bar_colors, width=0.7)

# Annotate peak (valid months only)
valid_df = df[df["quality"] == "valid"]
if not valid_df.empty:
    peak = valid_df["flood_area_km2"].idxmax()
    peak_val = valid_df.loc[peak, "flood_area_km2"]
    ax.annotate(f"{peak_val:,.0f} km²", xy=(peak, peak_val),
                xytext=(0, 8), textcoords="offset points",
                ha="center", fontsize=9, color="#1a3a5c", fontweight="bold")

# Scene count annotations (show low-count months as warning)
for month, row in df.iterrows():
    sc = SCENE_COUNTS.get(month)
    if sc is not None and sc <= 10 and row["quality"] == "valid":
        ax.text(month, (plot_areas[month] or 0) + 15,
                f"n={sc}", ha="center", fontsize=7, color="#cc4444", rotation=90)

ax.set_ylabel("Flooded area (km²)", fontsize=11)
ax.set_xlabel("Month", fontsize=11)
ax.set_title(
    "Monthly Flood Extent — Eastern DRC  (Sentinel-1 SAR, 100 m, Otsu/−3 dB threshold)\\n"
    "Red labels = low scene count months (≤10 scenes); orange = pending acquisition",
    fontsize=11)
ax.tick_params(axis="x", rotation=45)
peak_safe = valid_df["flood_area_km2"].max() if not valid_df.empty else 100
ax.set_ylim(0, peak_safe * 1.18)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

legend_handles = [
    mpatches.Patch(color="#1a6faf", label="Valid"),
    mpatches.Patch(color="#cc4444", label="⚠️ Uncalibrated (2025-01/02)"),
    mpatches.Patch(color="#aaaaaa", label="Data gap (sparse coverage)"),
    mpatches.Patch(color="#f0a500", label="⏳ Pending acquisition"),
]
ax.legend(handles=legend_handles, loc="upper left", fontsize=9)
plt.tight_layout()

chart_path = OUTPUT_DIR / "flood_area_annotated.png"
plt.savefig(chart_path, dpi=150)
plt.show()
print(f"Saved: {chart_path}")
"""),

    md_cell("""\
## Seasonal validation

Eastern DRC has a **bimodal rainfall regime**:

| Season | Months | Expected signal |
|--------|--------|----------------|
| Short rains | Sep – Nov | Peak flood extent |
| Dry season | Jun – Aug | Low flood extent |
| Long rains | Mar – May | Moderate flood extent |
| Short dry | Dec – Feb | Transitional |

### Detected signal vs expectation

| Month | Scenes | Flood area (km²) | Expectation | Assessment |
|-------|--------|-----------------|-------------|------------|
| 2025-03 | 14 | 2.3 | Rains beginning | ✅ Low — consistent |
| 2025-05 | 31 | 26.6 | Peak long rains | ✅ Elevated — consistent |
| 2025-06 | 19 | 14.0 | Transition | ✅ Declining — consistent |
| 2025-07 | 7 | 8.1 | Dry season | ✅ Low — consistent |
| 2025-08 | 21 | 37.6 | Pre-season onset | ✅ Rising — consistent |
| **2025-09** | **38** | **3,427.6** | **Peak short rains** | ✅ **Dominant signal** |
| 2025-10 | **8** | 10.9 | Short rains tail | ⚠️ **Low scene count** — likely under-detection |
| 2025-11 | 11 | 11.4 | Late short rains | ⚠️ Low — check S1 revisit |
| 2025-12 | 17 | 10.2 | Short dry | ✅ Low — consistent |
| 2026-01 | 15 | 9.2 | Short dry | ✅ Low — consistent |
| 2026-02 | 29 | 108.6 | Long rains onset | ✅ Rising — consistent (seasonal bias risk) |

> **Sep 2025 peak (3,427 km²):** Consistent with OCHA-reported Uvira/Butembo flooding.
> C-band lower bound — L-band SAR comparison recommended for forest-covered zones.
> **Oct 2025 (only 8 scenes):** Rapid post-peak dip may reflect data sparsity rather
> than true drainage. Verify against CEMS EMSR-702 (South Kivu, Sep–Oct 2025).
"""),

    md_cell("## Interactive map"),

    code_cell("""\
valid_df  = df[df["quality"] == "valid"]
max_area  = valid_df["flood_area_km2"].max() if not valid_df.empty else 1

def area_to_color(area_km2):
    if max_area == 0 or pd.isna(area_km2):
        return "#1a6faf"
    t = min(area_km2 / max_area, 1.0)
    r = int(0xff + t * (0x1a - 0xff))
    g = int(0xe0 + t * (0x3a - 0xe0))
    b = int(0x66 + t * (0x6e - 0x66))
    return f"#{r:02x}{g:02x}{b:02x}"

m = folium.Map(location=[-1.5, 28.8], zoom_start=6, tiles="CartoDB positron")

geojson_files = sorted(OUTPUT_DIR.glob("flood_extent_????-??.geojson"))

loaded = 0
for gj_path in geojson_files:
    month = gj_path.stem.replace("flood_extent_", "")
    quality = df.loc[month, "quality"] if month in df.index else "valid"
    if quality in ("bad", "pending"):
        continue
    area  = df.loc[month, "flood_area_km2"] if month in df.index else 0
    sc    = SCENE_COUNTS.get(month, "?")
    color = area_to_color(area)
    label = f"{month}  ({area:,.0f} km²,  n={sc} scenes)"
    if quality == "gap":
        label += "  [data gap]"

    with open(gj_path) as f:
        gj = json.load(f)

    fg = folium.FeatureGroup(name=label, show=(month == "2025-09"))
    folium.GeoJson(
        gj,
        style_function=lambda _f, c=color: {
            "fillColor": c, "color": "#0a1a3a",
            "weight": 0.5, "fillOpacity": 0.55,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["month"], aliases=["Month:"]
        ) if gj.get("features") and
             gj["features"][0].get("properties", {}).get("month") else None,
    ).add_to(fg)
    fg.add_to(m)
    loaded += 1

folium.LayerControl(collapsed=False).add_to(m)

aoi_coords = [[-5.9, 26.8], [-5.9, 30.8], [3.0, 30.8], [3.0, 26.8], [-5.9, 26.8]]
folium.PolyLine(aoi_coords, color="#555", weight=1.5, dash_array="6 4",
                tooltip="AOI: Eastern DRC").add_to(m)

map_path = DOCS_DIR / "flood_map_interactive.html"
m.save(str(map_path))
print(f"Loaded {loaded} months  |  Map saved: {map_path}")
m
"""),

    md_cell("## Export inventory"),

    code_cell("""\
rows = []
for gj_path in sorted(OUTPUT_DIR.glob("flood_extent_????-??.geojson")):
    month   = gj_path.stem.replace("flood_extent_", "")
    quality = df.loc[month, "quality"] if month in df.index else "—"
    area    = df.loc[month, "flood_area_km2"] if month in df.index else 0
    sc      = SCENE_COUNTS.get(month, "?")
    size_kb = round(gj_path.stat().st_size / 1024, 1)
    rows.append({"month": month, "scenes": sc, "flood_area_km2": area,
                 "quality": quality, "geojson_kb": size_kb, "file": gj_path.name})

inv = pd.DataFrame(rows)
print(inv.to_string(index=False))
print(f"\\nTotal valid GeoJSONs : {(inv.quality == 'valid').sum()}")
print(f"Interactive map      : docs/flood_map_interactive.html")
print(f"Time-series chart    : data/outputs/flood_extent/flood_area_annotated.png")
"""),

    md_cell("## Summary statistics"),

    code_cell("""\
valid = df[df["quality"] == "valid"]

print("=== Eastern DRC Flood Extent Summary (valid months only) ===")
if not valid.empty:
    print(f"Period         : {valid.index.min()} – {valid.index.max()}")
    print(f"Valid months   : {len(valid)}")
    print(f"Peak month     : {valid['flood_area_km2'].idxmax()}  "
          f"({valid['flood_area_km2'].max():,.1f} km²)  "
          f"[{SCENE_COUNTS.get(valid['flood_area_km2'].idxmax(), '?')} scenes]")
    print(f"Mean (valid)   : {valid['flood_area_km2'].mean():,.1f} km²/month")
    print(f"Total extent   : {valid['flood_area_km2'].sum():,.1f} km² cumulative")
    print()
    print("Top 5 months by flood area:")
    print(valid["flood_area_km2"].sort_values(ascending=False).head().to_string())

print()
print("Pending months (run extend_may_july_2026.py to acquire):")
for m in sorted(PENDING_MONTHS):
    print(f"  {m}")
"""),

]

nb["cells"] = cells

with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print(f"Updated: {NB_PATH}  ({len(cells)} cells)")
