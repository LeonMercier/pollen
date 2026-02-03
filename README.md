## Extract

## Dev environment

```
python3.13 -m venv .venv
source ./venv/bin/activate
dnf install azure-cli terraform
pip install -r requirements.txt
az login
az account set --subscription "your-subscription-id"
az ad sp create-for-rbac --role="Contributor" --scopes="/subscriptions/<SUBSCRIPTION_ID>"
```

use the output to create your .env like this

- ARM_SUBSCRIPTION_ID comes from `az account list` field "id"

### terraform.tfvars

- cdsapi_key = "your_api_key"
- admin_email = "your_email_for_azure_cost_alerts"

## Start your session

```
source ./venv/bin/activate
source .env
terraform init
```

## Deploy

```
terraform plan
terraform apply
```
