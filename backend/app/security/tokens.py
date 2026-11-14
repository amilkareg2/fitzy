"""Signed, expiring session tokens for the single owner (standard library only).

Token: ``<payload b64url>.<signature b64url>``, where the payload is JSON
``{"sub": "owner", "iat": ..., "exp": ..., "v": 1}`` and the signature is HMAC-SHA256 with
a key derived from AUTH_SECRET. Rotating AUTH_SECRET signs everyone (i.e. the owner) out.
The same token works as a cookie (browser) and as a Bearer token (CLI, MCP server).
"""

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

SUBJECT = "owner"
VERSION = 1


@dataclass(frozen=True)
class Session:
    issued_at: int
    expires_at: int


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64url(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _key(secret: str) -> bytes:
    # Domain separation: AUTH_SECRET may sign other things later.
    return hmac.new(secret.encode(), b"fitzy-session-v1", hashlib.sha256).digest()


def _sign(payload: str, secret: str) -> str:
    return _b64url(hmac.new(_key(secret), payload.encode(), hashlib.sha256).digest())


def issue(secret: str, ttl_seconds: int, now: int | None = None) -> tuple[str, Session]:
    issued = int(time.time()) if now is None else now
    session = Session(issued_at=issued, expires_at=issued + ttl_seconds)
    body = {"sub": SUBJECT, "iat": session.issued_at, "exp": session.expires_at, "v": VERSION}
    payload = _b64url(json.dumps(body, separators=(",", ":")).encode())
    return f"{payload}.{_sign(payload, secret)}", session


def verify(token: str, secret: str, now: int | None = None) -> Session | None:
    """Return the session if the token is authentic and unexpired, else None."""
    try:
        payload, signature = token.split(".")
        if not hmac.compare_digest(signature, _sign(payload, secret)):
            return None
        body = json.loads(_unb64url(payload))
    except (ValueError, json.JSONDecodeError):
        return None
    if body.get("sub") != SUBJECT or body.get("v") != VERSION:
        return None
    current = int(time.time()) if now is None else now
    exp, iat = body.get("exp"), body.get("iat")
    if not isinstance(exp, int) or not isinstance(iat, int) or exp <= current:
        return None
    return Session(issued_at=iat, expires_at=exp)
