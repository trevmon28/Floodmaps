"""
update_nb04.py — patches NB04 for Mar/Apr 2026 recovery + July partial month.
"""
import json
from pathlib import Path

NB_PATH = Path(r"C:\Users\trevm\Projects\Floodmaps\notebooks\04_validation_export.ipynb")

with open(NB_PATH, encoding="utf-8") as f:
    nb = json.load(f)

def find_cell(cell_id):
    for i, c in enumerate(nb["cells"]):
        if c.get("id") == cell_id:
            return i, c
    raise KeyError(f"Cell {cell_id!r} not found")

def set_code_source(cell_id, src_lines):
    """Replace source of a code cell; clear outputs."""
    i, c = find_cell(cell_id)
    assert c["cell_type"] == "code", f"{cell_id} is not a code cell"
    c["source"] = src_lines
    c["outputs"] = []
    c["execution_count"] = None
    nb["cells"][i] = c

def set_md_source(cell_id, src_lines):
    """Replace source of a markdown cell (no outputs/execution_count)."""
    i, c = find_cell(cell_id)
    assert c["cell_type"] == "markdown", f"{cell_id} is not a markdown cell"
    c["source"] = src_lines
    # remove stale code-cell fields if present
    c.pop("outputs", None)
    c.pop("execution_count", None)
    nb["cells"][i] = c

# ── Cell 0899f1f0  Quality flags (code) ──────────────────────────────────────
set_code_source("0899f1f0", [
    "import json, warnings\n",
    "import numpy as np\n",
    "import pandas as pd\n",
    "import geopandas as gpd\n",
    "import folium\n",
    "import matplotlib.pyplot as plt\n",
    "import matplotlib.patches as mpatches\n",
    "import matplotlib.colors as mcolors\n",
    "import rasterio\n",
    "warnings.filterwarnings(\"ignore\")\n",
    "\n",
    "OUTPUT_DIR = Path(\"data/outputs/flood_extent\")\n",
    "DOCS_DIR   = Path(\"docs\")\n",
    "DOCS_DIR.mkdir(exist_ok=True)\n",
    "\n",
    "# Quality flags\n",
    "BAD_MONTHS     = {\"2025-01\", \"2025-02\"}              # uncalibrated amplitude\n",
    "NO_DATA_MONTHS = {\"2026-06\"}                          # permanent gap -- corrupt MPC RTC tiles\n",
    "PARTIAL_MONTHS = {\"2026-07\"}                          # partial month -- re-run after 2026-07-31\n",
    "PENDING_MONTHS = set()                                # no pending months\n",
    "\n",
    "SCENE_COUNTS = {\n",
    "    \"2025-01\": 22, \"2025-02\": 18, \"2025-03\": 14, \"2025-04\": 9,\n",
    "    \"2025-05\": 31, \"2025-06\": 19, \"2025-07\": 7,  \"2025-08\": 21,\n",
    "    \"2025-09\": 38, \"2025-10\": 8,  \"2025-11\": 11, \"2025-12\": 17,\n",
    "    \"2026-01\": 15, \"2026-02\": 29, \"2026-03\": 107, \"2026-04\": 98,\n",
    "    \"2026-05\": 127, \"2026-06\": 0,  \"2026-07\": 12,\n",
    "}\n",
    "\n",
    "df = pd.read_csv(OUTPUT_DIR / \"flood_stats.csv\", index_col=\"month\").sort_index()\n",
    "\n",
    "for m in sorted(PARTIAL_MONTHS | PENDING_MONTHS | NO_DATA_MONTHS):\n",
    "    if m not in df.index:\n",
    "        df.loc[m] = {\"flooded_pct\": None, \"flooded_px\": 0, \"flood_area_km2\": None}\n",
    "df = df.sort_index()\n",
    "\n",
    "df[\"quality\"] = \"valid\"\n",
    "df.loc[df.index.isin(BAD_MONTHS),     \"quality\"] = \"bad\"\n",
    "df.loc[df.index.isin(NO_DATA_MONTHS), \"quality\"] = \"gap\"\n",
    "df.loc[df.index.isin(PARTIAL_MONTHS), \"quality\"] = \"partial\"\n",
    "df.loc[df.index.isin(PENDING_MONTHS), \"quality\"] = \"pending\"\n",
    "df[\"scene_count\"] = df.index.map(SCENE_COUNTS)\n",
    "\n",
    "print(df[[\"flood_area_km2\", \"flooded_pct\", \"scene_count\", \"quality\"]].to_string())\n",
])

