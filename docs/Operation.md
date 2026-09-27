# Operation and Maintenance Manual / 运维手册

## 1. Runtime Components / 运行组件

### English
- **Web**: TanStack Start app in `apps/web`, deployed to Vercel.
- **API**: FastAPI service in `apps/api`, deployed to Azure App Service.
- **Database/Auth**: Hosted Supabase.
- **Ingestion**: Python `yfinance` ingestion command in `apps/api/app/ingestion.py`.
- **Config**: API stock universe in `apps/api/config/stocks.json`.

### 中文
- **前端**：`apps/web` 中的 TanStack Start 应用，部署到 Vercel。
- **API**：`apps/api` 中的 FastAPI 服务，部署到 Azure App Service。
- **数据库/认证**：Hosted Supabase。
- **数据采集**：`apps/api/app/ingestion.py` 中的 Python `yfinance` 采集命令。
- **配置**：`apps/api/config/stocks.json` 中的 API 股票池。

## 2. Required Environment Variables / 必需环境变量

### English
API environment variables:
- `APP_ENV`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ALLOWED_USER_EMAILS`
- `CORS_ORIGINS`

Web environment variables:
- `VITE_API_BASE_URL`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_ALLOWED_USER_EMAILS`

Do not put `SUPABASE_SERVICE_ROLE_KEY` in Vercel or any browser-exposed environment.
`ALLOWED_USER_EMAILS` and `VITE_ALLOWED_USER_EMAILS` should use the same comma-separated email list. The API value is the security boundary; the web value is only for user experience.

### 中文
API 环境变量：
- `APP_ENV`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ALLOWED_USER_EMAILS`
- `CORS_ORIGINS`

前端环境变量：
- `VITE_API_BASE_URL`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_ALLOWED_USER_EMAILS`

不要把 `SUPABASE_SERVICE_ROLE_KEY` 放到 Vercel 或任何会暴露给浏览器的环境中。
`ALLOWED_USER_EMAILS` 和 `VITE_ALLOWED_USER_EMAILS` 应使用同一份逗号分隔邮箱列表。API 环境变量是真正的安全边界；前端环境变量只用于用户体验。

## 3. Local Runbook / 本地运行手册

### English
Install JavaScript dependencies:

```sh
bun install
```

Install Python dependencies:

```sh
cd apps/api
python3.11 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

Create app-local env files from the examples:

```sh
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env
```

Then run:

```sh
bun run generate:api
bun run api:dev
bun --filter web dev
```

Open:
- API health: `http://127.0.0.1:8000/health`
- API root links: `http://127.0.0.1:8000/`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Web: `http://localhost:3000`

### 中文
安装 JavaScript 依赖：

```sh
bun install
```

安装 Python 依赖：

```sh
cd apps/api
python3.11 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

从示例文件创建 app 本地环境变量文件：

```sh
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env
```

然后运行：

```sh
bun run generate:api
bun run api:dev
bun --filter web dev
```

打开：
- API 健康检查：`http://127.0.0.1:8000/health`
- API 入口链接：`http://127.0.0.1:8000/`
- Swagger UI：`http://127.0.0.1:8000/docs`
- ReDoc：`http://127.0.0.1:8000/redoc`
- 前端：`http://localhost:3000`

## 4. Ingestion Operations / 采集操作

### English
Run ingestion manually:

```sh
bun run api:ingest
```

Expected success:

```json
{
  "status": "completed",
  "symbols_total": 12,
  "symbols_succeeded": 12,
  "symbols_failed": 0,
  "errors": []
}
```

If `status` is `completed_with_errors`, inspect the `errors` array. Common causes:
- Missing or invalid Supabase environment variables.
- Supabase migrations not applied.
- Yahoo Finance/yfinance temporary fetch failure.
- Unknown or delisted symbol in `stocks.json`.
- Network connectivity issue from the API host.

### 中文
手动执行采集：

```sh
bun run api:ingest
```

期望成功结果：

```json
{
  "status": "completed",
  "symbols_total": 12,
  "symbols_succeeded": 12,
  "symbols_failed": 0,
  "errors": []
}
```

如果 `status` 是 `completed_with_errors`，检查 `errors` 数组。常见原因：
- Supabase 环境变量缺失或错误。
- Supabase migrations 未执行。
- Yahoo Finance/yfinance 临时拉取失败。
- `stocks.json` 中存在未知或退市 symbol。
- API 主机网络连接问题。

