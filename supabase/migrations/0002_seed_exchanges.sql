insert into public.exchanges (code, name, timezone, currency)
values
  ('NASDAQ', 'Nasdaq Stock Market', 'America/New_York', 'USD'),
  ('NYSE', 'New York Stock Exchange', 'America/New_York', 'USD'),
  ('TSE', 'Tokyo Stock Exchange', 'Asia/Tokyo', 'JPY'),
  ('ASX', 'Australian Securities Exchange', 'Australia/Sydney', 'AUD')
on conflict (code) do update
set
  name = excluded.name,
  timezone = excluded.timezone,
  currency = excluded.currency,
  updated_at = now();
