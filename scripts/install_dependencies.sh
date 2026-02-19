#!/bin/bash
# Databricks cluster init script for installing Python dependencies
# This runs once when the cluster starts, before any notebooks execute

set -euo pipefail

echo "Installing Python dependencies..."

# pandas and numpy are preinstalled on Databricks
pip install --upgrade pip
pip install cdsapi pygrib azure-storage-blob
echo "Dependencies installed successfully!"
