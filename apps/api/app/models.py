from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class ExchangeConfig(BaseModel):
    code: str
    name: str
    timezone: str
    currency: str
    symbols: list[str]


class StockUniverse(BaseModel):
    exchanges: list[ExchangeConfig]


class HealthResponse(BaseModel):
    status: str
    supabase_configured: bool


class Security(BaseModel):
    id: str | None = None
    symbol: str
    yahoo_symbol: str
    exchange_code: str
    exchange_name: str
    name: str
    sector: str | None = None
    industry: str | None = None
    currency: str
    active: bool = True


class OhlcvDaily(BaseModel):
    date: date
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal | None = None
    adj_close: Decimal | None = None
    volume: int | None = None


class QuoteSnapshot(BaseModel):
    symbol: str
    price: Decimal | None = None
    previous_close: Decimal | None = None
    currency: str
    market_state: str | None = None
    collected_at: datetime


class IngestionRun(BaseModel):
    id: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    symbols_total: int
    symbols_succeeded: int
    symbols_failed: int
    errors: list[dict[str, Any]]


class IngestionRunResult(BaseModel):
    run_id: str
    status: str
    symbols_total: int
    symbols_succeeded: int
    symbols_failed: int
    errors: list[dict[str, Any]]
