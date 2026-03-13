"""
Pollen ETL API

Minimal FastAPI application serving as a placeholder.
Currently provides a single route returning an HTML welcome page.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# local modules
from database import lookup_city_coordinates
from plot import plot

app = FastAPI(
    title="Pollen ETL API",
    description="API for Pollen ETL data pipeline",
    version="0.1.0",
)


@app.get("/", response_class=HTMLResponse)
# lat: param name
# float | None: type hint
# = None: default value
async def root(
    lat: float | None = None, lon: float | None = None, city: str | None = None
):
    """
    Root endpoint returning a simple HTML page.
    Accepts either city name or lat/lon coordinates.
    """
    # Resolve coordinates from city name if provided
    resolved_lat = lat
    resolved_lon = lon
    city_not_found = False

    if city:
        coords = lookup_city_coordinates(city)
        if coords:
            resolved_lat, resolved_lon = coords
        else:
            city_not_found = True

    html_start = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pollen ETL API</title>
        <style>
            body {
                font-family: system-ui, -apple-system, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                text-align: center;
                padding: 2rem;
            }
            h1 {
                font-size: 3rem;
                margin-bottom: 1rem;
            }
            p {
                font-size: 1.2rem;
                opacity: 0.9;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Pollen ETL API</h1>
            <p>Welcome to the Pollen ETL data pipeline API</p>
            <a href="/?city=Helsinki">Helsinki</a>
            <a href="/?city=Turku">Turku</a>
            <a href="/?city=Tampere">Tampere</a>
    """

    if city_not_found:
        fig = f"<p>City '{city}' not found</p>"
    elif resolved_lat and resolved_lon:
        try:
            fig = plot(resolved_lat, resolved_lon)
        except:
            fig = "<p>Error happened</p>"
    else:
        fig = "<p>Press a button</p>"

    html_end = """
    </div>
    </body>
    </html>
    """

    html_content = html_start + fig + html_end

    return html_content


@app.get("/health")
async def health():
    """
    Health check endpoint for monitoring.
    """
    return {"status": "healthy"}
