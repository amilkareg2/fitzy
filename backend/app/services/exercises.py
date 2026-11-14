from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Exercise


def list_exercises(session: Session, *, include_archived: bool = False) -> Sequence[Exercise]:
    stmt = select(Exercise).order_by(Exercise.name)
    if not include_archived:
        stmt = stmt.where(Exercise.archived.is_(False))
    return session.scalars(stmt).all()
