## Extract

## Dev environment

npm install -g azure-functions-core-tools@4
npm install -g azurite
mkdir azure_functions && cd azure_functions
func init . --python

### Environment variables needed

- CDSAPI_URL
- CDSAPI_KEY

for local development these can be in azure_functions/local.settings.json in "Values"

cdsapi tries to read api keys from $HOME/.cdsapirc if they dont exist otherwise
