import json
from datetime import UTC, datetime
from decimal import Decimal

from app.repository import _quote_insert_payload, _to_jsonable


def test_to_jsonable_converts_decimal_and_datetime_payloads():
    payload = {
        "price": Decimal("123.45"),
        "collected_at": datetime(2026, 9, 19, 10, 30, tzinfo=UTC),
        "rows": [{"open": Decimal("1.23"), "volume": 100}],
    }

    converted = _to_jsonable(payload)

    assert converted == {
        "price": 123.45,
        "collected_at": "2026-09-19T10:30:00+00:00",
        "rows": [{"open": 1.23, "volume": 100}],
    }
    json.dumps(converted)


def test_quote_insert_payload_removes_transient_symbol_and_serializes_decimal():
    payload = _quote_insert_payload(
        {
            "security_id": "security-id",
            "symbol": "AAPL",
            "price": Decimal("123.45"),
            "previous_close": Decimal("120.00"),
            "currency": "USD",
            "market_state": "REGULAR",
        }
    )

    assert payload == {
        "security_id": "security-id",
        "price": 123.45,
        "previous_close": 120.0,
        "currency": "USD",
        "market_state": "REGULAR",
    }
    json.dumps(payload)
