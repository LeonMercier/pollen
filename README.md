# Pollen ETL project

This is a work in progress ETL pipeline for visualizing pollen forecast data from [the EU Copernicus programme](https://atmosphere.copernicus.eu/). The pipeline is deployed on Azure and you can see outputs live [here](http://www.pollencast.eu/), with updates once per day!!

Check out the project description and goals [here](showcase.pdf).

## Tech used

- Orchestration: Azure Data Factory
- ETL pipeline: pySpark on Databricks
- Database: Azure PostgreSQL Flexible Server
- Backend: FastAPI on Azure App Service
- Visualizations: plotly
- Frontend: hosted on Azure blob storage
- Infrastructure as Code: Terraform

## Setting up the dev environment

Clone this repo and then do the following:

Create local python environment. The notebook code cannot run locally, but at least you can get hints in your IDE.

```
python3.12 -m venv .venv
source ./venv/bin/activate
pip install -r requirements.txt
```

Install packages. These instructions are for Fedora, adapt accordingly to your environment.

```
dnf install azure-cli terraform
```

Set up your Azure access. Your subscription ID should be in the output of the first command.

```
az login
az account set --subscription "your-subscription-id"
az ad sp create-for-rbac --role="Contributor" --scopes="/subscriptions/<SUBSCRIPTION_ID>"
```

Run `az account list` and use the field 'id' to create a `.env` file that looks like below:

```
export ARM_SUBSCRIPTION_ID="your_subscription_id"
```

The rest of your environment will be managed by Terraform. Information about the CDS API keys [here](https://ads.atmosphere.copernicus.eu/how-to-api). Create a terraform.tfvars file:

```
cdsapi_key = "your_api_key"
admin_email = "your_email_for_azure_cost_alerts"
```

And finally run `terraform init` in `environments/dev` and `environemnts/prod`.

## Local Development (FastAPI)

The notebooks and cloud infrastructure remain in Azure, but you can develop and test the FastAPI application locally with a PostgreSQL database running in Docker.

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Azure CLI (for syncing data from Azure)
- [go-task](https://taskfile.dev/) (task runner)
- PostgreSQL client tools (`pg_dump`, `psql`)

### First-Time Setup

1. **Check prerequisites:**

   ```bash
   task check:prereqs
   ```

2. **Set up local environment:**

   ```bash
   task local:setup
   ```

   This will:
   - Start PostgreSQL 16 in Docker (matching Azure version)
   - Create the database schema
   - Sync data from Azure dev environment

3. **Run the API:**
   ```bash
   task local:api
   ```
   The API will be available at http://localhost:8000 with auto-reload enabled.

### Daily Development Workflow

```bash
# Start PostgreSQL (if not running)
task local:up

# Run the API with auto-reload
task local:api

# In another terminal: view database logs if needed
task local:logs

# Stop PostgreSQL when done (data persists)
task local:down
```

### Common Tasks

```bash
task --list              # Show all available tasks
task local:up            # Start PostgreSQL container
task local:down          # Stop PostgreSQL container
task local:sync          # Sync fresh data from Azure
task local:shell         # Open psql shell to local database
task local:reset         # Reset database (deletes all data)
task local:status        # Check container status
```

### Refreshing Data

To get the latest data from Azure dev environment:

```bash
task local:sync
```

This requires:

- You're logged in with `az login`
- You have access to the Key Vault

### Troubleshooting

**Connection refused:**

```bash
# Check if PostgreSQL is running
docker ps | grep pollen-postgres

# View logs
task local:logs
```

**Environment variable issues:**
Make sure `.env.local` exists in the project root. It should be auto-created but you can verify it contains:

```bash
ENV=local
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=pollen
DATABASE_USER=pollen_user
DATABASE_PASSWORD=local_dev_password
DATABASE_SSLMODE=disable
AZURE_KEY_VAULT_NAME=your-keyvault-name
```

## Start your development session

```
source ./venv/bin/activate
source .env
az login
```

## Create the infrastructure

```
terraform apply
```

This will create all the infra on Azure. The pipeline will be set to disabled on Data Factory and you will need to enable it manually.For testing, it is better to spin up a Databricks cluster manually from the Databricks workspace. When doing that remember to set the cluster init script to the one that is uploaded under shared files.
