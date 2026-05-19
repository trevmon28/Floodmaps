"""
Flood Analytics MCP Server
Exposes flood data tools for Claude via FastMCP.
"""
import os
import httpx
from mcp.server.fastmcp import FastMCP

API_BASE = os.environ.get("FLOOD_API_URL", "http://localhost:8001")

mcp = FastMCP(
    "Flood Analytics",
    instructions=(
        "You have access to monthly flood extent data for territories in eastern DRC "
        "(North Kivu, South Kivu, Ituri). Data covers March 2025 – February 2026. "
        "Use list_areas() first if you are unsure of the territory name — fuzzy matching "
        "is supported so partial names work. Flood area is in km². Quality flag 'gap' means "
        "no satellite data was available that month."
    ),
)


def _get(path: str, **params) -> dict:
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(f"{API_BASE}{path}", params=params)
            r.raise_for_status()
            return r.json()
    except httpx.HTTPStatusError as e:
        return {"error": e.response.json().get("detail", str(e))}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def check_health() -> dict:
    """Confirms the flood analytics API is live and reports how much data is loaded."""
    return _get("/health")


@mcp.tool()
def list_areas() -> dict:
    """Lists all DRC territory names available in the flood dataset."""
    return _get("/areas")


@mcp.tool()
def get_flood_extent(area: str, year: int, month: int) -> dict:
    """
    Returns flood extent for a specific DRC territory and month.

    Args:
        area: Territory name — partial or fuzzy names are accepted (e.g. 'Rutshuru', 'butembo')
        year: Year as integer (e.g. 2025)
        month: Month as integer 1-12 (e.g. 9 for September)
    """
    return _get(f"/flood/{area}/{year}/{month}")


@mcp.tool()
def get_flood_summary(area: str) -> dict:
    """
    Returns the full monthly time series of flood extent for a DRC territory.

    Args:
        area: Territory name — partial or fuzzy names are accepted
    """
    return _get(f"/flood/{area}/summary")


@mcp.tool()
def find_flood_events(area: str, threshold_km2: float = 1.0) -> dict:
    """
    Returns months where flooding in a DRC territory exceeded a given area threshold.

    Args:
        area: Territory name — partial or fuzzy names are accepted
        threshold_km2: Minimum flood area in km² to qualify as an event (default 1.0)
    """
    return _get(f"/flood/{area}/events", threshold=threshold_km2)


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    port = int(os.environ.get("MCP_PORT", "9001"))

    if transport == "http":
        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = port
        mcp.settings.transport_security.enable_dns_rebinding_protection = False
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
