create extension if not exists pgcrypto;

create table public.exchanges (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  timezone text not null,
  currency text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.securities (
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

create table public.ohlcv_daily (
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

create table public.quote_snapshots (
  id uuid primary key default gen_random_uuid(),
  security_id uuid not null references public.securities(id) on delete cascade,
  date date not null,
  price numeric,
  currency text not null,
  market_state text,
  collected_at timestamptz not null default now(),
  unique (security_id, date)
);

create table public.ingestion_runs (
  id uuid primary key default gen_random_uuid(),
  status text not null check (status in ('running', 'completed', 'failed', 'completed_with_errors')),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  symbols_total integer not null default 0,
  symbols_succeeded integer not null default 0,
  symbols_failed integer not null default 0,
  errors jsonb not null default '[]'::jsonb
);

create index ohlcv_daily_security_date_idx on public.ohlcv_daily (security_id, date desc);
create index quote_snapshots_security_date_idx on public.quote_snapshots (security_id, date desc);
create index ingestion_runs_started_idx on public.ingestion_runs (started_at desc);

alter table public.exchanges enable row level security;
alter table public.securities enable row level security;
alter table public.ohlcv_daily enable row level security;
alter table public.quote_snapshots enable row level security;
alter table public.ingestion_runs enable row level security;

create policy "Authenticated users can read exchanges"
  on public.exchanges for select
  to authenticated
  using (true);

create policy "Authenticated users can read securities"
  on public.securities for select
  to authenticated
  using (true);

create policy "Authenticated users can read ohlcv"
  on public.ohlcv_daily for select
  to authenticated
  using (true);

create policy "Authenticated users can read quote snapshots"
  on public.quote_snapshots for select
  to authenticated
  using (true);

create policy "Authenticated users can read ingestion runs"
  on public.ingestion_runs for select
  to authenticated
  using (true);
