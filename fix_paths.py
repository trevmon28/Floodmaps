"""
Replace the Colab git-clone cell in all three notebooks with a portable
path-detection cell that works in VS Code, JupyterLab, and Google Colab.
"""
import json
from pathlib import Path

NOTEBOOKS_DIR = Path(__file__).parent / "notebooks"

NEW_CELL_SOURCE = [
    "# Environment setup — works in VS Code, JupyterLab, and Google Colab\n",
    "from pathlib import Path\n",
    "import os\n",
    "\n",
    "def _find_project_root():\n",
    "    in_colab = 'COLAB_GPU' in os.environ or 'COLAB_RELEASE_TAG' in os.environ\n",
    "    if in_colab:\n",
    "        import subprocess\n",
    "        if not Path('Floodmaps').exists():\n",
    "            subprocess.run(['git', 'clone', 'https://github.com/trevmon28/Floodmaps.git'], check=True)\n",
    "        return Path('Floodmaps').resolve()\n",
    "    for candidate in [Path(os.path.abspath('')), Path(os.path.abspath('')).parent]:\n",
    "        if (candidate / 'config' / 'config.yaml').exists():\n",
    "            return candidate\n",
    "    raise FileNotFoundError(\n",
    "        'Cannot locate config/config.yaml.\\n'\n",
    "        'Run from the project root or the notebooks/ directory.'\n",
    "    )\n",
    "\n",
    "PROJECT_ROOT = _find_project_root()\n",
    "os.chdir(PROJECT_ROOT)\n",
    "print('Project root:', PROJECT_ROOT)\n",
]

CLONE_MARKERS = [
    "git clone https://github.com/trevmon28/Floodmaps.git",
]

def is_clone_cell(cell):
    src = "".join(cell.get("source", []))
    return any(m in src for m in CLONE_MARKERS)

def patch_notebook(nb_path):
    with open(nb_path, encoding="utf-8") as f:
        nb = json.load(f)

    changed = False
    for cell in nb["cells"]:
        if cell["cell_type"] == "code" and is_clone_cell(cell):
            cell["source"] = NEW_CELL_SOURCE
            cell["outputs"] = []
            cell["execution_count"] = None
            changed = True
            print(f"  Patched clone cell in {nb_path.name}")

    if changed:
        with open(nb_path, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)
    else:
        print(f"  No clone cell found in {nb_path.name} — skipping")

for nb_file in sorted(NOTEBOOKS_DIR.glob("0*.ipynb")):
    patch_notebook(nb_file)

print("Done.")
