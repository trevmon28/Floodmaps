import json

path = r'c:\Users\trevm\Projects\Floodmaps\notebooks\04_validation_export.ipynb'
with open(path, encoding='utf-8') as f:
    nb = json.load(f)

new_cell = {
    'cell_type': 'code',
    'execution_count': None,
    'metadata': {},
    'outputs': [],
    'source': [
        'import webbrowser, pathlib\n',
        'webbrowser.open(pathlib.Path(map_path).resolve().as_uri())\n',
        'print(f"Map opened in browser: {map_path}")'
    ]
}

for i, cell in enumerate(nb['cells']):
    if cell.get('id') == 'c40ba151':
        nb['cells'].insert(i + 1, new_cell)
        print(f'Inserted after cell index {i}')
        break

with open(path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print('Done')