# ── Cell d825291d  Bar chart (code) — add "partial" to color_map ─────────────
set_code_source("d825291d", [
    "color_map = {\n",
    "    \"valid\":   \"#1a6faf\",\n",
    "    \"bad\":     \"#cc4444\",\n",
    "    \"gap\":     \"#aaaaaa\",\n",
    "    \"partial\": \"#8b5cf6\",\n",
    "    \"pending\": \"#f0a500\",\n",
    "}\n",
    "bar_colors = [color_map[q] for q in df[\"quality\"]]\n",
    "\n",
    "plot_areas = df[\"flood_area_km2\"].fillna(0)\n",
    "\n",
    "fig, ax = plt.subplots(figsize=(15, 5))\n",
    "bars = ax.bar(df.index, plot_areas, color=bar_colors, width=0.7)\n",
    "\n",
    "valid_df = df[df[\"quality\"] == \"valid\"]\n",
    "if not valid_df.empty:\n",
    "    peak = valid_df[\"flood_area_km2\"].idxmax()\n",
    "    peak_val = valid_df.loc[peak, \"flood_area_km2\"]\n",
    "    ax.annotate(f\"{peak_val:,.0f} km\\u00b2\", xy=(peak, peak_val),\n",
    "                xytext=(0, 8), textcoords=\"offset points\",\n",
    "                ha=\"center\", fontsize=9, color=\"#1a3a5c\", fontweight=\"bold\")\n",
    "\n",
    "for month, row in df.iterrows():\n",
    "    sc = SCENE_COUNTS.get(month)\n",
    "    if sc is not None and sc <= 10 and row[\"quality\"] == \"valid\":\n",
    "        ax.text(month, (plot_areas[month] or 0) + 15,\n",
    "                f\"n={sc}\", ha=\"center\", fontsize=7, color=\"#cc4444\", rotation=90)\n",
    "\n",
    "ax.set_ylabel(\"Flooded area (km\\u00b2)\", fontsize=11)\n",
    "ax.set_xlabel(\"Month\", fontsize=11)\n",
    "ax.set_title(\n",
    "    \"Monthly Flood Extent \\u2014 Eastern DRC  (Sentinel-1 SAR, 100 m, \\u22125 dB threshold)\\n\"\n",
    "    \"Red labels = low scene count months (\\u226410 scenes); purple = partial month\",\n",
    "    fontsize=11)\n",
    "ax.tick_params(axis=\"x\", rotation=45)\n",
    "peak_safe = valid_df[\"flood_area_km2\"].max() if not valid_df.empty else 100\n",
    "ax.set_ylim(0, peak_safe * 1.18)\n",
    "ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f\"{x:,.0f}\"))\n",
    "\n",
    "legend_handles = [\n",
    "    mpatches.Patch(color=\"#1a6faf\", label=\"Valid\"),\n",
    "    mpatches.Patch(color=\"#cc4444\", label=\"Unreliable (2025-01/02)\"),\n",
    "    mpatches.Patch(color=\"#aaaaaa\", label=\"Data gap\"),\n",
    "    mpatches.Patch(color=\"#8b5cf6\", label=\"Partial month (re-run 2026-08-01)\"),\n",
    "]\n",
    "ax.legend(handles=legend_handles, loc=\"upper left\", fontsize=9)\n",
    "plt.tight_layout()\n",
    "\n",
    "chart_path = OUTPUT_DIR / \"flood_area_annotated.png\"\n",
    "plt.savefig(chart_path, dpi=150)\n",
    "plt.show()\n",
    "print(f\"Saved: {chart_path}\")\n",
])