## 5. Changing the Stock Universe / 修改股票池

### English
Edit:

```text
apps/api/config/stocks.json
```

Rules:
- Use Yahoo Finance/yfinance symbols.
- Keep exchange code, timezone, and currency consistent.
- Run tests after changes:

```sh
bun run api:test
bun run test
```

Then run ingestion and verify `symbols_failed = 0`.

### 中文
修改文件：

```text
apps/api/config/stocks.json
```

规则：
- 使用 Yahoo Finance/yfinance symbol。
- 保持交易所代码、时区和币种一致。
- 修改后运行测试：

```sh
bun run api:test
bun run test
```

然后执行采集并确认 `symbols_failed = 0`。

## 6. Database Maintenance / 数据库维护

### English
Apply migrations in order:

```text
supabase/migrations/0001_stock_data.sql
supabase/migrations/0002_seed_exchanges.sql
```

To completely clean a local/dev/test Supabase environment before re-applying migrations, run:

```text
supabase/clean.sql
```

Warning: `clean.sql` drops the Quant v1 app tables and deletes collected data. Do not run it in production unless this is intentional.

Operational checks:
- `ingestion_runs` should show a recent completed run.
- `ohlcv_daily` should have rows for all active securities.
- `quote_snapshots` should have recent rows after each ingestion.
- If schema changes affect API responses, run `bun run generate:api` and commit regenerated client files.

Useful API endpoints:
- `GET /api/stocks/{symbol}/ohlcv`: historical OHLCV, with optional `start`, `end`, and `limit`.
- `GET /api/stocks/{symbol}/ohlcv/today`: current UTC date OHLCV by default; use `trading_date=YYYY-MM-DD` to request a specific date.

### 中文
按顺序执行 migrations：

```text
supabase/migrations/0001_stock_data.sql
supabase/migrations/0002_seed_exchanges.sql
```

如果需要在 local/dev/test Supabase 环境中完全清理后重新执行 migrations，运行：

```text
supabase/clean.sql
```

警告：`clean.sql` 会 drop Quant v1 应用表并删除已采集数据。除非明确需要，否则不要在生产环境执行。

运维检查：
- `ingestion_runs` 应该有最近成功的运行记录。
- `ohlcv_daily` 应该包含所有启用股票的数据。
- 每次采集后 `quote_snapshots` 应该有新的快照记录。
- 如果 schema 变化影响 API 返回结构，运行 `bun run generate:api` 并提交重新生成的前端客户端代码。

常用 API：
- `GET /api/stocks/{symbol}/ohlcv`：历史 OHLCV，可传 `start`、`end`、`limit`。
- `GET /api/stocks/{symbol}/ohlcv/today`：默认查询当前 UTC 日期的 OHLCV；也可以用 `trading_date=YYYY-MM-DD` 查询指定日期。

## 7. Validation Commands / 验证命令

### English
Run before deployment:

```sh
bun run api:lint
bun run api:test
bun run test
bun run build
```

### 中文
部署前运行：

```sh
bun run api:lint
bun run api:test
bun run test
bun run build
```

## 8. Incident Response / 故障处理

### English
- **API health fails**: check Azure App Service logs, startup command, Python version, and app settings.
- **401 from API**: verify Supabase JWT settings, browser session, and `Authorization: Bearer <token>`.
- **CORS error**: add the Vercel production URL to `CORS_ORIGINS` on Azure.
- **Ingestion fails for all symbols**: check Supabase service role key, migrations, and network access.
- **Ingestion fails for one symbol**: check symbol validity in Yahoo Finance and update `stocks.json` if needed.
- **Web cannot load data**: verify `VITE_API_BASE_URL` points to the Azure API URL and redeploy Vercel after changes.

### 中文
- **API 健康检查失败**：检查 Azure App Service 日志、启动命令、Python 版本和 app settings。
- **API 返回 401**：检查 Supabase JWT 配置、浏览器登录 session 和 `Authorization: Bearer <token>`。
- **CORS 错误**：把 Vercel 生产域名加入 Azure 的 `CORS_ORIGINS`。
- **所有 symbol 采集失败**：检查 Supabase service role key、migrations 和网络访问。
- **单个 symbol 采集失败**：检查 Yahoo Finance 中 symbol 是否有效，必要时更新 `stocks.json`。
- **前端无法加载数据**：确认 `VITE_API_BASE_URL` 指向 Azure API 地址，并在修改后重新部署 Vercel。
