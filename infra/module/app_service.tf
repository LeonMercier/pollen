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
    "SCM_DO_BUILD_DURING_DEPLOYMENT"      = "true"
    "ENABLE_ORYX_BUILD"                   = "true"
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "false"
  }

  # ZIP deployment configuration
  # Terraform will package and deploy the ./api directory
  zip_deploy_file = data.archive_file.api_code.output_path

  tags = azurerm_resource_group.rg.tags
}

# 11.3: Archive API code for deployment
# This packages the ./api directory into a zip file
data "archive_file" "api_code" {
  type        = "zip"
  source_dir  = "${path.module}/../../api"
  output_path = "${path.module}/.terraform/api-deploy.zip"
}
