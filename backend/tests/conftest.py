"""Shared fixtures.

DB tests run against a real Postgres when TEST_DATABASE_URL (preferred) or DATABASE_URL is set,
and are skipped otherwise. The schema is migrated to head once per session; every test runs in a
transaction that is rolled back, so the database is left as it was.

Heavy imports happen inside fixtures so the pure unit tests run without a database driver.
"""

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_AUTH_SECRET = "test-secret-" + "x" * 32

_db_url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
if _db_url:
    # Make app settings (and therefore get_engine) point at the test database.
    os.environ["DATABASE_URL"] = _db_url
os.environ.setdefault("APP_ENV", "test")
os.environ["AUTH_SECRET"] = TEST_AUTH_SECRET


@pytest.fixture(scope="session")
def db_url() -> str:
    if not _db_url:
        pytest.skip("no TEST_DATABASE_URL/DATABASE_URL set; skipping database tests")
    from app.config import get_settings

    return get_settings().database_url  # normalized to the psycopg driver


@pytest.fixture(scope="session")
def engine(db_url: str) -> Iterator[Any]:
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine

    eng = create_engine(db_url)
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["configure_logger"] = False
    with eng.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def has_pgvector(engine: Any) -> bool:
    from sqlalchemy import text

    with engine.connect() as conn:
        return bool(
            conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).scalar()
        )


@pytest.fixture
def db_session(engine: Any) -> Iterator[Any]:
    from sqlalchemy.orm import Session

    with engine.connect() as conn:
        trans = conn.begin()
        # Commits inside the code under test only release savepoints; the outer rollback wins.
        session = Session(bind=conn, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            trans.rollback()


@pytest.fixture
def client(db_session: Any) -> Iterator[Any]:
    from fastapi.testclient import TestClient

    from app.db import get_session
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TEST_AUTH_SECRET}"}
