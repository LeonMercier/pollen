"""
Geographic configuration for Pollen ETL pipeline.

IMPORTANT: These bounds define the area for pollen forecast data extraction.
All downstream processing (geocoding, analysis) must use these same bounds.

Coordinate system: WGS84 decimal degrees
Area covered: Scandinavia and Central Europe
"""

# CAMS data covers all of Europe excluding Canary islands and Azores but including Iceland
# Here we limit to a box including Finland, Sweden and the Baltic countries
GRID_NORTH = 70.05  # northernmost of Finland
GRID_SOUTH = 53.0  # southernmost of Lithuania
GRID_WEST = 10.0  # westernmost of Sweden
GRID_EAST = 31.4  # easternmost of  Finland


def get_cdsapi_area():
    """
    Returns bounding box in CDSAPI area format.

    CDSAPI uses [north, west, south, east] order.

    Returns:
        list: [north, west, south, east] in decimal degrees
    """
    return [GRID_NORTH, GRID_WEST, GRID_SOUTH, GRID_EAST]


def get_bounds_dict():
    """
    Returns bounding box as dictionary.

    Returns:
        dict: Geographic bounds with keys 'north', 'south', 'west', 'east'
    """
    return {
        "north": GRID_NORTH,
        "south": GRID_SOUTH,
        "west": GRID_WEST,
        "east": GRID_EAST,
    }


def validate_point_in_bounds(lat, lon):
    """
    Check if a lat/lon point falls within the pollen data bounds.

    Args:
        lat (float): Latitude in decimal degrees
        lon (float): Longitude in decimal degrees

    Returns:
        bool: True if point is within bounds, False otherwise
    """
    return GRID_SOUTH <= lat <= GRID_NORTH and GRID_WEST <= lon <= GRID_EAST
