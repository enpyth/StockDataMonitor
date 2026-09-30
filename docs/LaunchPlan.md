# Launch Plan: API to Azure and Web to Vercel

## 1. Deployment Architecture

- Deploy `apps/api` to Azure App Service for Linux as the FastAPI runtime.
- Deploy `apps/web` to Vercel as the TanStack Start web app.
- Keep Supabase hosted externally for Auth and Postgres.
- Vercel calls Azure API through `VITE_API_BASE_URL`.
- Azure API calls Supabase using service-role credentials.

Official references:
- [Azure App Service Python configuration](https://learn.microsoft.com/en-us/azure/app-service/configure-language-python)
- [Azure App Service app settings](https://learn.microsoft.com/en-us/azure/app-service/configure-common)
- [Azure ZIP deploy](https://learn.microsoft.com/en-us/azure/app-service/deploy-zip)
- [Vercel environment variables](https://vercel.com/docs/environment-variables)
- [Vercel deploy from CLI](https://vercel.com/docs/projects/deploy-from-cli)

## 2. Pre-Launch Checklist

- Supabase project is created.
- SQL migrations are applied in order:
  - `supabase/migrations/0001_stock_data.sql`
  - `supabase/migrations/0002_seed_exchanges.sql`
- Supabase Google OAuth and email magic links are configured.
- API checks pass from the API app directory:

```sh
cd apps/api
. .venv/bin/activate
ruff check .
pytest
python -m app.ingestion
```

- Web checks pass from the web app directory:

```sh
cd apps/web
bun run test
bun run build
```

## 3. Deploy API to Azure App Service

This project should deploy the `apps/api` directory as the Azure application root. Azure App Service Python build automation expects dependency metadata such as `pyproject.toml` or `requirements.txt` at the deployed project root.

Install and log in:

```sh
az login
az account set --subscription "<subscription-id-or-name>"
```

Create resource group and App Service resources:

```sh
RESOURCE_GROUP="quant-v1-rg"
LOCATION="australiaeast"
PLAN_NAME="quant-v1-api-plan"
APP_NAME="quant-v1-api"

az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION"

az appservice plan create \
  --name "$PLAN_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --is-linux \
  --sku B1

az webapp create \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --plan "$PLAN_NAME" \
  --runtime "PYTHON|3.11"
```

Set Azure app settings:

```sh
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_NAME" \
  --settings \
    APP_ENV="production" \
    SUPABASE_URL="<supabase-url>" \
    SUPABASE_ANON_KEY="<supabase-anon-key>" \
    SUPABASE_SERVICE_ROLE_KEY="<supabase-service-role-key>" \
    ALLOWED_USER_EMAILS="alice@example.com,bob@example.com" \
    CORS_ORIGINS="https://<your-vercel-domain>"
```

Enable build automation for ZIP deploy:

```sh
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_NAME" \
  --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

Set the FastAPI startup command:

```sh
az webapp config set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_NAME" \
  --startup-file "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

Package and deploy the API:

```sh
cd apps/api
zip -r api.zip app config pyproject.toml requirements.txt

az webapp deploy \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_NAME" \
  --src-path api.zip \
  --type zip
```

Verify:

```sh
curl "https://$APP_NAME.azurewebsites.net/health"
```

Expected:

```json
{
  "status": "ok",
  "supabase_configured": true
}
```

Run ingestion after deployment. Use Azure SSH console or a one-off command in the App Service container:

```sh
python -m app.ingestion
```

## 4. Deploy Web to Vercel

Recommended Vercel project settings:

```text
Root Directory: apps/web
Framework Preset: Vite
Install Command: bun install
Build Command: bun run build
Output Directory: dist/client
```

Add Vercel environment variables for Production and Preview:

```text
VITE_API_BASE_URL=https://<azure-api-app-name>.azurewebsites.net
VITE_SUPABASE_URL=<supabase-url>
VITE_SUPABASE_ANON_KEY=<supabase-anon-key>
VITE_ALLOWED_USER_EMAILS=alice@example.com,bob@example.com
```

Dashboard flow:
1. Import the Git repository into Vercel.
2. Set Root Directory to `apps/web`.
3. Add the environment variables above.
4. Deploy.
5. Copy the production Vercel URL.
6. Update Azure `CORS_ORIGINS` to include the Vercel URL.
7. Redeploy or restart the Azure API if needed.

CLI flow:

```sh
cd apps/web
npm i -g vercel
vercel login
vercel link
vercel env add VITE_API_BASE_URL production
vercel env add VITE_SUPABASE_URL production
vercel env add VITE_SUPABASE_ANON_KEY production
vercel env add VITE_ALLOWED_USER_EMAILS production
vercel deploy --prod
```

After the first Vercel production URL is known, update Azure CORS:

```sh
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_NAME" \
  --settings CORS_ORIGINS="https://<your-vercel-domain>"
```

## 5. Post-Launch Verification

API:

```sh
curl https://<azure-api-app-name>.azurewebsites.net/health
```

Web:
- Open the Vercel production URL.
- Sign in with Supabase Auth.
- Confirm the dashboard loads stocks and quotes.
- Trigger ingestion from the UI or API.
- Confirm `ingestion_runs` has a new completed row.

## 6. Rollback

- **Vercel**: use the Vercel dashboard to promote a previous deployment.
- **Azure API**: redeploy the previous ZIP package or use App Service deployment slots if configured.
- **Database**: avoid destructive migrations. Back up Supabase before schema changes.
- **Config rollback**: revert `apps/api/config/stocks.json`, regenerate API client only if API shape changed, redeploy, then rerun ingestion.
