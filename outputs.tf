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

# SQL Database
output "sql_server_name" {
  description = "SQL Server name"
  value       = azurerm_mssql_server.sql.name
}

output "sql_server_fqdn" {
  description = "SQL Server fully qualified domain name (for connections)"
  value       = azurerm_mssql_server.sql.fully_qualified_domain_name
}

output "sql_database_name" {
  description = "SQL Database name"
  value       = azurerm_mssql_database.sqldb.name
}

output "sql_admin_username" {
  description = "SQL Server admin username"
  value       = var.sql_admin_username
}

output "sql_admin_password" {
  description = "SQL Server admin password (sensitive - use: terraform output -raw sql_admin_password)"
  value       = random_password.sql_admin.result
  sensitive   = true
}

output "sql_connection_string" {
  description = "SQL Server connection string (without password)"
  value       = "Server=${azurerm_mssql_server.sql.fully_qualified_domain_name};Database=${azurerm_mssql_database.sqldb.name};User Id=${var.sql_admin_username};Encrypt=true;"
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

