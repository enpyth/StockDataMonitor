# Operation and Maintenance Manual

## 1. Runtime Components

- **Web**: TanStack Start app in `apps/web`, deployed to Vercel.
- **API**: FastAPI service in `apps/api`, deployed to Azure App Service.
- **Database/Auth**: Hosted Supabase.
- **Ingestion**: Python `yfinance` ingestion command in `apps/api/app/ingestion.py`.
- **Config**: API stock universe in `apps/api/config/stocks.json`.

## 2. Required Environment Variables

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

## 3. Local Runbook

Install JavaScript dependencies from the web app directory:

```sh
cd apps/web
bun install
```

Install Python dependencies from the API app directory:

```sh
cd apps/api
python3.11 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

Create app-local env files from the examples:

```sh
cd apps/api
cp .env.example .env

cd ../web
cp .env.example .env
```

Run the API from the API app directory:

```sh
cd apps/api
. .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run the web app from the web app directory in a separate terminal:

```sh
cd apps/web
bun run dev
```

Open:
- API health: `http://127.0.0.1:8000/health`
- API root links: `http://127.0.0.1:8000/`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Web: `http://localhost:3000`

## 4. Ingestion Operations

Run ingestion manually from the API app directory:

```sh
cd apps/api
. .venv/bin/activate
python -m app.ingestion
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

## 5. Changing the Stock Universe

Edit:

```text
apps/api/config/stocks.json
```

Rules:
- Use Yahoo Finance/yfinance symbols.
- Keep exchange code, timezone, and currency consistent.
- Run tests after changes:

```sh
cd apps/api
. .venv/bin/activate
pytest

cd ../web
bun run test
```

Then run ingestion and verify `symbols_failed = 0`.

## 6. Database Maintenance

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
- If schema changes affect API responses, export `apps/web/openapi.json`, regenerate the web client from `apps/web`, and commit regenerated client files.

OpenAPI/client regeneration:

```sh
# From the repository root; reads apps/api and writes apps/web/openapi.json.
python scripts/export_openapi.py

cd apps/web
bunx @hey-api/openapi-ts -c openapi-ts.config.ts
```

Useful API endpoints:
- `GET /api/stocks/{symbol}/ohlcv`: historical OHLCV, with optional `start`, `end`, and `limit`.
- `GET /api/stocks/{symbol}/ohlcv/today`: current UTC date OHLCV by default; use `trading_date=YYYY-MM-DD` to request a specific date.

## 7. Validation Commands

Run before deployment:

```sh
cd apps/api
. .venv/bin/activate
ruff check .
pytest

cd ../web
bun run test
bun run build
```

## 8. Incident Response

- **API health fails**: check Azure App Service logs, startup command, Python version, and app settings.
- **401 from API**: verify Supabase JWT settings, browser session, and `Authorization: Bearer <token>`.
- **CORS error**: add the Vercel production URL to `CORS_ORIGINS` on Azure.
- **Ingestion fails for all symbols**: check Supabase service role key, migrations, and network access.
- **Ingestion fails for one symbol**: check symbol validity in Yahoo Finance and update `stocks.json` if needed.
- **Web cannot load data**: verify `VITE_API_BASE_URL` points to the Azure API URL and redeploy Vercel after changes.
