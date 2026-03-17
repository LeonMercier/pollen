"""
Database connection configuration for PostgreSQL.

Supports two modes:
- Production/Azure: Environment variables from Azure Key Vault via App Service
- Local development: Environment variables from .env.local when ENV=local
"""

import os
from pathlib import Path


def load_local_env():
    """Load .env.local if ENV=local and file exists."""
    if os.getenv("ENV") == "local":
        env_file = Path(__file__).parent.parent / ".env.local"
        if env_file.exists():
            print(f"Loading local environment from {env_file}")
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "=" in line:
                            key, value = line.split("=", 1)
                            os.environ.setdefault(key, value)
        else:
            print(
                f"ENV=local but {env_file} not found. "
                "Using system environment variables."
            )


# Load local env if applicable
# Runs on module import and saves to module variables below
load_local_env()

# Database connection parameters from environment variables
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_SSLMODE = os.getenv("DATABASE_SSLMODE", "require")


def get_database_url() -> str:
    """
    Construct PostgreSQL connection URL from environment variables.

    Returns:
        str: PostgreSQL connection URL with SSL mode

    Example:
        postgresql://user:pass@host:5432/dbname?sslmode=require
    """
    if not all([DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD, DATABASE_NAME]):
        raise ValueError(
            "Missing required database environment variables. "
            "Ensure DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD, "
            "and DATABASE_NAME are set."
        )

    env_mode = os.getenv("ENV", "production")
    print(
        f"Connecting to PostgreSQL ({env_mode} mode): "
        f"{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
    )

    return (
        f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}"
        f"@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
        f"?sslmode={DATABASE_SSLMODE}"
    )


# Example usage with psycopg (sync)
def get_sync_connection():
    """
    Get a sync database connection using psycopg.
    """
    import psycopg

    conn = psycopg.connect(
        host=DATABASE_HOST,
        port=DATABASE_PORT,
        dbname=DATABASE_NAME,
        user=DATABASE_USER,
        password=DATABASE_PASSWORD,
        sslmode=DATABASE_SSLMODE,
    )
    return conn


def search_cities(query: str, limit: int = 10) -> list[dict]:
    """
    Search for cities by ASCII name prefix (case-insensitive).

    Args:
        query: Prefix string to search for (must be at least 2 characters)
        limit: Maximum number of results to return (default 10)

    Returns:
        List of dicts with 'name', 'ascii_name', and 'country_code' keys,
        ordered by population descending. Returns empty list if query is too
        short or on any DB error.
    """
    import psycopg

    if len(query) < 2:
        return []

    try:
        conn = get_sync_connection()
        with conn.cursor() as cur:
            # Prefix match on ascii_name; uses idx_cities_ascii_name index
            cur.execute(
                """
                SELECT name, ascii_name, country_code
                FROM public.cities
                WHERE ascii_name ILIKE %s
                ORDER BY population DESC NULLS LAST
                LIMIT %s
                """,
                (f"{query}%", limit),
            )
            rows = cur.fetchall()
            conn.close()
            return [
                {"name": row[0], "ascii_name": row[1], "country_code": row[2]}
                for row in rows
            ]

    except Exception as e:
        print(f"Error searching cities for '{query}': {str(e)}")
        return []


def lookup_city_coordinates(city_name: str) -> tuple[float, float] | None:
    """
    Look up pollen grid coordinates for a city by name (case-insensitive).

    Args:
        city_name: City name to search for (exact match, case-insensitive)

    Returns:
        Tuple of (latitude, longitude) for the highest population match,
        or None if city not found

    Note:
        Uses pollen_latitude and pollen_longitude which are snapped to
        the 0.1-degree pollen forecast grid.
    """
    import psycopg

    try:
        conn = get_sync_connection()
        with conn.cursor() as cur:
            # Case-insensitive exact match on name or ascii_name
            # Order by population DESC to get highest population city
            cur.execute(
                """
                SELECT pollen_latitude, pollen_longitude
                FROM public.cities
                WHERE LOWER(name) = LOWER(%s) OR LOWER(ascii_name) = LOWER(%s)
                ORDER BY population DESC NULLS LAST
                LIMIT 1
                """,
                (city_name, city_name),
            )
            result = cur.fetchone()
            conn.close()

            if result:
                return (float(result[0]), float(result[1]))
            return None

    except Exception as e:
        print(f"Error looking up city '{city_name}': {str(e)}")
        return None
