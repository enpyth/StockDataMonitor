import json
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from .models import ExchangeConfig, StockUniverse

API_ROOT = Path(__file__).resolve().parents[1]
USER_STOCK_CONFIG_DIR = API_ROOT / "config" / "users"


def load_stock_universe(config_path: str | Path) -> StockUniverse:
    path = Path(config_path)
    try:
        return StockUniverse.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Stock config not found: {path}") from exc
    except (json.JSONDecodeError, ValidationError) as exc:
        raise RuntimeError(f"Invalid stock config: {path}") from exc


def load_user_stock_universe(user_id: str, config_dir: Path = USER_STOCK_CONFIG_DIR) -> StockUniverse:
    # Supabase auth IDs are UUIDs. Parsing also keeps untrusted IDs out of paths.
    try:
        normalized_id = str(UUID(user_id))
    except (TypeError, ValueError, AttributeError):
        return StockUniverse(exchanges=[])
    path = config_dir / f"{normalized_id}.json"
    if not path.is_file():
        return StockUniverse(exchanges=[])
    return load_stock_universe(path)


def iter_all_user_symbols(config_dir: Path = USER_STOCK_CONFIG_DIR) -> list[tuple[ExchangeConfig, str]]:
    symbols: dict[str, tuple[ExchangeConfig, str]] = {}
    for path in sorted(config_dir.glob("*.json")):
        try:
            UUID(path.stem)
        except ValueError:
            continue
        for exchange, symbol in iter_configured_symbols(load_stock_universe(path)):
            symbols.setdefault(symbol, (exchange, symbol))
    return list(symbols.values())


def iter_configured_symbols(universe: StockUniverse) -> list[tuple[ExchangeConfig, str]]:
    return [(exchange, symbol) for exchange in universe.exchanges for symbol in exchange.symbols]


def configured_symbol_set(universe: StockUniverse) -> set[str]:
    return {symbol for _, symbol in iter_configured_symbols(universe)}


def configured_exchange_codes(universe: StockUniverse) -> list[str]:
    return list(dict.fromkeys(exchange.code for exchange in universe.exchanges if exchange.symbols))
