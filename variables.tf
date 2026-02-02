variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "swedencentral"
}

variable "app_name" {
  description = "Application name used in resource naming"
  type        = string
  default     = "pollen"
}

variable "sql_admin_username" {
  description = "Azure SQL Server administrator username"
  type        = string
  default     = "sqladmin"
}

variable "cdsapi_url" {
  description = "CDSAPI URL endpoint for Copernicus Atmosphere Data Store"
  type        = string
  sensitive   = false
  default     = "https://ads.atmosphere.copernicus.eu/api"
}

variable "cdsapi_key" {
  description = "CDSAPI authentication key (UID:API-key format)"
  type        = string
  sensitive   = true
  # No default - must be provided via terraform.tfvars
}

variable "admin_email" {
  description = "Email address for SQL database monitoring alerts"
  type        = string
  # No default - must be provided via terraform.tfvars
}

