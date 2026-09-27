# Launch Plan: API to Azure and Web to Vercel / 发布计划：API 部署到 Azure，Web 部署到 Vercel

## 1. Deployment Architecture / 部署架构

### English
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

### 中文
- 将 `apps/api` 部署到 Azure App Service for Linux，作为 FastAPI 运行环境。
- 将 `apps/web` 部署到 Vercel，作为 TanStack Start 前端应用。
- Supabase 继续作为外部托管的 Auth 和 Postgres。
- Vercel 前端通过 `VITE_API_BASE_URL` 调用 Azure API。
- Azure API 使用 service-role 凭证调用 Supabase。

官方参考：
- [Azure App Service Python configuration](https://learn.microsoft.com/en-us/azure/app-service/configure-language-python)
- [Azure App Service app settings](https://learn.microsoft.com/en-us/azure/app-service/configure-common)
- [Azure ZIP deploy](https://learn.microsoft.com/en-us/azure/app-service/deploy-zip)
- [Vercel environment variables](https://vercel.com/docs/environment-variables)
- [Vercel deploy from CLI](https://vercel.com/docs/projects/deploy-from-cli)

## 2. Pre-Launch Checklist / 发布前检查

### English
- Supabase project is created.
- SQL migrations are applied in order:
  - `supabase/migrations/0001_stock_data.sql`
  - `supabase/migrations/0002_seed_exchanges.sql`
- Supabase Google OAuth and email magic links are configured.
- Local checks pass:

```sh
bun run api:lint
bun run api:test
bun run test
bun run build
bun run api:ingest
```

### 中文
- Supabase project 已创建。
- SQL migrations 已按顺序执行：
  - `supabase/migrations/0001_stock_data.sql`
  - `supabase/migrations/0002_seed_exchanges.sql`
- Supabase Google OAuth 和邮箱 magic link 已配置。
- 本地检查通过：

```sh
bun run api:lint
bun run api:test
bun run test
bun run build
bun run api:ingest
```

## 3. Deploy API to Azure App Service / 将 API 部署到 Azure App Service

### English
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

### 中文
本项目应该把 `apps/api` 目录作为 Azure 应用根目录部署。Azure App Service 的 Python build automation 需要在部署根目录找到 `pyproject.toml`、`requirements.txt` 等依赖元数据。

安装并登录：

```sh
az login
az account set --subscription "<subscription-id-or-name>"
```

创建资源组和 App Service 资源：

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

设置 Azure app settings：

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

为 ZIP deploy 启用 build automation：

```sh
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_NAME" \
  --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true
```

设置 FastAPI 启动命令：

```sh
az webapp config set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_NAME" \
  --startup-file "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

打包并部署 API：

```sh
cd apps/api
zip -r api.zip app config pyproject.toml requirements.txt

az webapp deploy \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_NAME" \
  --src-path api.zip \
  --type zip
```

验证：

```sh
curl "https://$APP_NAME.azurewebsites.net/health"
```

期望返回：

```json
{
  "status": "ok",
  "supabase_configured": true
}
```

部署后执行采集。可以使用 Azure SSH console 或 App Service 容器中的一次性命令：

```sh
python -m app.ingestion
```

## 4. Deploy Web to Vercel / 将 Web 部署到 Vercel

### English
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

### 中文
推荐 Vercel 项目设置：

```text
Root Directory: apps/web
Framework Preset: Vite
Install Command: bun install
Build Command: bun run build
Output Directory: dist/client
```

为 Production 和 Preview 添加 Vercel 环境变量：

```text
VITE_API_BASE_URL=https://<azure-api-app-name>.azurewebsites.net
VITE_SUPABASE_URL=<supabase-url>
VITE_SUPABASE_ANON_KEY=<supabase-anon-key>
VITE_ALLOWED_USER_EMAILS=alice@example.com,bob@example.com
```

Dashboard 流程：
1. 将 Git 仓库导入 Vercel。
2. 设置 Root Directory 为 `apps/web`。
3. 添加上面的环境变量。
4. 部署。
5. 复制生产环境 Vercel URL。
6. 更新 Azure `CORS_ORIGINS`，加入 Vercel URL。
7. 如有需要，重新部署或重启 Azure API。

CLI 流程：

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

第一次获得 Vercel 生产 URL 后，更新 Azure CORS：

```sh
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_NAME" \
  --settings CORS_ORIGINS="https://<your-vercel-domain>"
```

## 5. Post-Launch Verification / 发布后验证

### English
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

### 中文
API：

```sh
curl https://<azure-api-app-name>.azurewebsites.net/health
```

前端：
- 打开 Vercel 生产 URL。
- 使用 Supabase Auth 登录。
- 确认仪表盘可以加载股票和价格快照。
- 从 UI 或 API 触发采集。
- 确认 `ingestion_runs` 中出现新的 completed 记录。

## 6. Rollback / 回滚

### English
- **Vercel**: use the Vercel dashboard to promote a previous deployment.
- **Azure API**: redeploy the previous ZIP package or use App Service deployment slots if configured.
- **Database**: avoid destructive migrations. Back up Supabase before schema changes.
- **Config rollback**: revert `apps/api/config/stocks.json`, regenerate API client only if API shape changed, redeploy, then rerun ingestion.

### 中文
- **Vercel**：在 Vercel dashboard 中将上一个 deployment 提升为生产版本。
- **Azure API**：重新部署上一个 ZIP 包；如果配置了 App Service deployment slots，可以通过 slot 回滚。
- **数据库**：避免破坏性 migration。schema 变更前先备份 Supabase。
- **配置回滚**：回滚 `apps/api/config/stocks.json`；只有 API 结构变化时才需要重新生成 API client；重新部署后再次执行采集。
