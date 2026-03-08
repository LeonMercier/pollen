"""
Database connection configuration for PostgreSQL.

Environment variables are automatically populated from Azure Key Vault
via App Service managed identity.
"""

import os

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

    return (
        f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}"
        f"@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
        f"?sslmode={DATABASE_SSLMODE}"
    )


# Example usage with psycopg2 (sync)
def get_sync_connection():
    """
    Example: Get a sync database connection using psycopg2.

    Install: pip install psycopg2-binary
    """
    import psycopg

    conn = psycopg.connect(
        host=DATABASE_HOST,
        port=DATABASE_PORT,
        database=DATABASE_NAME,
        user=DATABASE_USER,
        password=DATABASE_PASSWORD,
        sslmode=DATABASE_SSLMODE,
    )
    return conn
