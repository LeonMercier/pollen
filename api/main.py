"""
Pollen ETL API

FastAPI application providing pollen forecast data.
The frontend is served as a static file hosted separately (frontend/index.html).
"""

import json
import os

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

# local modules
from database import lookup_city_coordinates, search_cities
from plot import plot, plot_by_type

app = FastAPI(
    title="Pollen ETL API",
    description="API for Pollen ETL data pipeline",
    version="0.1.0",
)

# Allow the static frontend (Azure Blob Storage or localhost) to call this API.
# ALLOWED_ORIGINS is a comma-separated list of origins, e.g.:
#   http://localhost:8000,https://stwebpollenprod.z6.web.core.windows.net
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "")
# List comprehension
# split comma separated list, strip whitespace and empty strings
origins = [o.strip() for o in _allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/cities")
async def api_cities(q: str = Query(min_length=2)):
    """
    City autocomplete endpoint. Returns up to 10 city suggestions for a
    given prefix query (case-insensitive match on ASCII city name).

    Query params:
        q: Prefix string to search for (minimum 2 characters)

    Returns:
        JSON list of objects with 'name', 'ascii_name', and 'country_code'.
    """
    return search_cities(q)


@app.get("/api/plot")
async def api_plot(city: str | None = None):
    """
    API endpoint that returns plot data as JSON.
    Used by AJAX frontend to load plots without page reload.

    Query params:
        city: City name to search for

    Returns:
        JSON with 'success', 'plotly_data', 'plotly_layout', 'plotly_config', and optional 'error' fields
    """
    if not city:
        return {"success": False, "error": "City parameter is required"}

    # Look up city coordinates
    coords = lookup_city_coordinates(city)

    if not coords:
        return {"success": False, "error": f"City '{city}' not found"}

    # Get plot figure
    lat, lon = coords
    try:
        fig = plot(lat, lon)  # Returns a figure object

        # Use Plotly's built-in JSON serialization (idiomatic way)
        fig_json_str = fig.to_json()
        fig_data = json.loads(fig_json_str)

        return {
            "success": True,
            "city": city,
            "lat": lat,
            "lon": lon,
            "plotly_data": fig_data["data"],
            "plotly_layout": fig_data["layout"],
            "plotly_config": {"responsive": True},
        }
    except Exception as e:
        return {"success": False, "error": "Error generating plot"}


@app.get("/api/plots")
async def api_plots(city: str | None = None):
    """
    API endpoint that returns one Plotly figure per pollen type as JSON.
    Used by the frontend to render a responsive grid of charts.

    Query params:
        city: City name to search for

    Returns:
        JSON with 'success', 'city', 'lat', 'lon', and 'plots' dict keyed by
        pollen display name, each containing 'data', 'layout', and 'config'.
    """
    if not city:
        return {"success": False, "error": "City parameter is required"}

    coords = lookup_city_coordinates(city)

    if not coords:
        return {"success": False, "error": f"City '{city}' not found"}

    lat, lon = coords
    try:
        figures = plot_by_type(lat, lon)

        plots = {}
        for display_name, fig in figures.items():
            fig_data = json.loads(fig.to_json())
            plots[display_name] = {
                "data": fig_data["data"],
                "layout": fig_data["layout"],
                "config": {"responsive": True},
            }

        return {
            "success": True,
            "city": city,
            "lat": lat,
            "lon": lon,
            "plots": plots,
        }
    except Exception as e:
        return {"success": False, "error": "Error generating plots"}


@app.get("/health")
async def health():
    """
    Health check endpoint for monitoring.
    """
    return {"status": "healthy"}
