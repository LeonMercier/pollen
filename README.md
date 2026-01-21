## Extract

## Dev environment

npm install -g azure-functions-core-tools@4
npm install -g azurite
sudo dnf install azure-cli
az login
mkdir azure_functions && cd azure_functions
func init . --python

az account set --subscription "your-subscription-id"
az ad sp create-for-rbac --role="Contributor" --scopes="/subscriptions/<SUBSCRIPTION_ID>"

use the output to set your .env with
appId => ARM_CLIENT_ID
password => ARM_CLIENT_SECRET
tenant => ARM_TENANT_ID
ARM_SUBSCRIPTION_ID comes from `az account list` field "id"
export ARM_CLIENT_ID="<APPID_VALUE>"
export ARM_CLIENT_SECRET="<PASSWORD_VALUE>"
export ARM_SUBSCRIPTION_ID="<SUBSCRIPTION_ID>"
export ARM_TENANT_ID="<TENANT_VALUE>"

source .env

tf init

### Environment variables needed

- CDSAPI_URL
- CDSAPI_KEY

for local development these can be in azure_functions/local.settings.json in "Values"

cdsapi tries to read api keys from $HOME/.cdsapirc if they dont exist otherwise
