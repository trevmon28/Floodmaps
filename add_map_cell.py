import json
from pathlib import Path

path = r'c:\Users\trevm\Projects\Floodmaps\notebooks\05_sampling_frame.ipynb'
with open(path, encoding='utf-8') as f:
    nb = json.load(f)

map_md = {
    'cell_type': 'markdown',
    'metadata': {},
    'source': ['## 9  Interactive map — flood extents + admin-3 boundaries + cell towers']
}

src = '''\
import folium, math
from folium.plugins import MarkerCluster

m = folium.Map(location=[-1.5, 28.8], zoom_start=7, tiles="CartoDB positron")

# Admin-3 boundaries coloured by peak flood area
admin_layer = folium.FeatureGroup(name="Admin-3 territories", show=True)
for _, row in adm2_aoi.iterrows():
    peak_vals = admin3_df[admin3_df["shapeName"] == row["shapeName"]]["flood_area_km2"]
    peak = peak_vals.max() if len(peak_vals) else 0
    if math.isnan(peak): peak = 0
    color = "#d73027" if peak > 100 else "#fc8d59" if peak > 10 else "#fee090" if peak > 1 else "#e0f3f8"
    folium.GeoJson(
        row.geometry.__geo_interface__,
        style_function=lambda _, c=color: {"fillColor": c, "color": "#333", "weight": 1, "fillOpacity": 0.5},
        tooltip=f"{row['shapeName']}  (peak: {peak:,.1f} km²)"
    ).add_to(admin_layer)
admin_layer.add_to(m)

# Flood extents by month (Sep 2025 shown by default)
for month, gdf in flood_gdfs.items():
    fg = folium.FeatureGroup(name=f"Flood {month}", show=(month == "2025-09"))
    folium.GeoJson(
        gdf.__geo_interface__,
        style_function=lambda _: {"fillColor": "#08519c", "color": "#08306b", "weight": 0.4, "fillOpacity": 0.6}
    ).add_to(fg)
    fg.add_to(m)

# Cell towers (if loaded)
if towers_gdf is not None and len(towers_gdf) > 0:
    tower_layer = folium.FeatureGroup(name="Cell towers", show=False)
    cluster = MarkerCluster().add_to(tower_layer)
    for _, t in towers_gdf.iterrows():
        folium.CircleMarker(
            location=[t.lat, t.lon], radius=3,
            color="#e31a1c", fill=True, fill_opacity=0.7,
            tooltip=f"{t.get('radio', '')} net:{t.get('net', '')}"
        ).add_to(cluster)
    tower_layer.add_to(m)
else:
    print("No tower data — paste OpenCelliD token in cell 6 and re-run.")

# AOI outline
aoi_coords = [[-5.9, 26.8], [-5.9, 30.8], [3.0, 30.8], [3.0, 26.8], [-5.9, 26.8]]
folium.PolyLine(aoi_coords, color="#555", weight=1.5, dash_array="6 4", tooltip="AOI: Eastern DRC").add_to(m)

# Legend
legend_html = """
<div style="position:fixed;bottom:40px;left:40px;z-index:1000;background:white;
            padding:10px;border-radius:6px;border:1px solid #ccc;font-size:12px">
  <b>Peak flood area</b><br>
  <span style="background:#d73027;padding:2px 8px">&nbsp;</span> &gt;100 km²<br>
  <span style="background:#fc8d59;padding:2px 8px">&nbsp;</span> 10–100 km²<br>
  <span style="background:#fee090;padding:2px 8px">&nbsp;</span> 1–10 km²<br>
  <span style="background:#e0f3f8;padding:2px 8px">&nbsp;</span> &lt;1 km²
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))
folium.LayerControl(collapsed=False).add_to(m)

map_path = Path("docs/flood_sampling_map.html")
map_path.parent.mkdir(exist_ok=True)
m.save(str(map_path))
print(f"Map saved: {map_path}")
import webbrowser
webbrowser.open(map_path.resolve().as_uri())
m
'''

map_code = {
    'cell_type': 'code',
    'execution_count': None,
    'metadata': {},
    'outputs': [],
    'source': src
}

nb['cells'].append(map_md)
nb['cells'].append(map_code)

with open(path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print('Done — 2 cells added')
