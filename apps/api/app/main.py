from datetime import UTC, date, datetime

from fastapi import Depends, FastAPI, Query
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
from .yfinance_adapter import YFinanceClient


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

    @app.get("/api/stocks", response_model=list[Security], dependencies=[Depends(require_user)])
    def list_stocks(repository: StockRepository = Depends(get_repository)) -> list[Security]:
        return repository.list_securities()

    @app.get("/api/stocks/{symbol}", response_model=Security, dependencies=[Depends(require_user)])
    def get_stock(symbol: str, repository: StockRepository = Depends(get_repository)) -> Security:
        security = repository.get_security(symbol)
        if security is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Stock not found")
        return security

    @app.get("/api/stocks/{symbol}/ohlcv", response_model=list[OhlcvDaily], dependencies=[Depends(require_user)])
    def get_ohlcv(
        symbol: str,
        start: str | None = None,
        end: str | None = None,
        limit: int = Query(default=260, ge=1, le=1000),
        repository: StockRepository = Depends(get_repository),
    ) -> list[OhlcvDaily]:
        return repository.list_ohlcv(symbol, start, end, limit)

    @app.get("/api/stocks/{symbol}/ohlcv/today", response_model=list[OhlcvDaily], dependencies=[Depends(require_user)])
    def get_today_ohlcv(
        symbol: str,
        trading_date: date | None = Query(
            default=None,
            description="Trading date to fetch. Defaults to the API server's current UTC date.",
        ),
        repository: StockRepository = Depends(get_repository),
    ) -> list[OhlcvDaily]:
        target_date = trading_date or datetime.now(UTC).date()
        date_value = target_date.isoformat()
        return repository.list_ohlcv(symbol, date_value, date_value, 1)

    @app.get("/api/quotes/latest", response_model=list[QuoteSnapshot], dependencies=[Depends(require_user)])
    def latest_quotes(repository: StockRepository = Depends(get_repository)) -> list[QuoteSnapshot]:
        return repository.list_latest_quotes()

    @app.get("/api/ingestions", response_model=list[IngestionRun], dependencies=[Depends(require_user)])
    def ingestion_runs(
        limit: int = Query(default=20, ge=1, le=100),
        repository: StockRepository = Depends(get_repository),
    ) -> list[IngestionRun]:
        return repository.list_ingestion_runs(limit)

    @app.post("/api/ingestions/run", response_model=IngestionRunResult, dependencies=[Depends(require_user)])
    def run_ingestion(repository: StockRepository = Depends(get_repository)) -> IngestionRunResult:
        return StockIngestionService(repository, YFinanceClient()).run_daily()

    return app


app = create_app()
