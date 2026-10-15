import argparse
from typing import Any

from .config import get_settings
from .models import IngestionRunResult
from .repository import StockRepository, SupabaseStockRepository, get_supabase_client
from .stock_config import iter_all_user_symbols, iter_configured_symbols, load_user_stock_universe
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

    def run_daily(self, exchange_code: str, user_id: str | None = None) -> IngestionRunResult:
        exchange_code = exchange_code.strip().upper()
        configured_symbols = (
            iter_configured_symbols(load_user_stock_universe(user_id))
            if user_id is not None
            else iter_all_user_symbols()
        )
        selected_symbols = [
            (exchange, symbol)
            for exchange, symbol in configured_symbols
            if exchange.code.upper() == exchange_code
        ]
        if not selected_symbols:
            raise ValueError(f"Exchange is not configured or has no symbols: {exchange_code}")
        run_id = self.repository.create_ingestion_run(len(selected_symbols), user_id, exchange_code)
        succeeded = 0
        errors: list[dict[str, Any]] = []

        for exchange, symbol in selected_symbols:
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
            exchange_code=exchange_code,
            status=status,
            symbols_total=len(selected_symbols),
            symbols_succeeded=succeeded,
            symbols_failed=failed,
            errors=errors,
        )


def run_ingestion(exchange_code: str) -> IngestionRunResult:
    settings = get_settings()
    repository = SupabaseStockRepository(get_supabase_client(settings))
    return StockIngestionService(repository, YFinanceClient()).run_daily(exchange_code)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest configured stocks for one exchange")
    parser.add_argument("--exchange", required=True, help="Exchange code, for example NASDAQ or ASX")
    args = parser.parse_args()
    result = run_ingestion(args.exchange)
    print(result.model_dump_json(indent=2))
