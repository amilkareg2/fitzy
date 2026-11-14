"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session
from app.security import tokens

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

SESSION_COOKIE = "fitzy_session"

_bearer = HTTPBearer(auto_error=False)


def current_session(
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    cookie_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> tokens.Session:
    """The owner's session, from the session cookie (browser) or a Bearer token (CLI, MCP)."""
    token = credentials.credentials if credentials is not None else cookie_token
    session = tokens.verify(token, settings.auth_secret.get_secret_value()) if token else None
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return session


def require_owner(session: Annotated[tokens.Session, Depends(current_session)]) -> str:
    """Single-user auth: any valid session belongs to the owner."""
    return tokens.SUBJECT


OwnerDep = Annotated[str, Depends(require_owner)]
