-- Apply before seed.sql. Safe to run on a fresh database or after the old
-- numbered SQL files: existing tables are kept and the user access changes
-- are applied in place.
begin;

create extension if not exists pgcrypto;

create table if not exists public.exchanges (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  timezone text not null,
  currency text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.securities (
  id uuid primary key default gen_random_uuid(),
  exchange_id uuid not null references public.exchanges(id) on delete restrict,
  symbol text not null,
  yahoo_symbol text not null,
  name text not null,
  sector text,
  industry text,
  currency text not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (exchange_id, symbol),
  unique (yahoo_symbol)
);

create table if not exists public.ohlcv_daily (
  id uuid primary key default gen_random_uuid(),
  security_id uuid not null references public.securities(id) on delete cascade,
  date date not null,
  open numeric,
  high numeric,
  low numeric,
  close numeric,
  adj_close numeric,
  volume bigint,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (security_id, date)
);

create table if not exists public.quote_snapshots (
  id uuid primary key default gen_random_uuid(),
  security_id uuid not null references public.securities(id) on delete cascade,
  date date not null,
  price numeric,
  currency text not null,
  market_state text,
  collected_at timestamptz not null default now(),
  unique (security_id, date)
);

create table if not exists public.ingestion_runs (
  id uuid primary key default gen_random_uuid(),
  status text not null check (status in ('running', 'completed', 'failed', 'completed_with_errors')),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  symbols_total integer not null default 0,
  symbols_succeeded integer not null default 0,
  symbols_failed integer not null default 0,
  errors jsonb not null default '[]'::jsonb,
  user_id uuid references auth.users(id) on delete set null,
  exchange_code text
);

alter table public.ingestion_runs
  add column if not exists user_id uuid references auth.users(id) on delete set null;
alter table public.ingestion_runs
  add column if not exists exchange_code text;

create index if not exists ohlcv_daily_security_date_idx on public.ohlcv_daily (security_id, date desc);
create index if not exists quote_snapshots_security_date_idx on public.quote_snapshots (security_id, date desc);
create index if not exists ingestion_runs_started_idx on public.ingestion_runs (started_at desc);
create index if not exists ingestion_runs_user_started_idx on public.ingestion_runs (user_id, started_at desc);
create index if not exists ingestion_runs_user_exchange_started_idx on public.ingestion_runs (user_id, exchange_code, started_at desc);

alter table public.exchanges enable row level security;
alter table public.securities enable row level security;
alter table public.ohlcv_daily enable row level security;
alter table public.quote_snapshots enable row level security;
alter table public.ingestion_runs enable row level security;

-- Only the API's service role may read stock data. The API filters each
-- response using the signed-in user's server-side stock configuration.
drop policy if exists "Authenticated users can read exchanges" on public.exchanges;
drop policy if exists "Authenticated users can read securities" on public.securities;
drop policy if exists "Authenticated users can read ohlcv" on public.ohlcv_daily;
drop policy if exists "Authenticated users can read quote snapshots" on public.quote_snapshots;
drop policy if exists "Authenticated users can read ingestion runs" on public.ingestion_runs;

commit;
