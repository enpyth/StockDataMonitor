import json
from uuid import uuid4

from app.stock_config import (
    iter_all_user_symbols,
    iter_configured_symbols,
    load_stock_universe,
    load_user_stock_universe,
)


def test_example_stock_universe_has_three_symbols_per_exchange():
    from app.stock_config import API_ROOT

    universe = load_stock_universe(API_ROOT / "config" / "stocks.example.json")

    assert {exchange.code for exchange in universe.exchanges} == {"NASDAQ", "NYSE", "TSE", "ASX"}
    assert all(len(exchange.symbols) == 3 for exchange in universe.exchanges)
    assert len(iter_configured_symbols(universe)) == 12


def test_user_config_is_individual_and_missing_user_has_no_stocks(tmp_path):
    first_id, second_id = str(uuid4()), str(uuid4())
    for user_id, symbol in [(first_id, "AAPL"), (second_id, "MSFT")]:
        (tmp_path / f"{user_id}.json").write_text(json.dumps({"exchanges": [{
            "code": "NASDAQ", "name": "Nasdaq", "timezone": "America/New_York",
            "currency": "USD", "symbols": [symbol],
        }]}))

    assert [symbol for _, symbol in iter_configured_symbols(load_user_stock_universe(first_id, tmp_path))] == ["AAPL"]
    assert [symbol for _, symbol in iter_configured_symbols(load_user_stock_universe(second_id, tmp_path))] == ["MSFT"]
    assert load_user_stock_universe(str(uuid4()), tmp_path).exchanges == []
    assert load_user_stock_universe("../stocks.example", tmp_path).exchanges == []
    assert {symbol for _, symbol in iter_all_user_symbols(tmp_path)} == {"AAPL", "MSFT"}
