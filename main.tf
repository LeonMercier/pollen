# ========================================
# SECTION 1: Terraform & Provider Configuration
# ========================================

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

# Databricks provider - uses Azure CLI authentication
# Terraform knows to create the azure resource below first, then use it here
provider "databricks" {
  host = azurerm_databricks_workspace.dbw.workspace_url
}

# For generating random passwords
provider "random" {}

# ========================================
# SECTION 2: Data Sources
# ========================================

# Get current Azure client configuration (for tenant ID, object ID)
# Essentially because I am logged in with `az login`, Terraform can query
# this information on its own
data "azurerm_client_config" "current" {}

# ========================================
# SECTION 3: Random Resources
# ========================================

# Random suffix for globally unique resource names
resource "random_string" "unique" {
  length  = 6
  special = false
  upper   = false
}

# Random password for SQL Server administrator
resource "random_password" "sql_admin" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
  min_lower        = 1
  min_upper        = 1
  min_numeric      = 1
  min_special      = 1
}

# ========================================
# SECTION 4: Resource Group
# ========================================

resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.app_name}-${substr(var.location, 0, 2)}"
  location = var.location

  tags = {
    ManagedBy = "Terraform"
    Project   = "Pollen-ETL"
  }
}

# ========================================
# SECTION 5: Key Vault (Secrets Management)
# ========================================

resource "azurerm_key_vault" "kv" {
  name                       = "kv-${var.app_name}-${random_string.unique.result}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7     # Minimum for cost savings
  purge_protection_enabled   = false # Allows immediate recreate during development

  tags = azurerm_resource_group.rg.tags
}

# Access policy for your user (to manage secrets)
resource "azurerm_key_vault_access_policy" "user" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Get", "List", "Set", "Delete", "Purge", "Recover"
  ]
}

# Access policy for Data Factory managed identity (read-only)
resource "azurerm_key_vault_access_policy" "adf" {
  key_vault_id = azurerm_key_vault.kv.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_data_factory.adf.identity[0].principal_id

  secret_permissions = [
    "Get", "List"
  ]

  depends_on = [azurerm_data_factory.adf]
}

# Store SQL admin password in Key Vault
resource "azurerm_key_vault_secret" "sql_password" {
  name         = "sql-admin-password"
  value        = random_password.sql_admin.result
  key_vault_id = azurerm_key_vault.kv.id

  depends_on = [azurerm_key_vault_access_policy.user]
}

# ========================================
# SECTION 6: Azure SQL Database
# ========================================

resource "azurerm_mssql_server" "sql" {
  name                         = "sql-${var.app_name}-${random_string.unique.result}"
  resource_group_name          = azurerm_resource_group.rg.name
  location                     = azurerm_resource_group.rg.location
  version                      = "12.0"
  administrator_login          = var.sql_admin_username
  administrator_login_password = random_password.sql_admin.result

  tags = azurerm_resource_group.rg.tags
}

resource "azurerm_mssql_database" "sqldb" {
  name      = "sqldb-${var.app_name}"
  server_id = azurerm_mssql_server.sql.id
  sku_name  = "Basic"

  max_size_gb = 2 # Basic tier limit

  tags = azurerm_resource_group.rg.tags
}

# Allow Azure services to access SQL Server (required for Data Factory, Databricks)
# A separate rule can be created to allow direct access from outside
resource "azurerm_mssql_firewall_rule" "allow_azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_mssql_server.sql.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# ========================================
# SECTION 7: Databricks Workspace
# ========================================

resource "azurerm_databricks_workspace" "dbw" {
  name                = "dbw-${var.app_name}-${substr(var.location, 0, 2)}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "standard"

  tags = azurerm_resource_group.rg.tags
}

# Grant Data Factory Managed Identity access to Databricks workspace
# This allows Data Factory to authenticate using Managed Identity instead of PAT token
resource "azurerm_role_assignment" "adf_databricks" {
  scope                = azurerm_databricks_workspace.dbw.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_data_factory.adf.identity[0].principal_id

  depends_on = [
    azurerm_databricks_workspace.dbw,
    azurerm_data_factory.adf
  ]
}

