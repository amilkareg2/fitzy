import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, enum_check, enum_column, uuid_pk
from app.models.enums import GoalDirection, GoalKind, GoalMetric


class Goal(Base):
    """Append-only, versioned goal.

    Editing a goal closes the current row (``valid_to = now()``, ``replaced_by_id = new.id``) and
    inserts a new one, so the coach can reason about how goals changed over time.
    A goal is active while ``valid_to IS NULL``.
    """

    __tablename__ = "goal"
    __table_args__ = (
        enum_check("kind", GoalKind),
        enum_check("direction", GoalDirection),
        enum_check("metric", GoalMetric),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="end_after_start"),
        CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="valid_range"),
        Index(
            "ix_goal_user_id_active",
            "user_id",
            postgresql_where=text("valid_to IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = enum_column(GoalKind, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    exercise_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("exercise.id", ondelete="RESTRICT")
    )
    muscle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("muscle.id", ondelete="RESTRICT")
    )
    direction: Mapped[str | None] = enum_column(GoalDirection)
    metric: Mapped[str | None] = enum_column(GoalMetric)
    target_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    start_date: Mapped[dt.date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    end_date: Mapped[dt.date | None] = mapped_column(Date)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=text("'{}'::text[]")
    )
    valid_from: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("goal.id", ondelete="SET NULL")
    )

    @property
    def is_active(self) -> bool:
        return self.valid_to is None
