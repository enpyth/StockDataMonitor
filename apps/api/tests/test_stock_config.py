from app.stock_config import iter_configured_symbols, load_stock_universe


def test_load_stock_universe_has_three_symbols_per_exchange():
    universe = load_stock_universe()

    assert {exchange.code for exchange in universe.exchanges} == {"NASDAQ", "NYSE", "TSE", "ASX"}
    assert all(len(exchange.symbols) == 3 for exchange in universe.exchanges)
    assert len(iter_configured_symbols(universe)) == 12
