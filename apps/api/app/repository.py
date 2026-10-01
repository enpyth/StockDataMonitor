from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import uuid4

from supabase import Client, create_client

from .config import Settings
from .models import ExchangeConfig, IngestionRun, OhlcvDaily, QuoteSnapshot, Security


class StockRepository(Protocol):
    def list_securities(self) -> list[Security]: ...
    def get_security(self, symbol: str) -> Security | None: ...
    def list_ohlcv(self, symbol: str, start: str | None, end: str | None, limit: int) -> list[OhlcvDaily]: ...
    def list_latest_quotes(self) -> list[QuoteSnapshot]: ...
    def list_ingestion_runs(self, limit: int) -> list[IngestionRun]: ...
    def create_ingestion_run(self, symbols_total: int) -> str: ...
    def finish_ingestion_run(self, run_id: str, status: str, succeeded: int, failed: int, errors: list[dict[str, Any]]) -> None: ...
    def upsert_exchange(self, exchange: ExchangeConfig) -> str: ...
    def upsert_security(self, exchange_id: str, profile: dict[str, Any]) -> str: ...
    def upsert_ohlcv(self, rows: list[dict[str, Any]]) -> None: ...
    def insert_quote(self, quote: dict[str, Any]) -> None: ...


def _require_supabase(settings: Settings) -> tuple[str, str]:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase URL and service role key are required")
    return str(settings.supabase_url), settings.supabase_service_role_key


def get_supabase_client(settings: Settings) -> Client:
    url, key = _require_supabase(settings)
    return create_client(url, key)


