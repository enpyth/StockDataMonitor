from functools import lru_cache

from fastapi import Depends, HTTPException, status

from .config import Settings, get_settings
from .repository import StockRepository, SupabaseStockRepository, get_supabase_client


@lru_cache
def get_repository_from_settings() -> StockRepository:
    settings = get_settings()
    return SupabaseStockRepository(get_supabase_client(settings))


def get_repository(settings: Settings = Depends(get_settings)) -> StockRepository:
    try:
        if settings != get_settings():
            return SupabaseStockRepository(get_supabase_client(settings))
        return get_repository_from_settings()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
