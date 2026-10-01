import json
from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from .models import ExchangeConfig, StockUniverse

API_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STOCK_CONFIG_PATH = API_ROOT / "config" / "stocks.json"


@lru_cache
def load_stock_universe(config_path: str | Path = DEFAULT_STOCK_CONFIG_PATH) -> StockUniverse:
    path = Path(config_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return StockUniverse.model_validate(payload)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Stock config not found: {path}") from exc
    except (json.JSONDecodeError, ValidationError) as exc:
        raise RuntimeError(f"Invalid stock config: {path}") from exc


def iter_configured_symbols(universe: StockUniverse) -> list[tuple[ExchangeConfig, str]]:
    return [(exchange, symbol) for exchange in universe.exchanges for symbol in exchange.symbols]
