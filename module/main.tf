# ========================================
# SECTION 1: Terraform & Provider Configuration
# ========================================

# While providers are configured in the root config, provider requirements
# for the module are defined (also) here in the module
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

# ========================================
# SECTION 2: Data Sources
# ========================================

# Get current Azure client configuration (for tenant ID, object ID)
# Essentially when you are logged in with `az login`, Terraform can query
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
  name     = "rg-${var.app_name}-${var.environment}-${substr(var.location, 0, 2)}"
  location = var.location

  tags = {
    Environment = var.environment
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

# Store SQL Server FQDN in Databricks secret scope
resource "databricks_secret" "sql_server_fqdn" {
  scope        = databricks_secret_scope.secrets.name
  key          = "sql-server-fqdn"
  string_value = azurerm_mssql_server.sql.fully_qualified_domain_name

  depends_on = [databricks_secret_scope.secrets]
}

# Store SQL admin username in Databricks secret scope
resource "databricks_secret" "sql_admin_username" {
  scope        = databricks_secret_scope.secrets.name
  key          = "sql-admin-username"
  string_value = var.sql_admin_username

  depends_on = [databricks_secret_scope.secrets]
}

# Store SQL admin password in Databricks secret scope
resource "databricks_secret" "sql_admin_password" {
  scope        = databricks_secret_scope.secrets.name
  key          = "sql-admin-password"
  string_value = random_password.sql_admin.result

  depends_on = [databricks_secret_scope.secrets]
}

# CDSAPI URL secret
resource "azurerm_key_vault_secret" "cdsapi_url" {
  name         = "cdsapi-url"
  value        = var.cdsapi_url
  key_vault_id = azurerm_key_vault.kv.id

  depends_on = [azurerm_key_vault_access_policy.user]
}

# CDSAPI Key secret
resource "azurerm_key_vault_secret" "cdsapi_key" {
  name         = "cdsapi-key"
  value        = var.cdsapi_key
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

  sku_name = var.sql_sku_name

  # Free tier limits
  max_size_gb = 32 # Free tier maximum

  # Serverless configuration
  auto_pause_delay_in_minutes = 15  # Auto-pause after 15 min idle 
  min_capacity                = 0.5 # Minimum 0.5 vCores when active

  # Storage redundancy (free tier requirement)
  storage_account_type = "Local" # LRS only for free tier

  # Backup retention (free tier limit)
  short_term_retention_policy {
    retention_days = 7 # Maximum for free tier
  }

  tags = azurerm_resource_group.rg.tags
}

# Allow Azure services to access SQL Server (required for Data Factory, Databricks)
# A separate rule can be created to allow direct access from outside
resource "azurerm_mssql_firewall_rule" "allow_azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_mssql_server.sql.id
  # 0.0.0.0 is a spacial value allowing everything isnide of Azure
  # https://learn.microsoft.com/fi-fi/rest/api/sql/firewall-rules/create-or-update
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

# Create Databricks-managed secret scope
# Secrets are stored in Databricks (encrypted at rest), not in Azure Key Vault
# This works with Standard tier Databricks (Premium tier not required)
resource "databricks_secret_scope" "secrets" {
  name = "secrets"

  # No keyvault_metadata block = Databricks-managed scope

  # Standard tier requires initial_manage_principal = "users"
  # This allows all workspace users to manage the scope
  initial_manage_principal = "users"

  depends_on = [
    azurerm_role_assignment.adf_databricks
  ]
}

# Store CDSAPI URL in Databricks secret scope
resource "databricks_secret" "cdsapi_url" {
  scope        = databricks_secret_scope.secrets.name
  key          = "cdsapi-url"
  string_value = var.cdsapi_url

  depends_on = [databricks_secret_scope.secrets]
}

# Store CDSAPI key in Databricks secret scope
resource "databricks_secret" "cdsapi_key" {
  scope        = databricks_secret_scope.secrets.name
  key          = "cdsapi-key"
  string_value = var.cdsapi_key

  depends_on = [databricks_secret_scope.secrets]
}

# ========================================
# SECTION 7.5: Databricks Init Scripts
# ========================================

# Upload init script to Workspace (browseable in Databricks UI)
resource "databricks_workspace_file" "init_script" {
  source = "${path.module}/../scripts/install_dependencies.sh"
  path   = "/Shared/init_scripts/install_dependencies.sh"

  depends_on = [
    azurerm_role_assignment.adf_databricks
  ]
}

# ========================================
# SECTION 8: Databricks Notebooks
# ========================================

# Upload extract notebook
resource "databricks_notebook" "extract" {
  source = "${path.module}/../notebooks/extract.py"
  path   = "/Workspace/notebooks/extract"

  # Ensure workspace and permissions are ready
  depends_on = [
    azurerm_role_assignment.adf_databricks,
    databricks_secret_scope.secrets
  ]
}

# Upload transform notebook
resource "databricks_notebook" "transform" {
  source = "${path.module}/../notebooks/transform.py"
  path   = "/Workspace/notebooks/transform"

  depends_on = [
    azurerm_role_assignment.adf_databricks,
    databricks_secret_scope.secrets
  ]
}

# Upload load notebook
resource "databricks_notebook" "load" {
  source = "${path.module}/../notebooks/load.py"
  path   = "/Workspace/notebooks/load"

  depends_on = [
    azurerm_role_assignment.adf_databricks,
    databricks_secret_scope.secrets
  ]
}

# Upload plot notebook
resource "databricks_notebook" "plot" {
  source = "${path.module}/../notebooks/plot.py"
  path   = "/Workspace/notebooks/plot"

  depends_on = [
    azurerm_role_assignment.adf_databricks,
    databricks_secret_scope.secrets
  ]
}

# ========================================
# SECTION 9: Data Factory (Orchestration)
# ========================================

# 9.1: Data Factory Resource
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

# 9.2: Linked Service - Key Vault
resource "azurerm_data_factory_linked_service_key_vault" "kv" {
  name            = "ls-keyvault"
  data_factory_id = azurerm_data_factory.adf.id
  key_vault_id    = azurerm_key_vault.kv.id
}

# 9.3: Linked Service - Databricks (with Managed Identity authentication)
# This cluster will spin up when the trigger (see below) is activated. 
# when it is activated = false, is will only spin up with manual activation
# from Data Factory UI. In the meantime, dev clusters can be spun up from the 
# Databricks UI. 
resource "azurerm_data_factory_linked_service_azure_databricks" "dbw" {
  name            = "ls-databricks"
  data_factory_id = azurerm_data_factory.adf.id

  # New cluster configuration (ephemeral - spins up per job, then destroys)
  new_cluster_config {
    node_type             = var.databricks_node_type
    cluster_version       = "17.3.x-scala2.13"  # Latest LTS Spark version
    min_number_of_workers = 1                   # Minimum cluster size
    max_number_of_workers = 1                   # Fixed size for cost control

    # Init script to install Python dependencies
    init_scripts = ["workspace:${databricks_workspace_file.init_script.path}"]
  }

  adb_domain       = "https://${azurerm_databricks_workspace.dbw.workspace_url}"
  msi_workspace_id = azurerm_databricks_workspace.dbw.id

  depends_on = [
    azurerm_role_assignment.adf_databricks, # Wait for permissions to be granted
    databricks_workspace_file.init_script   # Ensure init script is uploaded first
  ]
}

# 9.4: Linked Service - Azure SQL Database
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

# 9.5: Pipeline - ETL Workflow
resource "azurerm_data_factory_pipeline" "etl" {
  name            = "pipeline-pollen-etl"
  data_factory_id = azurerm_data_factory.adf.id

  # Pipeline orchestrates Extract → Transform → Load workflow
  # Each notebook runs sequentially on ephemeral Databricks clusters
  activities_json = jsonencode([
    {
      name = "Extract"
      type = "DatabricksNotebook"

      dependsOn = []

      typeProperties = {
        notebookPath = databricks_notebook.extract.path

        baseParameters = {
          # Parameters can be added here if needed
        }
      }

      linkedServiceName = {
        referenceName = azurerm_data_factory_linked_service_azure_databricks.dbw.name
        type          = "LinkedServiceReference"
      }
    },
    {
      name = "Transform"
      type = "DatabricksNotebook"

      # Transform waits for Extract to complete
      dependsOn = [
        {
          activity             = "Extract"
          dependencyConditions = ["Succeeded"]
        }
      ]

      typeProperties = {
        notebookPath = databricks_notebook.transform.path

        baseParameters = {
          input_path = "@activity('Extract').output.runOutput"
        }
      }

      linkedServiceName = {
        referenceName = azurerm_data_factory_linked_service_azure_databricks.dbw.name
        type          = "LinkedServiceReference"
      }
    },
    {
      name = "Load"
      type = "DatabricksNotebook"

      # Load waits for Transform to complete
      dependsOn = [
        {
          activity             = "Transform"
          dependencyConditions = ["Succeeded"]
        }
      ]

      typeProperties = {
        notebookPath = databricks_notebook.load.path

        baseParameters = {
          input_path = "@activity('Transform').output.runOutput"
        }
      }

      linkedServiceName = {
        referenceName = azurerm_data_factory_linked_service_azure_databricks.dbw.name
        type          = "LinkedServiceReference"
      }
    },
    {
      name = "Plot"
      type = "DatabricksNotebook"

      # Plot waits for Load to complete
      dependsOn = [
        {
          activity             = "Load"
          dependencyConditions = ["Succeeded"]
        }
      ]

      typeProperties = {
        notebookPath = databricks_notebook.plot.path

        baseParameters = {
          # No parameters needed for plot
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
    azurerm_data_factory_linked_service_azure_sql_database.sql,
    databricks_notebook.extract,
    databricks_notebook.transform,
    databricks_notebook.load,
    databricks_notebook.plot
  ]
}

# 9.6: Trigger - Daily Schedule at 10:00 UTC
resource "azurerm_data_factory_trigger_schedule" "daily" {
  name            = "trigger-daily-etl"
  data_factory_id = azurerm_data_factory.adf.id
  pipeline_name   = azurerm_data_factory_pipeline.etl.name

  frequency = "Day"
  interval  = 1

  activated = var.adf_trigger_activated

  schedule {
    hours   = [10]
    minutes = [0]
  }
}

# ========================================
# SECTION 10: Static Website Hosting
# ========================================

# Storage account for hosting static HTML charts
# This enables the plot.py notebook to generate and publish Plotly charts
# that are publicly accessible via HTTPS
resource "azurerm_storage_account" "web" {
  name                     = "stweb${var.app_name}${random_string.unique.result}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS" # Locally redundant storage (free tier)

  tags = azurerm_resource_group.rg.tags
}

# Enable static website hosting on the storage account
# Files uploaded to $web container are served via primary_web_endpoint
resource "azurerm_storage_account_static_website" "web" {
  storage_account_id = azurerm_storage_account.web.id
  index_document     = "index.html"
}

# Store storage account name in Databricks secrets
# Used by plot.py to authenticate and upload generated HTML
resource "databricks_secret" "storage_account_name" {
  scope        = databricks_secret_scope.secrets.name
  key          = "web-storage-account-name"
  string_value = azurerm_storage_account.web.name

  depends_on = [databricks_secret_scope.secrets]
}

# Store storage account key in Databricks secrets
# Access key allows plot.py to write HTML files to blob storage
resource "databricks_secret" "storage_account_key" {
  scope        = databricks_secret_scope.secrets.name
  key          = "web-storage-account-key"
  string_value = azurerm_storage_account.web.primary_access_key

  depends_on = [databricks_secret_scope.secrets]
}
