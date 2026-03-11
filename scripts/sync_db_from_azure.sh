#!/usr/bin/env bash
set -e

# Sync database from Azure dev environment to local PostgreSQL
#
# Prerequisites:
# - Azure CLI installed and logged in (az login)
# - docker-compose PostgreSQL container running
# - .env.local file with AZURE_KEY_VAULT_NAME configured

# Coordinate boundaries to filter data
LAT_MIN=60.0
LAT_MAX=62.0
LON_MIN=22.0
LON_MAX=26.0

# Load environment variables from .env.local
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env.local"
TEMP_FILE="/tmp/pollen_dump.csv"

# Cleanup function for error handling
cleanup() {
    if [ -f "$TEMP_FILE" ]; then
        rm -f "$TEMP_FILE"
    fi
}
trap cleanup EXIT

if [ ! -f "$ENV_FILE" ]; then
    echo ".env.local not found at $ENV_FILE"
    echo "Please create it with AZURE_KEY_VAULT_NAME configured"
    exit 1
fi

# Source the .env.local file to get AZURE_KEY_VAULT_NAME
source "$ENV_FILE"

if [ -z "$AZURE_KEY_VAULT_NAME" ]; then
    echo "AZURE_KEY_VAULT_NAME not set in .env.local"
    exit 1
fi

echo "Fetching Azure PostgreSQL credentials from Key Vault: $AZURE_KEY_VAULT_NAME..."

# Get credentials from Azure Key Vault
AZURE_DB_HOST=$(az keyvault secret show --vault-name "$AZURE_KEY_VAULT_NAME" --name postgres-server-fqdn --query value -o tsv)
AZURE_DB_USER=$(az keyvault secret show --vault-name "$AZURE_KEY_VAULT_NAME" --name postgres-admin-username --query value -o tsv)
AZURE_DB_PASSWORD=$(az keyvault secret show --vault-name "$AZURE_KEY_VAULT_NAME" --name postgres-admin-password --query value -o tsv)

if [ -z "$AZURE_DB_HOST" ] || [ -z "$AZURE_DB_USER" ] || [ -z "$AZURE_DB_PASSWORD" ]; then
    echo "Failed to retrieve credentials from Key Vault"
    exit 1
fi

echo "Credentials retrieved successfully"

# Check if container is running before attempting dump
if ! docker ps | grep -q pollen-postgres-local; then
    echo "PostgreSQL container is not running. Start it first with: task local:up"
    exit 1
fi

echo "Extracting data from Azure database: $AZURE_DB_HOST..."

# Validate boundary parameters
if [ -z "$LAT_MIN" ] || [ -z "$LAT_MAX" ] || [ -z "$LON_MIN" ] || [ -z "$LON_MAX" ]; then
    echo "Error: All boundary parameters must be specified"
    echo "  LAT_MIN, LAT_MAX, LON_MIN, LON_MAX"
    echo "Please edit the script to set these values"
    exit 1
fi

echo "   Filtering: latitude [$LAT_MIN, $LAT_MAX], longitude [$LON_MIN, $LON_MAX]"

# Extract data from Azure using psql with COPY TO STDOUT
# Filters data within the specified bounding box
PGSSLMODE=require PGPASSWORD="$AZURE_DB_PASSWORD" psql \
    --host="$AZURE_DB_HOST" \
    --username="$AZURE_DB_USER" \
    --dbname=pollen \
    --no-password \
    -c "COPY (SELECT * FROM public.pollen_forecast WHERE latitude BETWEEN $LAT_MIN AND $LAT_MAX AND longitude BETWEEN $LON_MIN AND $LON_MAX ORDER BY start_date, forecast_time) TO STDOUT WITH CSV HEADER" \
    > "$TEMP_FILE"

if [ $? -ne 0 ]; then
    echo "Failed to extract data from Azure"
    exit 1
fi

# Check if we got any data
ROW_COUNT=$(wc -l < "$TEMP_FILE")
ROW_COUNT=$((ROW_COUNT - 1))  # Subtract header row

if [ $ROW_COUNT -eq 0 ]; then
    echo "Warning: No data found within specified boundaries"
    echo "  Latitude: [$LAT_MIN, $LAT_MAX]"
    echo "  Longitude: [$LON_MIN, $LON_MAX]"
    echo "The local database will be truncated but no new data will be added."
fi

echo "Extracted $ROW_COUNT rows from Azure"
echo "Loading data to local PostgreSQL container..."

# Truncate the local table to start fresh
docker exec pollen-postgres-local psql -U pollen_user -d pollen \
    -c "TRUNCATE TABLE public.pollen_forecast;"

if [ $? -ne 0 ]; then
    echo "Failed to truncate local table"
    exit 1
fi

echo "Local table truncated"

# Load data into local database using COPY FROM STDIN
if [ $ROW_COUNT -gt 0 ]; then
    docker exec -i pollen-postgres-local psql -U pollen_user -d pollen \
        -c "COPY public.pollen_forecast FROM STDIN WITH CSV HEADER" < "$TEMP_FILE"

    if [ $? -ne 0 ]; then
        echo "Failed to load data into local database"
        exit 1
    fi

    echo "Loaded $ROW_COUNT rows into local database"
else
    echo " No rows loaded (no data found in Azure)"
fi

echo "Cleaning up temporary files..."
rm -f "$TEMP_FILE"

echo ""
echo "Database sync complete!"
echo "Bounding box: latitude [$LAT_MIN, $LAT_MAX], longitude [$LON_MIN, $LON_MAX]"
echo "Rows synced: $ROW_COUNT"
echo ""
echo "You can now run the API locally with: task local:api"
