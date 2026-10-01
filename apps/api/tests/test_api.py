from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.auth import require_user
from app.dependencies import get_repository
from app.main import app
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
    repository.insert_quote(
        {
            "security_id": security_id,
            "price": 2,
            "previous_close": 1,
            "currency": "USD",
            "market_state": "REGULAR",
            "collected_at": datetime.now(UTC),
        }
    )

    app.dependency_overrides[require_user] = lambda: {"sub": "user-id"}
    app.dependency_overrides[get_repository] = lambda: repository
    client = TestClient(app)

    try:
        assert client.get("/api/stocks").status_code == 200
        assert client.get("/api/stocks/AAPL").json()["name"] == "Apple Inc."
        assert client.get("/api/stocks/AAPL/ohlcv").json()[0]["volume"] == 100
        assert client.get("/api/stocks/AAPL/ohlcv/today?trading_date=2026-09-17").json()[0]["date"] == "2026-09-17"
        assert client.get("/api/quotes/latest").json()[0]["symbol"] == "AAPL"
    finally:
        app.dependency_overrides.clear()
