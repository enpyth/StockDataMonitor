import sys

import pandas as pd
import pytest

from app.ingestion import StockIngestionService, main
from app.models import ExchangeConfig, IngestionRunResult, StockUniverse
from app.repository import MemoryStockRepository


class FakeMarketData:
    def __init__(self):
        self.fetched: list[str] = []

    def fetch_symbol(self, symbol: str):
        self.fetched.append(symbol)
        return {"longName": symbol, "regularMarketPrice": 10}, {}, pd.DataFrame()


def test_ingestion_only_fetches_selected_exchange(monkeypatch):
    universe = StockUniverse(exchanges=[
        ExchangeConfig(code="NASDAQ", name="Nasdaq", timezone="America/New_York", currency="USD", symbols=["AAPL", "MSFT"]),
        ExchangeConfig(code="ASX", name="ASX", timezone="Australia/Sydney", currency="AUD", symbols=["BHP.AX"]),
    ])
    monkeypatch.setattr("app.ingestion.load_user_stock_universe", lambda _user_id: universe)
    repository = MemoryStockRepository()
    market_data = FakeMarketData()
    service = StockIngestionService(repository, market_data)

    result = service.run_daily("asx", "user-id")

    assert result.exchange_code == "ASX"
    assert result.symbols_total == 1
    assert result.symbols_succeeded == 1
    assert market_data.fetched == ["BHP.AX"]
    assert repository.list_ingestion_runs(10, "user-id")[0].exchange_code == "ASX"

    with pytest.raises(ValueError, match="Exchange is not configured"):
        service.run_daily("NYSE", "user-id")
    assert len(repository.runs) == 1


def test_cli_reports_partial_ingestion_as_failure(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ingestion.py", "--exchange", "ASX"])
    monkeypatch.setattr("app.ingestion.run_ingestion", lambda _exchange: IngestionRunResult(
        run_id="run-id", exchange_code="ASX", status="completed_with_errors",
        symbols_total=2, symbols_succeeded=1, symbols_failed=1, errors=[{"symbol": "BHP.AX"}],
    ))

    assert main() == 1
    assert '"symbols_failed": 1' in capsys.readouterr().out
