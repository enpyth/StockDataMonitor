from typing import Any

from .config import get_settings
from .models import IngestionRunResult
from .repository import StockRepository, SupabaseStockRepository, get_supabase_client
from .stock_config import iter_configured_symbols, load_stock_universe
from .yfinance_adapter import (
    YFinanceClient,
    normalize_company_profile,
    normalize_ohlcv_rows,
    normalize_quote_snapshot,
)


class StockIngestionService:
    def __init__(self, repository: StockRepository, market_data: YFinanceClient):
        self.repository = repository
        self.market_data = market_data

    def run_daily(self) -> IngestionRunResult:
        universe = load_stock_universe()
        configured_symbols = iter_configured_symbols(universe)
        run_id = self.repository.create_ingestion_run(symbols_total=len(configured_symbols))
        succeeded = 0
        errors: list[dict[str, Any]] = []

        for exchange, symbol in configured_symbols:
            try:
                exchange_id = self.repository.upsert_exchange(exchange)
                info, fast_info, history = self.market_data.fetch_symbol(symbol)
                profile = normalize_company_profile(symbol, exchange.code, exchange.currency, info)
                security_id = self.repository.upsert_security(exchange_id, profile)
                self.repository.upsert_ohlcv(normalize_ohlcv_rows(security_id, history))
                self.repository.upsert_quotes(
                    [normalize_quote_snapshot(security_id, symbol, profile["currency"], info, fast_info)]
                )
                succeeded += 1
            except Exception as exc:  # noqa: BLE001 - ingestion must isolate per-symbol failures
                errors.append({"symbol": symbol, "exchange": exchange.code, "message": str(exc)})

        failed = len(errors)
        status = "completed" if failed == 0 else "completed_with_errors"
        self.repository.finish_ingestion_run(run_id, status, succeeded, failed, errors)
        return IngestionRunResult(
            run_id=run_id,
            status=status,
            symbols_total=len(configured_symbols),
            symbols_succeeded=succeeded,
            symbols_failed=failed,
            errors=errors,
        )


def run_ingestion() -> IngestionRunResult:
    settings = get_settings()
    repository = SupabaseStockRepository(get_supabase_client(settings))
    return StockIngestionService(repository, YFinanceClient()).run_daily()


if __name__ == "__main__":
    result = run_ingestion()
    print(result.model_dump_json(indent=2))