class SupabaseStockRepository:
    def __init__(self, client: Client):
        self.client = client

    def list_securities(self) -> list[Security]:
        response = (
            self.client.table("securities")
            .select("id,symbol,yahoo_symbol,name,sector,industry,currency,active,exchanges(code,name)")
            .eq("active", True)
            .order("symbol")
            .execute()
        )
        return [_security_from_row(row) for row in response.data or []]

    def get_security(self, symbol: str) -> Security | None:
        response = (
            self.client.table("securities")
            .select("id,symbol,yahoo_symbol,name,sector,industry,currency,active,exchanges(code,name)")
            .eq("yahoo_symbol", symbol)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        return _security_from_row(rows[0]) if rows else None

    def list_ohlcv(self, symbol: str, start: str | None, end: str | None, limit: int) -> list[OhlcvDaily]:
        security = self.get_security(symbol)
        if not security or not security.id:
            return []
        query = (
            self.client.table("ohlcv_daily")
            .select("date,open,high,low,close,adj_close,volume")
            .eq("security_id", security.id)
            .order("date", desc=True)
            .limit(limit)
        )
        if start:
            query = query.gte("date", start)
        if end:
            query = query.lte("date", end)
        response = query.execute()
        return [OhlcvDaily.model_validate(row) for row in response.data or []]

    def list_latest_quotes(self) -> list[QuoteSnapshot]:
        securities = self.list_securities()
        quotes: list[QuoteSnapshot] = []
        for security in securities:
            if not security.id:
                continue
            response = (
                self.client.table("quote_snapshots")
                .select("price,previous_close,currency,market_state,collected_at")
                .eq("security_id", security.id)
                .order("collected_at", desc=True)
                .limit(1)
                .execute()
            )
            rows = response.data or []
            if rows:
                quotes.append(QuoteSnapshot(symbol=security.yahoo_symbol, **rows[0]))
        return quotes

    def list_ingestion_runs(self, limit: int) -> list[IngestionRun]:
        response = (
            self.client.table("ingestion_runs")
            .select("*")
            .order("started_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [IngestionRun.model_validate(row) for row in response.data or []]

    def create_ingestion_run(self, symbols_total: int) -> str:
        response = (
            self.client.table("ingestion_runs")
            .insert({"status": "running", "symbols_total": symbols_total})
            .execute()
        )
        rows = response.data or []
        if not rows:
            raise RuntimeError("Failed to create ingestion run")
        return rows[0]["id"]

    def finish_ingestion_run(self, run_id: str, status: str, succeeded: int, failed: int, errors: list[dict[str, Any]]) -> None:
        payload = _to_jsonable(
            {
                "status": status,
                "finished_at": datetime.now(UTC),
                "symbols_succeeded": succeeded,
                "symbols_failed": failed,
                "errors": errors,
            }
        )
        (
            self.client.table("ingestion_runs")
            .update(payload)
            .eq("id", run_id)
            .execute()
        )

    def upsert_exchange(self, exchange: ExchangeConfig) -> str:
        response = (
            self.client.table("exchanges")
            .upsert(
                {
                    "code": exchange.code,
                    "name": exchange.name,
                    "timezone": exchange.timezone,
                    "currency": exchange.currency,
                },
                on_conflict="code",
            )
            .execute()
        )
        rows = response.data or []
        if rows:
            return rows[0]["id"]
        lookup = self.client.table("exchanges").select("id").eq("code", exchange.code).limit(1).execute()
        return lookup.data[0]["id"]

    def upsert_security(self, exchange_id: str, profile: dict[str, Any]) -> str:
        payload = {
            "exchange_id": exchange_id,
            "symbol": profile["symbol"],
            "yahoo_symbol": profile["yahoo_symbol"],
            "name": profile["name"],
            "sector": profile.get("sector"),
            "industry": profile.get("industry"),
            "currency": profile["currency"],
            "active": profile["active"],
        }
        response = self.client.table("securities").upsert(payload, on_conflict="yahoo_symbol").execute()
        rows = response.data or []
        if rows:
            return rows[0]["id"]
        lookup = (
            self.client.table("securities")
            .select("id")
            .eq("yahoo_symbol", profile["yahoo_symbol"])
            .limit(1)
            .execute()
        )
        return lookup.data[0]["id"]

    def upsert_ohlcv(self, rows: list[dict[str, Any]]) -> None:
        if rows:
            self.client.table("ohlcv_daily").upsert(
                _to_jsonable(rows),
                on_conflict="security_id,date",
            ).execute()

    def insert_quote(self, quote: dict[str, Any]) -> None:
        self.client.table("quote_snapshots").insert(_quote_insert_payload(quote)).execute()


class MemoryStockRepository:
    def __init__(self):
        self.exchanges: dict[str, str] = {}
        self.securities: dict[str, dict[str, Any]] = {}
        self.ohlcv: list[dict[str, Any]] = []
        self.quotes: list[dict[str, Any]] = []
        self.runs: dict[str, dict[str, Any]] = {}

    def list_securities(self) -> list[Security]:
        return [_security_from_row(row) for row in self.securities.values()]

    def get_security(self, symbol: str) -> Security | None:
        row = self.securities.get(symbol)
        return _security_from_row(row) if row else None

    def list_ohlcv(self, symbol: str, start: str | None, end: str | None, limit: int) -> list[OhlcvDaily]:
        security = self.get_security(symbol)
        if not security or not security.id:
            return []
        rows = [row for row in self.ohlcv if row["security_id"] == security.id]
        if start:
            rows = [row for row in rows if row["date"] >= start]
        if end:
            rows = [row for row in rows if row["date"] <= end]
        rows = sorted(rows, key=lambda row: row["date"], reverse=True)[:limit]
        return [OhlcvDaily.model_validate(row) for row in rows]

    def list_latest_quotes(self) -> list[QuoteSnapshot]:
        latest: dict[str, dict[str, Any]] = {}
        by_id = {row["id"]: row for row in self.securities.values()}
        for quote in self.quotes:
            security = by_id.get(quote["security_id"])
            if security:
                latest[security["yahoo_symbol"]] = {**quote, "symbol": security["yahoo_symbol"]}
        return [QuoteSnapshot.model_validate(row) for row in latest.values()]

    def list_ingestion_runs(self, limit: int) -> list[IngestionRun]:
        rows = sorted(self.runs.values(), key=lambda row: row["started_at"], reverse=True)[:limit]
        return [IngestionRun.model_validate(row) for row in rows]

    def create_ingestion_run(self, symbols_total: int) -> str:
        run_id = str(uuid4())
        self.runs[run_id] = {
            "id": run_id,
            "status": "running",
            "started_at": datetime.now(UTC),
            "finished_at": None,
            "symbols_total": symbols_total,
            "symbols_succeeded": 0,
            "symbols_failed": 0,
            "errors": [],
        }
        return run_id

    def finish_ingestion_run(self, run_id: str, status: str, succeeded: int, failed: int, errors: list[dict[str, Any]]) -> None:
        self.runs[run_id].update(
            {
                "status": status,
                "finished_at": datetime.now(UTC),
                "symbols_succeeded": succeeded,
                "symbols_failed": failed,
                "errors": errors,
            }
        )

    def upsert_exchange(self, exchange: ExchangeConfig) -> str:
        exchange_id = self.exchanges.setdefault(exchange.code, str(uuid4()))
        return exchange_id

    def upsert_security(self, exchange_id: str, profile: dict[str, Any]) -> str:
        security_id = self.securities.get(profile["yahoo_symbol"], {}).get("id", str(uuid4()))
        self.securities[profile["yahoo_symbol"]] = {
            "id": security_id,
            "exchange_id": exchange_id,
            "symbol": profile["symbol"],
            "yahoo_symbol": profile["yahoo_symbol"],
            "name": profile["name"],
            "sector": profile.get("sector"),
            "industry": profile.get("industry"),
            "currency": profile["currency"],
            "active": profile["active"],
            "exchanges": {"code": profile["exchange_code"], "name": profile["exchange_code"]},
        }
        return security_id

    def upsert_ohlcv(self, rows: list[dict[str, Any]]) -> None:
        existing = {(row["security_id"], row["date"]): row for row in self.ohlcv}
        for row in rows:
            existing[(row["security_id"], row["date"])] = row
        self.ohlcv = list(existing.values())

    def insert_quote(self, quote: dict[str, Any]) -> None:
        self.quotes.append({**quote, "collected_at": datetime.now(UTC)})


def _security_from_row(row: dict[str, Any]) -> Security:
    exchange = row.get("exchanges") or {}
    return Security(
        id=row.get("id"),
        symbol=row["symbol"],
        yahoo_symbol=row["yahoo_symbol"],
        exchange_code=exchange.get("code", ""),
        exchange_name=exchange.get("name", ""),
        name=row["name"],
        sector=row.get("sector"),
        industry=row.get("industry"),
        currency=row["currency"],
        active=row.get("active", True),
    )


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def _quote_insert_payload(quote: dict[str, Any]) -> dict[str, Any]:
    payload = {key: value for key, value in quote.items() if key != "symbol"}
    return _to_jsonable(payload)