# ── Cell b3090b17  Interactive map (code) ────────────────────────────────────
set_code_source("b3090b17", [
    "valid_df  = df[df[\"quality\"] == \"valid\"]\n",
    "max_area  = valid_df[\"flood_area_km2\"].max() if not valid_df.empty else 1\n",
    "\n",
    "def area_to_color(area_km2):\n",
    "    if max_area == 0 or pd.isna(area_km2):\n",
    "        return \"#1a6faf\"\n",
    "    t = min(area_km2 / max_area, 1.0)\n",
    "    r = int(0xff + t * (0x1a - 0xff))\n",
    "    g = int(0xe0 + t * (0x3a - 0xe0))\n",
    "    b = int(0x66 + t * (0x6e - 0x66))\n",
    "    return f\"#{r:02x}{g:02x}{b:02x}\"\n",
    "\n",
    "m = folium.Map(location=[-1.5, 28.8], zoom_start=6, tiles=\"CartoDB positron\")\n",
    "\n",
    "geojson_files = sorted(OUTPUT_DIR.glob(\"flood_extent_????-??.geojson\"))\n",
    "\n",
    "loaded = 0\n",
    "for gj_path in geojson_files:\n",
    "    month = gj_path.stem.replace(\"flood_extent_\", \"\")\n",
    "    quality = df.loc[month, \"quality\"] if month in df.index else \"valid\"\n",
    "    if quality in (\"bad\", \"pending\"):\n",
    "        continue\n",
    "    area  = df.loc[month, \"flood_area_km2\"] if month in df.index else 0\n",
    "    sc    = SCENE_COUNTS.get(month, \"?\")\n",
    "    color = area_to_color(area)\n",
    "    label = f\"{month}  ({area:,.1f} km\\u00b2,  n={sc} scenes)\"\n",
    "    if quality == \"gap\":\n",
    "        label += \"  [data gap]\"\n",
    "    elif quality == \"partial\":\n",
    "        label += \"  [partial month]\"\n",
    "\n",
    "    with open(gj_path) as f:\n",
    "        gj = json.load(f)\n",
    "\n",
    "    fg = folium.FeatureGroup(name=label, show=(month == \"2025-09\"))\n",
    "    folium.GeoJson(\n",
    "        gj,\n",
    "        style_function=lambda _f, c=color: {\n",
    "            \"fillColor\": c, \"color\": \"#0a1a3a\",\n",
    "            \"weight\": 0.5, \"fillOpacity\": 0.55,\n",
    "        },\n",
    "        tooltip=folium.GeoJsonTooltip(\n",
    "            fields=[\"month\"], aliases=[\"Month:\"]\n",
    "        ) if gj.get(\"features\") and\n",
    "             gj[\"features\"][0].get(\"properties\", {}).get(\"month\") else None,\n",
    "    ).add_to(fg)\n",
    "    fg.add_to(m)\n",
    "    loaded += 1\n",
    "\n",
    "# Partial months with no GeoJSON: add as informational empty layers\n",
    "seen = {gj.stem.replace(\"flood_extent_\", \"\") for gj in geojson_files}\n",
    "for month in sorted(PARTIAL_MONTHS):\n",
    "    if month in seen:\n",
    "        continue\n",
    "    area = df.loc[month, \"flood_area_km2\"] if month in df.index else 0.0\n",
    "    sc   = SCENE_COUNTS.get(month, \"?\")\n",
    "    label = f\"{month}  ({area:,.1f} km\\u00b2,  n={sc} scenes)  [partial month \\u2014 re-run 2026-08-01]\"\n",
    "    fg = folium.FeatureGroup(name=label, show=False)\n",
    "    fg.add_to(m)\n",
    "    loaded += 1\n",
    "\n",
    "folium.LayerControl(collapsed=False).add_to(m)\n",
    "\n",
    "aoi_coords = [[-5.9, 26.8], [-5.9, 30.8], [3.0, 30.8], [3.0, 26.8], [-5.9, 26.8]]\n",
    "folium.PolyLine(aoi_coords, color=\"#555\", weight=1.5, dash_array=\"6 4\",\n",
    "                tooltip=\"AOI: Eastern DRC\").add_to(m)\n",
    "\n",
    "map_path = DOCS_DIR / \"flood_map_interactive.html\"\n",
    "m.save(str(map_path))\n",
    "print(f\"Loaded {loaded} months  |  Map saved: {map_path}\")\n",
    "m\n",
])

