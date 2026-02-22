terraform {
  required_version = ">= 1.1.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

# Providers have to be defined in the root config, not in modules

provider "azurerm" {
  features {
    # Key Vault settings for easier development workflow
    key_vault {
      purge_soft_delete_on_destroy    = true # Allows immediate recreation
      recover_soft_deleted_key_vaults = true
    }
  }
  use_cli = true
}

# Databricks provider with Azure CLI authentication
provider "databricks" {
  azure_workspace_resource_id = module.pollen.databricks_workspace_id
}

# For generating random passwords
provider "random" {}

# Call the pollen-stack module
# variable values come from variables.tf
module "pollen" {
  source = "../../module"

  environment           = "prod"
  location              = var.location
  app_name              = var.app_name
  sql_admin_username    = var.sql_admin_username
  cdsapi_url            = var.cdsapi_url
  cdsapi_key            = var.cdsapi_key
  admin_email           = var.admin_email
  sql_sku_name          = var.sql_sku_name
  databricks_node_type  = var.databricks_node_type
  adf_trigger_activated = var.adf_trigger_activated
}
