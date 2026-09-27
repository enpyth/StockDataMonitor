-- WARNING:
-- This script deletes the Quant v1 application schema objects and all collected data.
-- Use it only for local/dev/test environment reset, or before re-applying migrations.
-- Do not run this in production unless you intentionally want to remove all app data.

begin;

drop table if exists public.quote_snapshots cascade;
drop table if exists public.ohlcv_daily cascade;
drop table if exists public.ingestion_runs cascade;
drop table if exists public.securities cascade;
drop table if exists public.exchanges cascade;

commit;
