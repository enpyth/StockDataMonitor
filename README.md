# Quant v1

Stock data platform MVP for collecting company metadata, daily OHLCV, and latest quote snapshots from Yahoo Finance through `yfinance`, then storing the data in hosted Supabase.

## Stack

- Bun workspaces and Turborepo
- TanStack Start web app in `apps/web`
- FastAPI Python API and ingestion runtime in `apps/api`
- Supabase Auth and Postgres
- OpenAPI-generated TypeScript client

## Setup

1. Copy `apps/api/.env.example` to `apps/api/.env`, copy `apps/web/.env.example` to `apps/web/.env`, and fill in Supabase values.
2. Install JavaScript dependencies:

   ```sh
   bun install
   ```

3. Install Python dependencies:

   ```sh
   cd apps/api
   python3.11 -m venv .venv
   . .venv/bin/activate
   pip install -e ".[dev]"
   ```

   `apps/api/requirements.txt` is also maintained for Azure App Service deployment, because Azure's Python build automation prioritizes `requirements.txt` in the deployed app root.

4. Apply `supabase/migrations/0001_stock_data.sql` to your hosted Supabase database.
5. Generate the frontend API client:

   ```sh
   bun run generate:api
   ```

6. Run the API and web app:

   ```sh
   bun run api:dev
   bun --filter web dev
   ```

## Ingestion

The API stock universe is defined in `apps/api/config/stocks.json`. Run the daily collector manually with:

```sh
bun run api:ingest
```

The same collector is available through the protected `POST /api/ingestions/run` endpoint.
