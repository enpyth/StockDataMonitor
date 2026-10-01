from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd
import yfinance as yf


def decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_company_profile(symbol: str, exchange_code: str, default_currency: str, info: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "yahoo_symbol": symbol,
        "exchange_code": exchange_code,
        "name": info.get("longName") or info.get("shortName") or symbol,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "currency": info.get("currency") or info.get("financialCurrency") or default_currency,
        "active": True,
    }


def normalize_ohlcv_rows(security_id: str, history: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if history.empty:
        return rows

    for index, row in history.iterrows():
        trading_date: date = index.date() if hasattr(index, "date") else pd.Timestamp(index).date()
        rows.append(
            {
                "security_id": security_id,
                "date": trading_date.isoformat(),
                "open": decimal_or_none(row.get("Open")),
                "high": decimal_or_none(row.get("High")),
                "low": decimal_or_none(row.get("Low")),
                "close": decimal_or_none(row.get("Close")),
                "adj_close": decimal_or_none(row.get("Adj Close")),
                "volume": int_or_none(row.get("Volume")),
            }
        )
    return rows


def normalize_quote_snapshot(
    security_id: str,
    symbol: str,
    currency: str,
    info: dict[str, Any],
    fast_info: Any,
) -> dict[str, Any]:
    def fast_get(key: str) -> Any:
        try:
            return fast_info.get(key)
        except AttributeError:
            return getattr(fast_info, key, None)

    price = (
        fast_get("last_price")
        or fast_get("lastPrice")
        or info.get("regularMarketPrice")
        or info.get("currentPrice")
    )
    previous_close = (
        fast_get("previous_close")
        or fast_get("previousClose")
        or info.get("regularMarketPreviousClose")
        or info.get("previousClose")
    )
    return {
        "security_id": security_id,
        "symbol": symbol,
        "price": decimal_or_none(price),
        "previous_close": decimal_or_none(previous_close),
        "currency": info.get("currency") or currency,
        "market_state": info.get("marketState"),
    }


class YFinanceClient:
    def fetch_symbol(self, symbol: str) -> tuple[dict[str, Any], Any, pd.DataFrame]:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        fast_info = ticker.fast_info
        history = ticker.history(period="1y", interval="1d", auto_adjust=False)
        return info, fast_info, history
