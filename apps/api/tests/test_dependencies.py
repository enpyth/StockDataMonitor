from fastapi import HTTPException

from app.config import Settings
from app.dependencies import get_repository


def test_get_repository_with_missing_supabase_config_raises_http_503():
    settings = Settings(
        SUPABASE_URL=None,
        SUPABASE_ANON_KEY=None,
        SUPABASE_SERVICE_ROLE_KEY=None,
    )

    try:
        get_repository(settings)
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "Supabase URL and service role key are required" in exc.detail
    else:
        raise AssertionError("Expected HTTPException")
