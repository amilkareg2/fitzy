import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, uuid_pk
from app.models.exercise import Exercise


class Routine(Base):
    __tablename__ = "routine"
    __table_args__ = (Index("ix_routine_user_id", "user_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    exercises: Mapped[list["RoutineExercise"]] = relationship(
        back_populates="routine",
        cascade="all, delete-orphan",
        order_by="RoutineExercise.position",
    )


class RoutineExercise(Base):
    __tablename__ = "routine_exercise"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_non_negative"),
        CheckConstraint("target_sets IS NULL OR target_sets >= 0", name="target_sets_non_negative"),
        CheckConstraint("target_reps IS NULL OR target_reps >= 0", name="target_reps_non_negative"),
        CheckConstraint(
            "target_weight_kg IS NULL OR target_weight_kg >= 0",
            name="target_weight_kg_non_negative",
        ),
        Index("ix_routine_exercise_routine_id_position", "routine_id", "position"),
    )

    # Surrogate key: the same exercise may appear twice in a routine (e.g. heavy and light).
    id: Mapped[uuid.UUID] = uuid_pk()
    routine_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("routine.id", ondelete="CASCADE"), nullable=False
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exercise.id", ondelete="RESTRICT"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    target_sets: Mapped[int | None] = mapped_column(Integer)
    target_reps: Mapped[int | None] = mapped_column(Integer)
    target_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(9, 4))

    routine: Mapped[Routine] = relationship(back_populates="exercises")
    exercise: Mapped[Exercise] = relationship()
