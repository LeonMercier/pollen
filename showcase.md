---
title:
  - Pollen ETL project
author:
  - Léon Mercier
theme:
  - Luebeck
date:
  - 22.2.2026
---

# What is this?

An ETL pipeline that downloads a pollen allergy forecast, builds charts from it and publishes them on the web

## Check it out

Repo: [https://github.com/LeonMercier/pollen](https://github.com/LeonMercier/pollen)

Static site: [https://stwebpollenprod.z1.web.core.windows.net/](https://stwebpollenprod.z1.web.core.windows.net/)

# Motivation

- Learn:
  - Data engineering concepts
  - Python
  - Databricks
  - Azure services
  - Infrastructure as code
- Create a resource for pollen allergy sufferers to manage their symptoms
  - Easily see what days and times of day symptoms are likely to happen

# What already exists

## norkko.fi

- Lack of details:
  - Pollen level: scale from 0 to 3
  - Forecast: three days, no hourly data
  - Only a few locations
- In reality pollen levels vary wildly depending on time of day and weather
- [https://norkko.fi/](https://norkko.fi/)

## EU Copernicus website

- Has animated map and charts
- Hard to discover and navigate
- Not user friendly
- [https://atmosphere.copernicus.eu/charts/packages/cams_air_quality/](https://atmosphere.copernicus.eu/charts/packages/cams_air_quality/)

# The data source

- EU Copernicus: European Union's Earth Observation Programme
- Releases daily
- 96 hours length, 1 hour granularity
- All of continental Europe and Iceland
- 0.1 degree grid (about 10 km x 10 km grid cells)
- Six pollen types

# The pipeline

- Each stage as a Databricks notebook
- Trigger daily from Azure Data Factory
- Use Databricks widgets to pass return values between stages
- Medallion architecture
  - Bronze: GRIB file
  - Silver: Parquet file
  - Gold: SQL database

- Sample from the SQL table

\tiny

| id  | start_date | load_timestamp | constituent_type | latitude  | longitude | constituent_value | forecast_time |
| --- | ---------- | -------------- | ---------------- | --------- | --------- | ----------------- | ------------- |
| 1   | 2026-02-22 | 2026-02-22     | Alnus            | 60.950000 | 2.050000  | 6.7680            | 0             |
| 12  | 2026-02-22 | 2026-02-22     | Betula           | 60.950000 | 2.050000  | 8.2321            | 0             |
| 55  | 2026-02-22 | 2026-02-22     | Alnus            | 55.250000 | 23.150000 | 0.1231            | 2             |
| 453 | 2026-02-22 | 2026-02-22     | Betula           | 54.150000 | 2.050000  | 0.1432            | 2             |

\normalsize

# Extract

- Use `CDSApi` package
- Formulate request for current date
- Execute request
- Save data to Datacricks storage
- Return filename (uses Databricks widgets)

# Transform

- GRIB binary format: process with `pygrib` package
- Data is gridded, needs to be flattened for SQL
- 700\*420 grid cells \* 96 hours \* 6 pollen types:
  - turns into 170 million rows in long format
- file contains multiple messages containing a complete geographical grid
  - ex. 5 pollen types \* 6 forecast time points = 30 messages
- extract the coordinates of the grid
- extract value for each grid point
- flatten everything and put in a dict
- transform dict into a dataframe
- Save as parquet to Databricks storage

# Load

- Create the database schema if it doesnt exist
- Read parquet file from transform stage
- Add timestamp for when data is loaded
- Use `TRUNCATE` so that old forecast it overwritten
- Question: This is a big write: will the database return inconsistent data during the write?
  - Do we need to write into a temporary table and then swap tables when everything is written?

# Plot

\small

- Use `plotly` package
  - Creates plots that are web-native and can be embedded into a web page as responsive components
- Read from SQL
- In the data `forecast_time` is given as hours since start of forecast
  - calculate actual datetimes for nicer presentation
- Generate plots, glue them together into on HTML file
- Upload to Azure web storage

\normalsize

![image](static-site-screenshot-2026-02-23-cropped.png)

# Infrastructure

- Terraform was adopted early:
  - Clicking in Azure portal is tedious
  - `terraform destroy` is a nice assurance that everything goes down and no costs are incurred
  - Goal is to have the Gitub repo in a state where someone can clone it and get started very quickly

# Future directions

- Move from MSSQL to PostgreSQL for cost savings
- Get a domain name
- Localize plots to Finnish
- Localize pollen types from Latin to English
- Implements history browser (but needs different database strategy?)
- Make a nicer looking web frontend
- Create a backend service
  - User requests "Helsinki" -> backend finds correct grid cell and generates plot
- Allow users to subscribe to alerts via email
- Mobile app
  - Homescreen widget
  - Native notifications
