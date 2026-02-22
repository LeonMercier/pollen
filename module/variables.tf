variable "environment" {
  description = "Environment name (dev or prod)"
  type = string
  validation {
    # contains() => the set contains at least one value matching the variable
    condition = contains(["dev", "prod"], var.environment)
    error_message = "Environment must be 'dev' or 'prod'."
  }
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
}

variable "app_name" {
  description = "Application name used in resource naming"
  type        = string
}

variable "sql_admin_username" {
  description = "Azure SQL Server administrator username"
  type        = string
}

variable "cdsapi_url" {
  description = "CDSAPI URL endpoint for Copernicus Atmosphere Data Store"
  type        = string
  sensitive   = false
}

variable "cdsapi_key" {
  description = "CDSAPI authentication key (UID:API-key format)"
  type        = string
  sensitive   = true
}

variable "admin_email" {
  description = "Email address for SQL database monitoring alerts"
  type        = string
}

variable "sql_sku_name" {
  description = "SKU for the SQL server"
  type = string
}

variable "databricks_node_type" {
  description = "SKU for Databricks compute"
  type = string
}

variable "adf_trigger_activated" {
  description = "Should the Data Factory pipeline start as activated"
  type = bool
}
