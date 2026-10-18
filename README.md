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

4. Apply `supabase/scheme.sql`, then `supabase/seed.sql` to your hosted Supabase database.
5. Generate the frontend API client:

   ```sh
   cd apps/web && ../api/.venv/bin/python -c 'import json; from app.main import app; open("openapi.json", "w").write(json.dumps(app.openapi()))' && ./node_modules/.bin/openapi-ts
   ```

6. Run the API and web app:

   ```sh
   cd apps/api && .venv/bin/uvicorn app.main:app --reload
   cd apps/web && bun run dev
   ```

## Ingestion

Create `apps/api/config/users/<supabase-user-id>.json` for each user who should see stocks. Use `apps/api/config/stocks.example.json` as a template; the ID is the user's UUID from Supabase Auth. Users without a file see no stocks, quotes, history, or ingestion runs. The old shared `stocks.json` is no longer used. Run one exchange at a time for the union of configured users' symbols with:

```sh
cd apps/api && .venv/bin/python -m app.ingestion --exchange ASX
```

The web dashboard lets users select one of their configured exchanges before ingestion. The protected `POST /api/ingestions/run?exchange=ASX` endpoint collects only the signed-in user's symbols on that exchange, and `GET /api/ingestions/exchanges` lists their choices. Each execution creates a separate exchange-tagged ingestion run. Apply the updated `supabase/scheme.sql` before using this endpoint.

### GitHub Actions scheduling

Each exchange has its own schedule in `.github/workflows/ingest-asx.yml`, `ingest-tse.yml`, `ingest-nasdaq.yml`, or `ingest-nyse.yml`. Edit only that file's `cron` when changing its run time; the shared ingestion logic is in `ingest-one-exchange.yml`. The configured times are ASX 16:09 Sydney time, TSE 15:24 Tokyo time, NASDAQ 15:35 and NYSE 15:59 New York time on weekdays. GitHub Actions uses the exchange's IANA timezone, including daylight-saving changes. Push these workflows and user stock config files to the default branch, then add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` as repository Actions secrets under **Settings → Secrets and variables → Actions**. Use **Actions → Ingest ASX/TSE/NASDAQ/NYSE → Run workflow** to test one exchange manually.

Scheduled runs execute the Python collector directly; they do not call the user-authenticated HTTP endpoint. They collect the union of users' configured symbols for each exchange. GitHub schedules may be delayed or missed, and weekdays include exchange holidays. The shared workflow rejects a scheduled run that reaches ingestion after the `pre_auction_deadline` in its exchange file. With a schedule one minute before the auction, runner startup and dependency installation may cause most runs to miss that deadline. If you move a schedule past that deadline, update the deadline only if the exchange's auction timing actually changed. Since data is collected before the closing auction, that day's OHLCV and quote are provisional. Scheduled runs currently have no user ID, so their records are not shown in the per-user web run history; inspect the Actions logs or `ingestion_runs` table instead.
