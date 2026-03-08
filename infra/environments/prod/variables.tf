variable "location" {
  description = "Azure region for all resources"
  type        = string
}
variable "app_name" {
  description = "Application name used in resource naming"
  type        = string
}
variable "postgres_admin_username" {
  description = "Azure PostgreSQL Flexible Server administrator username"
  type        = string
}
variable "cdsapi_url" {
  description = "CDSAPI URL endpoint for Copernicus Atmosphere Data Store"
  type        = string
}
variable "cdsapi_key" {
  description = "CDSAPI authentication key (UID:API-key format)"
  type        = string
  sensitive   = true
}
variable "admin_email" {
  description = "Email address for PostgreSQL database monitoring alerts"
  type        = string
}
variable "postgres_sku_name" {
  description = "SKU for the PostgreSQL Flexible Server (e.g., B_Standard_B1ms, GP_Standard_D2s_v3)"
  type        = string
}
variable "databricks_node_type" {
  description = "SKU for Databricks compute"
  type        = string
}
variable "adf_trigger_activated" {
  description = "Should the Data Factory pipeline start as activated"
  type        = bool
}

variable "database_sslmode" {
  description = "PostgreSQL SSL mode for App Service connections"
  type        = string
  default     = "require"
}
