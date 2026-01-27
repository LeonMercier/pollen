## Extract

## Dev environment

```
python3.13 -m venv .venv
source ./venv/bin/activate
npm install -g azure-functions-core-tools@4
npm install -g azurite
sudo dnf install azure-cli
pip install -r requirements.txt
pip install -r azure_functions/requirements.txt
az login
az account set --subscription "your-subscription-id"
az ad sp create-for-rbac --role="Contributor" --scopes="/subscriptions/<SUBSCRIPTION_ID>"
```

use the output to create your .env like this

- appId => ARM_CLIENT_ID
- password => ARM_CLIENT_SECRET
- tenant => ARM_TENANT_ID
- ARM_SUBSCRIPTION_ID comes from `az account list` field "id"

## Start your session

```
source ./venv/bin/activate
source .env
azurite --skipApiVersionCheck
tf init
```

### Environment variables needed

- CDSAPI_URL
- CDSAPI_KEY

for local development these can be in azure_functions/local.settings.json in "Values"

cdsapi tries to read api keys from $HOME/.cdsapirc if they dont exist otherwise