# ========================================
# SECTION 8: Data Factory (Orchestration)
# ========================================

# 8.1: Data Factory Resource
resource "azurerm_data_factory" "adf" {
  name                = "adf-${var.app_name}-${substr(var.location, 0, 2)}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  # Enable system-assigned managed identity for Key Vault access
  identity {
    type = "SystemAssigned"
  }

  tags = azurerm_resource_group.rg.tags
}

# 8.2: Linked Service - Key Vault
resource "azurerm_data_factory_linked_service_key_vault" "kv" {
  name            = "ls-keyvault"
  data_factory_id = azurerm_data_factory.adf.id
  key_vault_id    = azurerm_key_vault.kv.id
}

# 8.3: Linked Service - Databricks (with Managed Identity authentication)
resource "azurerm_data_factory_linked_service_azure_databricks" "dbw" {
  name            = "ls-databricks"
  data_factory_id = azurerm_data_factory.adf.id

  # New cluster configuration (ephemeral - spins up per job, then destroys)
  new_cluster_config {
    node_type             = "Standard_D2as_v5" # Smallest available in Sweden Central
    cluster_version       = "17.3.x-scala2.13" # Latest LTS Spark version
    min_number_of_workers = 1                  # Minimum cluster size
    max_number_of_workers = 1                  # Fixed size for cost control
  }

  adb_domain                 = "https://${azurerm_databricks_workspace.dbw.workspace_url}"
  msi_work_space_resource_id = azurerm_databricks_workspace.dbw.id

  depends_on = [
    azurerm_role_assignment.adf_databricks # Wait for permissions to be granted
  ]
}

# 8.4: Linked Service - Azure SQL Database
resource "azurerm_data_factory_linked_service_azure_sql_database" "sql" {
  name            = "ls-sql"
  data_factory_id = azurerm_data_factory.adf.id

  connection_string = "Server=tcp:${azurerm_mssql_server.sql.fully_qualified_domain_name},1433;Initial Catalog=${azurerm_mssql_database.sqldb.name};Encrypt=true;TrustServerCertificate=false;Connection Timeout=30;User ID=${var.sql_admin_username};"

  # Use Key Vault for password
  key_vault_password {
    linked_service_name = azurerm_data_factory_linked_service_key_vault.kv.name
    secret_name         = "sql-admin-password"
  }
}

# 8.5: Pipeline - ETL Workflow
resource "azurerm_data_factory_pipeline" "etl" {
  name            = "pipeline-pollen-etl"
  data_factory_id = azurerm_data_factory.adf.id

  # Pipeline contains a single Databricks Notebook activity
  # The notebook path should match where you upload your notebook in Databricks
  activities_json = jsonencode([
    {
      name = "Run-ETL-Notebook"
      type = "DatabricksNotebook"

      dependsOn = []

      typeProperties = {
        # Update this path after creating your notebook in Databricks
        # Path should be relative to Databricks workspace root
        # Example: /Workspace/Users/your.email@domain.com/etl_pipeline
        # Or if using Repos: /Repos/your-repo/notebooks/etl_pipeline
        notebookPath = "/Workspace/notebooks/etl_pipeline"

        # Optional: Pass parameters to your notebook
        baseParameters = {
          # Example: environment = "production"
        }
      }

      linkedServiceName = {
        referenceName = azurerm_data_factory_linked_service_azure_databricks.dbw.name
        type          = "LinkedServiceReference"
      }
    }
  ])

  depends_on = [
    azurerm_data_factory_linked_service_azure_databricks.dbw,
    azurerm_data_factory_linked_service_key_vault.kv,
    azurerm_data_factory_linked_service_azure_sql_database.sql
  ]
}

# 8.6: Trigger - Hourly Schedule
resource "azurerm_data_factory_trigger_schedule" "hourly" {
  name            = "trigger-hourly-etl"
  data_factory_id = azurerm_data_factory.adf.id
  pipeline_name   = azurerm_data_factory_pipeline.etl.name

  frequency = "Hour"
  interval  = 1

  activated = false # Start disabled, hast obe enabled manually

  schedule {
    minutes = [5]
  }
}
