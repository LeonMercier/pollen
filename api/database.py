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
