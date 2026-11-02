"""Database engine and session handling."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        # Cloud Run scales to zero; keep the pool small.
        pool_size=5,
        max_overflow=5,
        # Neon suspends its compute after 5 idle minutes and drops open connections:
        # recycle before that, and allow time for a cold start on the first connect.
        pool_recycle=240,
        connect_args={"connect_timeout": 15},
    )


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, rolled back on error."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
