# This file just passes through outputs from the module, hence descriptions are omitted

# Resource Group
output "resource_group_name" { value = module.pollen.resource_group_name }
output "resource_group_location" { value = module.pollen.resource_group_location }

# Databricks
output "databricks_workspace_url" { value = module.pollen.databricks_workspace_url }
output "databricks_workspace_id" { value = module.pollen.databricks_workspace_id }

# Key Vault
output "key_vault_name" { value = module.pollen.key_vault_name }
output "key_vault_uri" { value = module.pollen.key_vault_uri }

# PostgreSQL Database
output "postgres_server_name" { value = module.pollen.postgres_server_name }
output "postgres_server_fqdn" { value = module.pollen.postgres_server_fqdn }
output "postgres_database_name" { value = module.pollen.postgres_database_name }
output "postgres_admin_username" { value = module.pollen.postgres_admin_username }
output "postgres_admin_password" {
  value     = module.pollen.postgres_admin_password
  sensitive = true
}
output "postgres_connection_string" {
  value     = module.pollen.postgres_connection_string
  sensitive = true
}

# Data Factory
output "data_factory_name" { value = module.pollen.data_factory_name }
output "data_factory_id" { value = module.pollen.data_factory_id }
output "data_factory_principal_id" { value = module.pollen.data_factory_principal_id }

# Static Website
output "static_website_url" { value = module.pollen.static_website_url }
output "web_storage_account_name" { value = module.pollen.web_storage_account_name }
output "web_storage_account_key" {
  value     = module.pollen.web_storage_account_key
  sensitive = true
}

# App Service
output "app_service_url" { value = module.pollen.app_service_url }
output "app_service_name" { value = module.pollen.app_service_name }
output "app_service_plan_name" { value = module.pollen.app_service_plan_name }
