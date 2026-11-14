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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, enum_check, enum_column, uuid_pk
from app.models.enums import SetType, Unit, WorkoutSource
from app.models.exercise import Exercise


class Workout(Base):
    __tablename__ = "workout"
    __table_args__ = (
        enum_check("source", WorkoutSource),
        CheckConstraint(
            "ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at",
            name="ended_after_started",
        ),
        Index("ix_workout_user_id_date", "user_id", "date"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = enum_column(
        WorkoutSource, nullable=False, default=WorkoutSource.APP, server_default="app"
    )
    copied_from_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workout.id", ondelete="SET NULL")
    )

    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        back_populates="workout",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.position",
    )


class WorkoutExercise(Base):
    __tablename__ = "workout_exercise"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_non_negative"),
        Index("ix_workout_exercise_workout_id_position", "workout_id", "position"),
        Index("ix_workout_exercise_exercise_id", "exercise_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workout_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workout.id", ondelete="CASCADE"), nullable=False
    )
    # RESTRICT: exercises with history are archived, never deleted.
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exercise.id", ondelete="RESTRICT"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    workout: Mapped[Workout] = relationship(back_populates="exercises")
    exercise: Mapped[Exercise] = relationship()
    sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="workout_exercise",
        cascade="all, delete-orphan",
        order_by="WorkoutSet.position",
    )


class WorkoutSet(Base):
    """One logged set. ``set`` is a reserved word, hence the table name."""

    __tablename__ = "workout_set"
    __table_args__ = (
        enum_check("entered_unit", Unit),
        enum_check("set_type", SetType),
        CheckConstraint("position >= 0", name="position_non_negative"),
        CheckConstraint("weight_kg IS NULL OR weight_kg >= 0", name="weight_kg_non_negative"),
        CheckConstraint("reps IS NULL OR reps >= 0", name="reps_non_negative"),
        CheckConstraint("rpe IS NULL OR (rpe >= 0 AND rpe <= 10)", name="rpe_range"),
        CheckConstraint("distance_m IS NULL OR distance_m >= 0", name="distance_m_non_negative"),
        CheckConstraint("duration_s IS NULL OR duration_s >= 0", name="duration_s_non_negative"),
        CheckConstraint(
            "weight_kg IS NOT NULL OR reps IS NOT NULL "
            "OR distance_m IS NOT NULL OR duration_s IS NOT NULL",
            name="has_measurement",
        ),
        Index("ix_workout_set_workout_exercise_id_position", "workout_exercise_id", "position"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    workout_exercise_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workout_exercise.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    # Canonical storage is kg; entered_unit remembers what the user typed so it can be shown back
    # exactly (see app.services.units). 4 decimals keep lb -> kg -> lb round trips exact to 0.01.
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(9, 4))
    entered_unit: Mapped[str] = enum_column(
        Unit, nullable=False, default=Unit.KG, server_default="kg"
    )
    reps: Mapped[int | None] = mapped_column(Integer)
    rpe: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    set_type: Mapped[str] = enum_column(
        SetType, nullable=False, default=SetType.WORKING, server_default="working"
    )
    distance_m: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    duration_s: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    logged_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Hash of the source row for idempotent imports; NULL for sets logged in the app.
    import_hash: Mapped[str | None] = mapped_column(String(64), unique=True)

    workout_exercise: Mapped[WorkoutExercise] = relationship(back_populates="sets")
