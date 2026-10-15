from datetime import UTC, date, datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .auth import require_user
from .config import get_settings
from .dependencies import get_repository
from .ingestion import StockIngestionService
from .models import (
    HealthResponse,
    IngestionRun,
    IngestionRunResult,
    OhlcvDaily,
    QuoteSnapshot,
    Security,
)
from .repository import StockRepository
from .stock_config import configured_exchange_codes, configured_symbol_set, load_user_stock_universe
from .yfinance_adapter import YFinanceClient


def get_user_symbols(user: dict = Depends(require_user)) -> set[str]:
    return configured_symbol_set(load_user_stock_universe(user["sub"]))


def require_configured_symbol(symbol: str, symbols: set[str]) -> None:
    if symbol not in symbols:
        raise HTTPException(status_code=404, detail="Stock not found")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Quant Stock Data API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "name": "Quant Stock Data API",
            "health": "/health",
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
        }

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", supabase_configured=settings.has_supabase)

    @app.get("/api/stocks", response_model=list[Security])
    def list_stocks(
        repository: StockRepository = Depends(get_repository),
        symbols: set[str] = Depends(get_user_symbols),
    ) -> list[Security]:
        return [security for security in repository.list_securities() if security.yahoo_symbol in symbols]

    @app.get("/api/stocks/{symbol}", response_model=Security)
    def get_stock(
        symbol: str,
        repository: StockRepository = Depends(get_repository),
        symbols: set[str] = Depends(get_user_symbols),
    ) -> Security:
        require_configured_symbol(symbol, symbols)
        security = repository.get_security(symbol)
        if security is None:
            raise HTTPException(status_code=404, detail="Stock not found")
        return security

    @app.get("/api/stocks/{symbol}/ohlcv", response_model=list[OhlcvDaily])
    def get_ohlcv(
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        limit: int = Query(default=260, ge=1, le=1000),
        repository: StockRepository = Depends(get_repository),
        symbols: set[str] = Depends(get_user_symbols),
    ) -> list[OhlcvDaily]:
        require_configured_symbol(symbol, symbols)
        return repository.list_ohlcv(symbol, start, end, limit)

    @app.get("/api/stocks/{symbol}/ohlcv/today", response_model=list[OhlcvDaily])
    def get_today_ohlcv(
        symbol: str,
        trading_date: date | None = Query(
            default=None,
            description="Trading date to fetch. Defaults to the API server's current UTC date.",
        ),
        repository: StockRepository = Depends(get_repository),
        symbols: set[str] = Depends(get_user_symbols),
    ) -> list[OhlcvDaily]:
        require_configured_symbol(symbol, symbols)
        target_date = trading_date or datetime.now(UTC).date()
        date_value = target_date.isoformat()
        return repository.list_ohlcv(symbol, date_value, date_value, 1)

    @app.get("/api/quotes/latest", response_model=list[QuoteSnapshot])
    def latest_quotes(
        repository: StockRepository = Depends(get_repository),
        symbols: set[str] = Depends(get_user_symbols),
    ) -> list[QuoteSnapshot]:
        return [quote for quote in repository.list_latest_quotes() if quote.symbol in symbols]

    @app.get("/api/stocks/{symbol}/prices", response_model=list[QuoteSnapshot])
    def get_quote_prices(
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        limit: int = Query(default=260, ge=1, le=1000),
        repository: StockRepository = Depends(get_repository),
        symbols: set[str] = Depends(get_user_symbols),
    ) -> list[QuoteSnapshot]:
        require_configured_symbol(symbol, symbols)
        return repository.list_quote_prices(symbol, start, end, limit)

    @app.get("/api/ingestions", response_model=list[IngestionRun])
    def ingestion_runs(
        limit: int = Query(default=20, ge=1, le=100),
        repository: StockRepository = Depends(get_repository),
        user: dict = Depends(require_user),
        symbols: set[str] = Depends(get_user_symbols),
    ) -> list[IngestionRun]:
        if not symbols:
            return []
        return repository.list_ingestion_runs(limit, user["sub"])

    @app.get("/api/ingestions/exchanges", response_model=list[str])
    def ingestion_exchanges(user: dict = Depends(require_user)) -> list[str]:
        return configured_exchange_codes(load_user_stock_universe(user["sub"]))

    @app.post("/api/ingestions/run", response_model=IngestionRunResult)
    def run_ingestion(
        exchange: str | None = Query(default=None, description="Configured exchange code"),
        repository: StockRepository = Depends(get_repository),
        user: dict = Depends(require_user),
        symbols: set[str] = Depends(get_user_symbols),
    ) -> IngestionRunResult:
        if not symbols:
            raise HTTPException(status_code=403, detail="No stock config for this user")
        if not exchange:
            raise HTTPException(status_code=400, detail="Exchange is required")
        if exchange.strip().upper() not in {
            code.upper() for code in configured_exchange_codes(load_user_stock_universe(user["sub"]))
        }:
            raise HTTPException(status_code=404, detail="Exchange not configured for this user")
        return StockIngestionService(repository, YFinanceClient()).run_daily(exchange, user["sub"])

    return app


app = create_app()
