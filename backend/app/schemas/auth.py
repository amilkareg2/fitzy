from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)


class SessionOut(BaseModel):
    expires_at: datetime


class LoginOut(SessionOut):
    # Also returned in the body so non-browser clients (CLI, MCP server) can use it as a
    # Bearer token. Browsers use the HttpOnly cookie and can ignore it.
    token: str
