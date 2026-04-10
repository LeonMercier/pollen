-- Schema initialization for local PostgreSQL
-- This file is automatically run when the container first starts
-- Needs to stay in sync with the schema defined in notebooks/load.py
--
-- PRODUCTION DEPLOYMENT PATTERN (notebooks/load.py):
-- The production ETL pipeline uses a blue-green deployment strategy for zero-downtime updates:
--   1. Load new data into pollen_forecast_staging table
--   2. Build indexes on staging table (production stays fast)
--   3. Validate staging data (constituent count, row count)
--   4. Atomically swap: staging → production (including indexes)
--   5. Drop old production table and indexes
-- This ensures the API always has access to complete, indexed data.
--
-- LOCAL DEVELOPMENT:
-- For local dev, we only create the production table since we don't need zero-downtime.
-- Indexes are created immediately since the database starts empty.

-- No primary key, not strictly necessary, improve performance
CREATE TABLE IF NOT EXISTS public.pollen_forecast (
    start_date TIMESTAMP NOT NULL,
    load_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    constituent_type VARCHAR(50) NOT NULL,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    constituent_value DOUBLE PRECISION NOT NULL,
    forecast_time INT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_location 
    ON public.pollen_forecast(latitude, longitude);

-- Cities table for geocoding support
-- Needs to stay in sync with the schema defined in notebooks/geocode.py
CREATE TABLE IF NOT EXISTS public.cities (
    id SERIAL PRIMARY KEY,
    geoname_id INTEGER NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    ascii_name VARCHAR(200) NOT NULL,
    country_code CHAR(2) NOT NULL,
    admin1_code VARCHAR(20),
    population BIGINT,
    timezone VARCHAR(40),
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    pollen_latitude DECIMAL(9,6) NOT NULL,
    pollen_longitude DECIMAL(9,6) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cities_name ON public.cities (name);
CREATE INDEX IF NOT EXISTS idx_cities_ascii_name ON public.cities (ascii_name);
CREATE INDEX IF NOT EXISTS idx_cities_country ON public.cities (country_code);
CREATE INDEX IF NOT EXISTS idx_cities_pollen_location ON public.cities (pollen_latitude, pollen_longitude);
CREATE INDEX IF NOT EXISTS idx_cities_geoname ON public.cities (geoname_id);
