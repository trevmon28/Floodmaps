"""
Flood Analytics REST API
Serves monthly flood extent data for DRC territories.
"""
import os
import difflib
from pathlib import Path
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

DATA_DIR = Path(os.environ.get("FLOOD_DATA_DIR", "/opt/flood/data/handover"))

# --- In-memory data store ---
store: dict = {"admin3": None, "stats": None, "areas": []}


def _load():
    # Admin-3 flood data
    csv_path = DATA_DIR / "csv" / "admin3_flood.csv"
    try:
        df = pd.read_csv(csv_path)
        df["flood_area_km2"] = pd.to_numeric(df["flood_area_km2"], errors="coerce").fillna(0)
        store["admin3"] = df
        store["areas"] = sorted(df["shapeName"].dropna().unique().tolist())
    except FileNotFoundError:
        raise RuntimeError(f"Data file not found: {csv_path}")

    # Overall monthly stats
    stats_path = DATA_DIR / "flood_stats.csv"
    if stats_path.exists():
        store["stats"] = pd.read_csv(stats_path, index_col="month")

    print(f"[startup] Loaded {len(store['areas'])} areas, {len(store['admin3'])} rows")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load()
    yield


app = FastAPI(title="Flood Analytics API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _match(name: str) -> str | None:
    if name in store["areas"]:
        return name
    hits = difflib.get_close_matches(name, store["areas"], n=1, cutoff=0.55)
    return hits[0] if hits else None


def _require_area(name: str) -> str:
    matched = _match(name)
    if not matched:
        raise HTTPException(
            status_code=404,
            detail=f"Area '{name}' not found. Try one of: {store['areas'][:8]}"
        )
    return matched


# --- Endpoints ---

@app.get("/health")
def check_health():
    return {
        "status": "ok",
        "areas_loaded": len(store["areas"]),
        "rows_loaded": len(store["admin3"]) if store["admin3"] is not None else 0,
        "data_dir": str(DATA_DIR),
    }


@app.get("/areas")
def list_areas():
    return {"areas": store["areas"], "count": len(store["areas"])}


@app.get("/flood/{area}/{year}/{month}")
def get_flood_extent(area: str, year: int, month: int):
    matched = _require_area(area)
    month_str = f"{year}-{month:02d}"
    df = store["admin3"]
    row = df[(df["shapeName"] == matched) & (df["month"] == month_str)]
    if row.empty:
        raise HTTPException(404, f"No data for '{matched}' in {month_str}")
    r = row.iloc[0]

    # flooded_pct from overall stats if area matches AOI-level, else omit
    flooded_pct = None
    if store["stats"] is not None and month_str in store["stats"].index:
        s = store["stats"].loc[month_str]
        flooded_pct = round(float(s.get("flooded_pct", 0)), 4) if "flooded_pct" in s else None

    return {
        "area": matched,
        "queried_as": area if area != matched else None,
        "month": month_str,
        "flood_area_km2": round(float(r["flood_area_km2"]), 3),
        "flooded_pct": flooded_pct,
        "quality": str(r.get("quality", "unknown")),
    }


@app.get("/flood/{area}/summary")
def get_flood_summary(area: str):
    matched = _require_area(area)
    df = store["admin3"]
    rows = df[df["shapeName"] == matched].sort_values("month")
    if rows.empty:
        raise HTTPException(404, f"No data for '{matched}'")
    records = rows[["month", "flood_area_km2", "quality"]].to_dict(orient="records")
    peak_row = rows.loc[rows["flood_area_km2"].idxmax()]
    return {
        "area": matched,
        "months": records,
        "peak_month": str(peak_row["month"]),
        "peak_km2": round(float(peak_row["flood_area_km2"]), 3),
        "total_months": len(records),
    }


@app.get("/flood/{area}/events")
def find_flood_events(
    area: str,
    threshold: float = Query(default=1.0, description="Minimum flood area in km²"),
):
    matched = _require_area(area)
    df = store["admin3"]
    rows = df[
        (df["shapeName"] == matched) & (df["flood_area_km2"] >= threshold)
    ].sort_values("flood_area_km2", ascending=False)
    return {
        "area": matched,
        "threshold_km2": threshold,
        "events": rows[["month", "flood_area_km2", "quality"]].to_dict(orient="records"),
        "count": len(rows),
    }
