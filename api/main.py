"""
Pollen ETL API

Minimal FastAPI application serving as a placeholder.
Currently provides a single route returning an HTML welcome page.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# local modules
from plot import plot

app = FastAPI(
    title="Pollen ETL API",
    description="API for Pollen ETL data pipeline",
    version="0.1.0",
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Root endpoint returning a simple HTML page.
    """
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
        </div>
    """

    fig = plot(60.15, 24.95)

    html_end = """
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
