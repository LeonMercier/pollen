"""
Database connection configuration for PostgreSQL.

Supports two modes:
- Production/Azure: Environment variables from Azure Key Vault via App Service
- Local development: Environment variables from .env.local when ENV=local

Uses lazy initialization to avoid startup failures if Key Vault references
haven't resolved yet.
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
# Runs on module import
load_local_env()

# Cache for database configuration (lazy initialization)
_db_config = None


def _get_db_config() -> dict:
    """
    Get database configuration from environment variables (lazy initialization).
    
    Returns:
        dict: Database connection parameters
        
    Raises:
        ValueError: If required environment variables are missing or contain unresolved Key Vault references
    """
    global _db_config
    
    if _db_config is not None:
        return _db_config
    
    # Read environment variables
    DATABASE_HOST = os.getenv("DATABASE_HOST")
    DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
    DATABASE_NAME = os.getenv("DATABASE_NAME")
    DATABASE_USER = os.getenv("DATABASE_USER")
    DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
    DATABASE_SSLMODE = os.getenv("DATABASE_SSLMODE", "require")
    
    # Validate required variables exist
    if not all([DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD, DATABASE_NAME]):
        missing = []
        if not DATABASE_HOST: missing.append("DATABASE_HOST")
        if not DATABASE_USER: missing.append("DATABASE_USER")
        if not DATABASE_PASSWORD: missing.append("DATABASE_PASSWORD")
        if not DATABASE_NAME: missing.append("DATABASE_NAME")
        
        raise ValueError(
            f"Missing required database environment variables: {', '.join(missing)}. "
            "Ensure all database credentials are set in App Service configuration."
        )
    
    # Check for unresolved Key Vault references (indicates Key Vault access issues)
    for var_name, var_value in [
        ("DATABASE_HOST", DATABASE_HOST),
        ("DATABASE_USER", DATABASE_USER),
        ("DATABASE_PASSWORD", DATABASE_PASSWORD),
    ]:
        if var_value and "@Microsoft.KeyVault" in var_value:
            raise ValueError(
                f"{var_name} contains unresolved Key Vault reference: {var_value[:50]}... "
                "This usually means the App Service managed identity doesn't have Key Vault access yet. "
                "Wait a few seconds and try again, or check Key Vault access policies."
            )
    
    env_mode = os.getenv("ENV", "production")
    print(
        f"Database config loaded ({env_mode} mode): "
        f"{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME} (sslmode={DATABASE_SSLMODE})"
    )
    
    _db_config = {
        "host": DATABASE_HOST,
        "port": DATABASE_PORT,
        "dbname": DATABASE_NAME,
        "user": DATABASE_USER,
        "password": DATABASE_PASSWORD,
        "sslmode": DATABASE_SSLMODE,
    }
    
    return _db_config


def get_database_url() -> str:
    """
    Construct PostgreSQL connection URL from environment variables.

    Returns:
        str: PostgreSQL connection URL with SSL mode

    Example:
        postgresql://user:pass@host:5432/dbname?sslmode=require
    """
    config = _get_db_config()
    
    return (
        f"postgresql://{config['user']}:{config['password']}"
        f"@{config['host']}:{config['port']}/{config['dbname']}"
        f"?sslmode={config['sslmode']}"
    )


# Example usage with psycopg (sync)
def get_sync_connection():
    """
    Get a sync database connection using psycopg.
    """
    import psycopg

    config = _get_db_config()
    
    conn = psycopg.connect(
        host=config["host"],
        port=config["port"],
        dbname=config["dbname"],
        user=config["user"],
        password=config["password"],
        sslmode=config["sslmode"],
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


def lookup_city_coordinates(city_name: str) -> tuple[float, float, str] | None:
    """
    Look up pollen grid coordinates and timezone for a city by name (case-insensitive).

    Args:
        city_name: City name to search for (exact match, case-insensitive)

    Returns:
        Tuple of (latitude, longitude, timezone) for the highest population match,
        or None if city not found. Timezone is an IANA timezone string (e.g., "America/New_York")
        or "UTC" if timezone is not available in the database.

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
                SELECT pollen_latitude, pollen_longitude, timezone
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
                timezone = result[2] if result[2] else "UTC"
                return (float(result[0]), float(result[1]), timezone)
            return None

    except Exception as e:
        print(f"Error looking up city '{city_name}': {str(e)}")
        return None
