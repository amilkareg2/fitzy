"""Shared FastAPI dependencies."""

import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_session

SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

_bearer = HTTPBearer(auto_error=False)


def require_owner(
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    """Single-user auth placeholder: ``Authorization: Bearer <AUTH_SECRET>``.

    Returns the owner's email. To be replaced by the real M0 login flow; routers depend on
    ``OwnerDep`` so the swap does not touch them.
    """
    expected = settings.auth_secret.get_secret_value().encode()
    if credentials is None or not hmac.compare_digest(credentials.credentials.encode(), expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return settings.owner_email


OwnerDep = Annotated[str, Depends(require_owner)]
