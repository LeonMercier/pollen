"""
Pollen ETL API

Minimal FastAPI application serving as a placeholder.
Currently provides a single route returning an HTML welcome page.
"""

import json

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
async def root():
    """
    Root endpoint returning a simple HTML page with city search functionality.
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pollen ETL API</title>
        <script src="https://cdn.plot.ly/plotly-3.4.0.min.js"></script>
        <style>
            body {
                font-family: system-ui, -apple-system, sans-serif;
                display: flex;
                justify-content: center;
                align-items: flex-start;
                min-height: 100vh;
                margin: 0;
                padding-top: 2rem;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                text-align: center;
                padding: 2rem;
                max-width: 1200px;
                width: 100%;
            }
            h1 {
                font-size: 3rem;
                margin-bottom: 1rem;
            }
            p {
                font-size: 1.2rem;
                opacity: 0.9;
            }
            
            /* Search form styling */
            #city-search-form {
                margin: 2rem 0;
                display: flex;
                gap: 0.5rem;
                justify-content: center;
                align-items: center;
            }
            
            #city-input {
                padding: 0.75rem 1rem;
                font-size: 1rem;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.1);
                color: white;
                min-width: 250px;
                transition: all 0.3s ease;
            }
            
            #city-input::placeholder {
                color: rgba(255, 255, 255, 0.6);
            }
            
            #city-input:focus {
                outline: none;
                border-color: rgba(255, 255, 255, 0.8);
                background: rgba(255, 255, 255, 0.2);
            }
            
            #city-search-form button {
                padding: 0.75rem 2rem;
                font-size: 1rem;
                border: none;
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.2);
                color: white;
                cursor: pointer;
                transition: all 0.3s ease;
                font-weight: 500;
            }
            
            #city-search-form button:hover {
                background: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
            }
            
            #city-search-form button:active {
                transform: translateY(0);
            }
            
            /* Plot container */
            #plot-container {
                margin-top: 2rem;
                height: 60vh;
                min-height: 30rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Pollen ETL API</h1>
            <p>Welcome to the Pollen ETL data pipeline API</p>
            
            <form id="city-search-form">
                <input 
                    type="text" 
                    id="city-input" 
                    name="city" 
                    placeholder="Enter city name"
                    autocomplete="off"
                    required
                />
                <button type="submit">Search</button>
            </form>
            
            <div id="plot-container">
                <p>Search for a city</p>
            </div>
        </div>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.getElementById('city-search-form');
            const input = document.getElementById('city-input');
            const container = document.getElementById('plot-container');
            
            form.addEventListener('submit', async function(e) {
                e.preventDefault();  // Prevent page reload
                
                const cityName = input.value.trim();
                if (!cityName) {
                    container.innerHTML = '<p>Please enter a city name</p>';
                    return;
                }
                
                // Show loading state
                container.innerHTML = '<p>Loading...</p>';
                
                try {
                    // Make AJAX request
                    const response = await fetch(`/api/plot?city=${encodeURIComponent(cityName)}`);
                    const data = await response.json();
                    
                    // Check if request was successful
                    if (data.success) {
                        // Clear loading message and render Plotly chart
                        container.innerHTML = '';
                        
                        Plotly.newPlot(
                            container,
                            data.plotly_data,
                            data.plotly_layout,
                            data.plotly_config
                        );
                        
                        console.log(`Loaded plot for ${data.city} (${data.lat}, ${data.lon})`);
                    } else {
                        // Show error message
                        container.innerHTML = `<p>${data.error}</p>`;
                        console.log(`Error: ${data.error}`);
                    }
                    
                } catch (error) {
                    // Handle network errors
                    container.innerHTML = '<p>Error: Could not connect to server</p>';
                    console.error('Fetch error:', error);
                }
            });
        });
        </script>
    </body>
    </html>
    """

    return html_content


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


@app.get("/health")
async def health():
    """
    Health check endpoint for monitoring.
    """
    return {"status": "healthy"}