# ── Cell 37e0b623  Markdown header ───────────────────────────────────────────
set_md_source("37e0b623", [
    "# Notebook 4 - Validation & Export\n",
    "**Inputs:**\n",
    "- `data/outputs/flood_extent/flood_stats.csv` -- monthly flood area table\n",
    "- `data/outputs/flood_extent/flood_extent_YYYY-MM.geojson` -- flood polygons (WGS84)\n",
    "\n",
    "**Outputs:**\n",
    "- Annotated time-series chart (PNG)\n",
    "- Interactive Folium map (`docs/flood_map_interactive.html`)\n",
    "- Export inventory table\n",
    "\n",
    "**AOI:** Eastern DRC -- North Kivu, South Kivu, Ituri  \n",
    "**Period:** Jan 2025 -- Jul 2026 (19 months; Jun 2026 = data gap; Jul 2026 = partial)  \n",
    "**Resolution:** 100 m | **CRS output:** EPSG:32735 -> reprojected to WGS84  \n",
    "**Detection threshold:** -5 dB change from baseline (2025-03/04/05)  \n",
    "**Post-processing:** 7x7 median filter (UN-SPIDER recommended practice)\n",
    "\n",
    "### Data-quality flags\n",
    "| Flag | Months | Reason |\n",
    "|------|--------|--------|\n",
    "| Unreliable | 2025-01, 2025-02 | Raw amplitude DN -- change signal meaningless |\n",
    "| Data gap | 2026-06 | WarpOperationError -- corrupt MPC RTC tiles across full AOI |\n",
    "| Partial | 2026-07 | Partial month (12 scenes, 2.5% coverage) -- re-run after 2026-07-31 |\n",
    "| Valid | All other months | Calibrated sigma0 dB, quality masks applied (15 valid months) |\n",
    "\n",
    "> **Sparse coverage note:** 2026-03 (107 scenes, 7.1% AOI), 2026-04 (98 scenes, 5.2%),\n",
    "> 2026-05 (127 scenes, 7.6%) use MPC sentinel-1-rtc for newer S1C/S1D satellites.\n",
    "> Signal is valid for covered pixels; spatial gaps exist across the remaining AOI.\n",
])

# ── Cell 37e2552f  Seasonal validation (markdown) -- fix stale -3 dB values ──
i, cell = find_cell("37e2552f")
src = "".join(cell["source"])
replacements = [
    ("3,427.6 km²", "217.2 km²"),
    ("**3,427.6**",  "**217.2**"),
    ("3,427 km²",   "217 km²"),
    ("| 2025-03 | 14 | 2.3 |",     "| 2025-03 | 14 | 0.0 |"),
    ("| 2025-05 | 31 | 26.6 |",    "| 2025-05 | 31 | 6.1 |"),
    ("| 2025-06 | 19 | 14.0 |",    "| 2025-06 | 19 | 4.3 |"),
    ("| 2025-07 | 7 | 8.1 |",      "| 2025-07 | 7 | 0.2 |"),
    ("| 2025-08 | 21 | 37.6 |",    "| 2025-08 | 21 | 0.4 |"),
    ("| 2025-10 | **8** | 10.9 |", "| 2025-10 | **8** | 0.9 |"),
    ("| 2025-11 | 11 | 11.4 |",    "| 2025-11 | 11 | 1.6 |"),
    ("| 2025-12 | 17 | 10.2 |",    "| 2025-12 | 17 | 2.0 |"),
    ("| 2026-01 | 15 | 9.2 |",     "| 2026-01 | 15 | 2.1 |"),
    ("| 2026-02 | 29 | 108.6 |",   "| 2026-02 | 29 | 17.4 |"),
    ("Otsu/−3 dB threshold",        "−5 dB threshold"),
    ("Otsu adaptive (capped at −3 dB) or fixed −3 dB", "fixed −5 dB"),
]
for old, new in replacements:
    src = src.replace(old, new)
nb["cells"][i]["source"] = src   # store as single string (valid per nbformat spec)

with open(NB_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print("NB04 patched successfully.")
