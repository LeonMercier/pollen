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

