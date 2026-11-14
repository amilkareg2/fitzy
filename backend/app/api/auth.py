"""Single-user login: password -> signed session (cookie + Bearer token)."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import SESSION_COOKIE, SettingsDep, current_session
from app.schemas.auth import LoginOut, LoginRequest, SessionOut
from app.security import tokens
from app.security.passwords import verify_password
from app.security.throttle import LoginThrottle

router = APIRouter(prefix="/auth", tags=["auth"])

throttle = LoginThrottle()


def _client_key(request: Request) -> str:
    # Cloud Run sets X-Forwarded-For; the first address is the client.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _as_datetime(epoch: int) -> datetime:
    return datetime.fromtimestamp(epoch, tz=UTC)


@router.post("/login", response_model=LoginOut)
def login(body: LoginRequest, request: Request, response: Response, settings: SettingsDep):
    key = _client_key(request)
    wait = throttle.retry_after(key)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts",
            headers={"Retry-After": str(wait)},
        )
    stored = settings.owner_password_hash
    if stored is None or not verify_password(body.password, stored.get_secret_value()):
        throttle.record_failure(key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong password")
    throttle.reset(key)

    ttl = settings.session_days * 86400
    token, session = tokens.issue(settings.auth_secret.get_secret_value(), ttl)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=ttl,
        httponly=True,
        secure=settings.is_deployed,
        samesite="lax",
        path="/",
    )
    return LoginOut(token=token, expires_at=_as_datetime(session.expires_at))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, settings: SettingsDep) -> None:
    # Clears the browser cookie. Tokens are stateless: rotate AUTH_SECRET to revoke all.
    response.delete_cookie(SESSION_COOKIE, path="/", secure=settings.is_deployed, httponly=True)


@router.get("/me", response_model=SessionOut)
def me(session: Annotated[tokens.Session, Depends(current_session)]) -> SessionOut:
    return SessionOut(expires_at=_as_datetime(session.expires_at))
