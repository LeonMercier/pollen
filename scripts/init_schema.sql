-- Schema initialization for local PostgreSQL
-- This file is automatically run when the container first starts
-- Needs to stay in sync with the schema defined in notebooks/load.py

CREATE TABLE IF NOT EXISTS public.pollen_forecast (
    id SERIAL PRIMARY KEY,
    start_date TIMESTAMP NOT NULL,
    load_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    constituent_type VARCHAR(50) NOT NULL,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    constituent_value DOUBLE PRECISION NOT NULL,
    forecast_time INT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_forecast_time 
    ON public.pollen_forecast(forecast_time DESC);

CREATE INDEX IF NOT EXISTS idx_constituent 
    ON public.pollen_forecast(constituent_type);

CREATE INDEX IF NOT EXISTS idx_location 
    ON public.pollen_forecast(latitude, longitude);
