# ========================================
# SECTION 11: Azure App Service (FastAPI)
# ========================================

# 11.1: App Service Plan (Linux, Free F1 tier)
resource "azurerm_service_plan" "api" {
  name                = "asp-${var.app_name}-${var.environment}-${substr(var.location, 0, 2)}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = var.app_service_sku_name

  tags = azurerm_resource_group.rg.tags
}

# 11.2: Linux Web App for FastAPI
resource "azurerm_linux_web_app" "api" {
  name                = "app-${var.app_name}-api-${var.environment}-${random_string.unique.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  service_plan_id     = azurerm_service_plan.api.id

  # Enable system-assigned managed identity for Key Vault access
  identity {
    type = "SystemAssigned"
  }

  # Site configuration
  site_config {
    # Python 3.11 runtime
    application_stack {
      python_version = var.python_runtime_version
    }

    # Azure routes connections to port 8000
    app_command_line = "python -m uvicorn main:app --host 0.0.0.0 --port 8000"

    # Always on (not available in Free tier, will be ignored)
    always_on = false

    # Health check endpoint (if we have a health check, then the eviction tim
    # is needed too.
    health_check_path                 = "/health"
    health_check_eviction_time_in_min = 2
  }

  # Application settings (environment variables)
  app_settings = {
    # Build settings
    "SCM_DO_BUILD_DURING_DEPLOYMENT"      = "true"
    "ENABLE_ORYX_BUILD"                   = "true"
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "false"

    # Database connection settings (from Key Vault)
    # Note: Key Vault references require the App Service managed identity to have access
    "DATABASE_HOST"     = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.postgres_fqdn.versionless_id})"
    "DATABASE_PORT"     = "5432"
    "DATABASE_NAME"     = azurerm_postgresql_flexible_server_database.pollen.name
    "DATABASE_USER"     = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.postgres_username.versionless_id})"
    "DATABASE_PASSWORD" = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.postgres_password.versionless_id})"
    "DATABASE_SSLMODE"  = var.database_sslmode
  }

  # ZIP deployment configuration
  # Terraform will package and deploy the ./api directory
  # zip_deploy_file = data.archive_file.api_code.output_path

  tags = azurerm_resource_group.rg.tags

  # Lifecycle rule
  # lifecycle {
  #   ignore_changes = [
  #     zip_deploy_file # Ignore changes to deployment package hash
  #   ]
  # }

  # Ensure Key Vault secrets and access policy are created before App Service app_settings reference them
  depends_on = [
    azurerm_key_vault_secret.postgres_fqdn,
    azurerm_key_vault_secret.postgres_username,
    azurerm_key_vault_secret.postgres_password
  ]
}

# 11.2.1: Key Vault access policy for App Service managed identity
# This allows the App Service to read database credentials from Key Vault
resource "azurerm_key_vault_access_policy" "app_service" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = try(azurerm_linux_web_app.api.identity[0].tenant_id, data.azurerm_client_config.current.tenant_id)
  object_id    = try(azurerm_linux_web_app.api.identity[0].principal_id, "")

  secret_permissions = [
    "Get"
  ]

  depends_on = [
    azurerm_linux_web_app.api,
    azurerm_key_vault_access_policy.user
  ]
}

# 11.3: Archive API code for deployment
# This packages the ./api directory into a zip file
data "archive_file" "api_code" {
  type        = "zip"
  source_dir  = "${path.module}/../../api"
  output_path = "${path.module}/.terraform/api-deploy.zip"
}
