import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, enum_check, enum_column, uuid_pk
from app.models.enums import RecordType


class PersonalRecord(Base):
    """Derived from workout_set; can be truncated and rebuilt at any time."""

    __tablename__ = "personal_record"
    __table_args__ = (
        enum_check("record_type", RecordType),
        CheckConstraint(
            "record_type <> 'weight_at_reps' OR reps IS NOT NULL", name="reps_required"
        ),
        CheckConstraint("reps IS NULL OR reps >= 1", name="reps_positive"),
        CheckConstraint("value >= 0", name="value_non_negative"),
        Index("ix_personal_record_exercise_id_record_type", "exercise_id", "record_type", "reps"),
        Index("ix_personal_record_set_id", "set_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exercise.id", ondelete="CASCADE"), nullable=False
    )
    record_type: Mapped[str] = enum_column(RecordType, nullable=False)
    reps: Mapped[int | None] = mapped_column(Integer)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workout_set.id", ondelete="CASCADE"), nullable=False
    )
    achieved_on: Mapped[dt.date] = mapped_column(Date, nullable=False)
