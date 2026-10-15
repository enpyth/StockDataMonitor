from datetime import UTC, datetime
from importlib import import_module

import pandas as pd
from fastapi import Depends
from fastapi.testclient import TestClient

from app.auth import require_user
from app.dependencies import get_repository
from app.main import app, get_user_symbols
from app.models import ExchangeConfig, StockUniverse
from app.repository import MemoryStockRepository


def test_protected_route_rejects_missing_token():
    client = TestClient(app)

    response = client.get("/api/stocks")

    assert response.status_code == 401


def test_root_exposes_api_documentation_links():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["swagger"] == "/docs"
    assert response.json()["openapi"] == "/openapi.json"


def test_stock_routes_with_overridden_auth_and_repository():
    repository = MemoryStockRepository()
    exchange_id = repository.upsert_exchange(
        type("Exchange", (), {"code": "NASDAQ", "name": "Nasdaq", "timezone": "America/New_York", "currency": "USD"})()
    )
    security_id = repository.upsert_security(
        exchange_id,
        {
            "symbol": "AAPL",
            "yahoo_symbol": "AAPL",
            "exchange_code": "NASDAQ",
            "name": "Apple Inc.",
            "currency": "USD",
            "active": True,
        },
    )
    repository.upsert_ohlcv(
        [
            {
                "security_id": security_id,
                "date": "2026-09-17",
                "open": 1,
                "high": 2,
                "low": 1,
                "close": 2,
                "adj_close": 2,
                "volume": 100,
            }
        ]
    )
    repository.upsert_quotes(
        [
            {
                "security_id": security_id,
                "date": "2026-09-17",
                "price": 2,
                "currency": "USD",
                "market_state": "REGULAR",
                "collected_at": datetime.now(UTC),
            }
        ]
    )

    app.dependency_overrides[require_user] = lambda: {"sub": "user-id"}
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_user_symbols] = lambda: {"AAPL"}
    client = TestClient(app)

    try:
        assert client.get("/api/stocks").status_code == 200
        assert client.get("/api/stocks/AAPL").json()["name"] == "Apple Inc."
        assert client.get("/api/stocks/AAPL/ohlcv").json()[0]["volume"] == 100
        assert client.get("/api/stocks/AAPL/ohlcv/today?trading_date=2026-09-17").json()[0]["date"] == "2026-09-17"
        assert client.get("/api/quotes/latest").json()[0]["symbol"] == "AAPL"
        assert client.get("/api/stocks/AAPL/prices").json()[0]["date"] == "2026-09-17"
    finally:
        app.dependency_overrides.clear()


def test_users_only_see_their_configured_stocks_and_runs():
    repository = MemoryStockRepository()
    exchange_id = repository.upsert_exchange(
        type("Exchange", (), {"code": "NASDAQ", "name": "Nasdaq", "timezone": "America/New_York", "currency": "USD"})()
    )
    for symbol in ("AAPL", "MSFT"):
        security_id = repository.upsert_security(exchange_id, {
            "symbol": symbol, "yahoo_symbol": symbol, "exchange_code": "NASDAQ",
            "name": symbol, "currency": "USD", "active": True,
        })
        repository.upsert_ohlcv([{
            "security_id": security_id, "date": "2026-09-17", "open": 1, "high": 2,
            "low": 1, "close": 2, "adj_close": 2, "volume": 100,
        }])
        repository.upsert_quotes([{
            "security_id": security_id, "date": "2026-09-17", "price": 2,
            "currency": "USD", "collected_at": datetime.now(UTC),
        }])
    repository.create_ingestion_run(1, "alice")
    repository.create_ingestion_run(1, "bob")

    current_user = {"sub": "alice"}

    def user_symbols(user: dict = Depends(require_user)) -> set[str]:
        return {"AAPL"} if user["sub"] == "alice" else set()

    app.dependency_overrides[require_user] = lambda: current_user
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_user_symbols] = user_symbols
    client = TestClient(app)
    try:
        assert [stock["symbol"] for stock in client.get("/api/stocks").json()] == ["AAPL"]
        assert [quote["symbol"] for quote in client.get("/api/quotes/latest").json()] == ["AAPL"]
        assert len(client.get("/api/ingestions").json()) == 1
        for path in ("/api/stocks/MSFT", "/api/stocks/MSFT/ohlcv", "/api/stocks/MSFT/ohlcv/today", "/api/stocks/MSFT/prices"):
            assert client.get(path).status_code == 404

        current_user["sub"] = "bob"
        assert client.get("/api/stocks").json() == []
        assert client.get("/api/quotes/latest").json() == []
        assert client.get("/api/stocks/AAPL").status_code == 404
        assert client.get("/api/stocks/AAPL/ohlcv").status_code == 404
        assert client.get("/api/stocks/AAPL/prices").status_code == 404
        assert client.get("/api/ingestions").json() == []
        assert client.post("/api/ingestions/run").status_code == 403

        current_user["sub"] = "unconfigured"
        assert client.get("/api/ingestions").json() == []
    finally:
        app.dependency_overrides.clear()


def test_ingestion_exchange_route_uses_current_user_config(monkeypatch):
    universe = StockUniverse(exchanges=[
        ExchangeConfig(code="ASX", name="ASX", timezone="Australia/Sydney", currency="AUD", symbols=["BHP.AX"]),
    ])
    main_module = import_module("app.main")
    ingestion_module = import_module("app.ingestion")
    monkeypatch.setattr(main_module, "load_user_stock_universe", lambda _user_id: universe)
    monkeypatch.setattr(ingestion_module, "load_user_stock_universe", lambda _user_id: universe)

    fetched: list[str] = []

    class FakeMarketData:
        def fetch_symbol(self, symbol):
            fetched.append(symbol)
            return {"longName": symbol, "regularMarketPrice": 10}, {}, pd.DataFrame()

    monkeypatch.setattr(main_module, "YFinanceClient", FakeMarketData)
    repository = MemoryStockRepository()
    app.dependency_overrides[require_user] = lambda: {"sub": "user-id"}
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_user_symbols] = lambda: {"BHP.AX"}
    client = TestClient(app)
    try:
        assert client.get("/api/ingestions/exchanges").json() == ["ASX"]
        assert client.post("/api/ingestions/run").status_code == 400
        assert client.post("/api/ingestions/run?exchange=NASDAQ").status_code == 404
        assert not repository.runs
        response = client.post("/api/ingestions/run?exchange=ASX")
        assert response.status_code == 200
        assert response.json()["exchange_code"] == "ASX"
        assert fetched == ["BHP.AX"]
    finally:
        app.dependency_overrides.clear()
