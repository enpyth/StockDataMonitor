from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import create_client

from .config import Settings, get_settings

bearer = HTTPBearer(auto_error=False)


def require_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = credentials.credentials
    if settings.supabase_url and settings.supabase_anon_key:
        client = create_client(str(settings.supabase_url), settings.supabase_anon_key)
        try:
            user_response = client.auth.get_user(token)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token") from exc

        user = user_response.user
        email = (user.email or "").strip().lower()
        if not email:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Authenticated user email is required")
        if not is_allowed_email(email, settings.allowed_user_email_set):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User email is not allowed")
        return {"sub": user.id, "email": email, "role": "authenticated"}

    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase auth is not configured")


def is_allowed_email(email: str, allowed_emails: set[str]) -> bool:
    if not allowed_emails:
        return True
    return email.strip().lower() in allowed_emails
