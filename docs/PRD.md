# Product Requirements Document

## 1. Product Summary

Quant v1 is a stock data collection and monitoring platform. It collects company profile data, daily OHLCV data, and latest quote snapshots for a configured stock universe using `yfinance`, stores the data in Supabase, and exposes it through a FastAPI API and TanStack Start web dashboard.

## 2. Goals

- Collect stock metadata, daily OHLCV, and latest quote snapshots for selected NASDAQ, NYSE, TSE, and ASX stocks.
- Keep the stock universe configurable without code changes.
- Store normalized market data in Supabase Postgres.
- Provide authenticated API and web access through Supabase Auth.
- Support manual ingestion in v1, with daily batch scheduling as the intended operating model.

## 3. Non-Goals

- No real-time streaming or high-frequency intraday trading feed.
- No trading, brokerage, order management, or portfolio execution.
- No paid market data provider integration in v1.
- No investment advice or recommendation engine.

## 4. Users and Use Cases

- **Admin/operator**: configures the stock universe, runs ingestion, checks ingestion health, and verifies stored data.
- **Analyst/user**: signs in, reviews latest quote snapshots, checks recent OHLCV history, and monitors supported exchanges.

## 5. Functional Requirements

- Stock universe is defined in `apps/api/config/stocks.json`.
- Default configured symbols:
  - NASDAQ: `AAPL`, `MSFT`, `NVDA`
  - NYSE: `JPM`, `JNJ`, `KO`
  - TSE: `7203.T`, `6758.T`, `8306.T`
  - ASX: `BHP.AX`, `CBA.AX`, `CSL.AX`
- API supports:
  - health check
  - list active securities
  - get one security
  - get OHLCV history
  - get latest quote snapshots
  - list ingestion runs
  - trigger ingestion
- Web app supports:
  - Supabase Google OAuth and email magic-link login
  - stock universe table
  - selected stock detail panel
  - OHLCV mini chart
  - recent ingestion status
  - manual ingestion trigger

## 6. Data Model

Supabase tables:
- `exchanges`: exchange code, name, timezone, and currency.
- `securities`: stock identity, Yahoo Finance symbol, company metadata, and active flag.
- `ohlcv_daily`: daily open, high, low, close, adjusted close, and volume.
- `quote_snapshots`: point-in-time quote snapshots.
- `ingestion_runs`: ingestion status, counts, timestamps, and symbol-level errors.

## 7. Security and Access

- Supabase Auth is the identity provider.
- Protected API routes require a Supabase bearer token.
- Supabase RLS allows authenticated users to read stock data.
- API server uses `SUPABASE_SERVICE_ROLE_KEY`; this key must never be exposed to the browser.
- Web app only uses `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, and `VITE_API_BASE_URL`.

## 8. Acceptance Criteria

- API lint passes:

```sh
cd apps/api
. .venv/bin/activate
ruff check .
```

- API tests pass:

```sh
cd apps/api
. .venv/bin/activate
pytest
```

- Web tests and build pass:

```sh
cd apps/web
bun run test
bun run build
```

- Ingestion completes with `symbols_succeeded = 12` and `symbols_failed = 0` after Supabase is configured:

```sh
cd apps/api
. .venv/bin/activate
python -m app.ingestion
```

- Web users can sign in and view stocks, quotes, OHLCV, and ingestion runs.
