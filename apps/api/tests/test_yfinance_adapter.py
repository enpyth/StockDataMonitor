import pandas as pd

from app.yfinance_adapter import (
    normalize_company_profile,
    normalize_ohlcv_rows,
    normalize_quote_snapshot,
)


def test_normalize_company_profile_uses_expected_fields():
    profile = normalize_company_profile(
        "AAPL",
        "NASDAQ",
        "USD",
        {"longName": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"},
    )

    assert profile["name"] == "Apple Inc."
    assert profile["currency"] == "USD"
    assert profile["exchange_code"] == "NASDAQ"


def test_normalize_ohlcv_rows_converts_dataframe_values():
    history = pd.DataFrame(
        [{"Open": 1.1, "High": 2.2, "Low": 1.0, "Close": 2.0, "Adj Close": 1.9, "Volume": 1000}],
        index=[pd.Timestamp("2026-09-17")],
    )

    rows = normalize_ohlcv_rows("security-id", history)

    assert rows == [
        {
            "security_id": "security-id",
            "date": "2026-09-17",
            "open": rows[0]["open"],
            "high": rows[0]["high"],
            "low": rows[0]["low"],
            "close": rows[0]["close"],
            "adj_close": rows[0]["adj_close"],
            "volume": 1000,
        }
    ]


def test_normalize_quote_snapshot_prefers_fast_info():
    quote = normalize_quote_snapshot(
        "security-id",
        "MSFT",
        "USD",
        {"regularMarketPrice": 10, "regularMarketPreviousClose": 9},
        {"last_price": 11, "previous_close": 10},
    )

    assert quote["price"] == 11
    assert quote["previous_close"] == 10
