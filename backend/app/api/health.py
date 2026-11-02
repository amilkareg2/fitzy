import logging

from fastapi import APIRouter
from sqlalchemy import text

from app.db import get_engine
from app.schemas.health import HealthOut

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> HealthOut:
    """Liveness plus a best-effort DB check. Always 200 while the process is up, so a database
    blip does not make Cloud Run recycle healthy instances; ``db`` reports reachability."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        db = "ok"
    except Exception:
        logger.warning("health: database unreachable", exc_info=True)
        db = "unavailable"
    return HealthOut(status="ok", db=db)
