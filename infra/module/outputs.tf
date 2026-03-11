# ========================================
# Outputs - Deployment Information
# ========================================

# Resource Group
output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.rg.name
}

output "resource_group_location" {
  description = "Location of the resource group"
  value       = azurerm_resource_group.rg.location
}

# Databricks
output "databricks_workspace_url" {
  description = "URL to access Databricks workspace"
  value       = "https://${azurerm_databricks_workspace.dbw.workspace_url}"
}

output "databricks_workspace_id" {
  description = "Databricks workspace resource ID"
  value       = azurerm_databricks_workspace.dbw.id
}

# Key Vault
output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.kv.name
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = azurerm_key_vault.kv.vault_uri
}

# PostgreSQL Database
output "postgres_server_name" {
  description = "PostgreSQL Flexible Server name"
  value       = azurerm_postgresql_flexible_server.postgres.name
}

output "postgres_server_fqdn" {
  description = "PostgreSQL Server fully qualified domain name (for connections)"
  value       = azurerm_postgresql_flexible_server.postgres.fqdn
}

output "postgres_database_name" {
  description = "PostgreSQL Database name"
  value       = azurerm_postgresql_flexible_server_database.pollen.name
}

output "postgres_admin_username" {
  description = "PostgreSQL Server admin username"
  value       = var.postgres_admin_username
}

output "postgres_admin_password" {
  description = "PostgreSQL Server admin password (sensitive - use: terraform output -raw postgres_admin_password)"
  value       = random_password.postgres_admin.result
  sensitive   = true
}

output "postgres_connection_string" {
  description = "PostgreSQL Server connection string (without password)"
  value       = "Host=${azurerm_postgresql_flexible_server.postgres.fqdn};Port=5432;Database=${azurerm_postgresql_flexible_server_database.pollen.name};Username=${var.postgres_admin_username};Ssl Mode=Require;"
  sensitive   = true
}

# Data Factory
output "data_factory_name" {
  description = "Data Factory name"
  value       = azurerm_data_factory.adf.name
}

output "data_factory_id" {
  description = "Data Factory resource ID"
  value       = azurerm_data_factory.adf.id
}

output "data_factory_principal_id" {
  description = "Data Factory Managed Identity principal ID"
  value       = azurerm_data_factory.adf.identity[0].principal_id
}

# ========================================
# Static Website Outputs
# ========================================

output "static_website_url" {
  description = "URL to access the static website hosting Plotly charts"
  value       = azurerm_storage_account.web.primary_web_endpoint
}

output "web_storage_account_name" {
  description = "Storage account name for static website (used by plot.py)"
  value       = azurerm_storage_account.web.name
}

output "web_storage_account_key" {
  description = "Storage account primary access key (sensitive - use: terraform output -raw web_storage_account_key)"
  value       = azurerm_storage_account.web.primary_access_key
  sensitive   = true
}

# ========================================
# App Service Outputs
# ========================================

output "app_service_url" {
  description = "URL to access the FastAPI application"
  value       = try("https://${azurerm_linux_web_app.api[0].default_hostname}", "")
}

output "app_service_name" {
  description = "App Service name"
  value       = try(azurerm_linux_web_app.api[0].name, "")
}

output "app_service_plan_name" {
  description = "App Service Plan name"
  value       = try(azurerm_service_plan.api[0].name, "")
}

output "app_service_principal_id" {
  description = "App Service Managed Identity principal ID"
  value       = try(azurerm_linux_web_app.api[0].identity[0].principal_id, "")
}
