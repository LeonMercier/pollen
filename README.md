## Extract

## Setting up the dev environment

Clone this repo and then do the following:

Create local python environment. The code cannot run locally, but at least you can get hints in your IDE.

```
python3.13 -m venv .venv
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

The rest of your environment will be managed by Terraform. Create a terraform.tfvars file:

```
cdsapi_key = "your_api_key"
admin_email = "your_email_for_azure_cost_alerts"
```

And finally run `terraform init`.

## Start your development session

```
source ./venv/bin/activate
source .env
az login
```

## Deploy changes

```
terraform apply
```
