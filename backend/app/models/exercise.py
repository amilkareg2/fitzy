import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    text,
)
from sqlalchemy.engine.default import DefaultExecutionContext
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, enum_check, enum_column, uuid_pk
from app.models.enums import BodyRegion, LoadType, MuscleGroup, MuscleRole

PRIMARY_MUSCLE_WEIGHT = Decimal("1.0")
SECONDARY_MUSCLE_WEIGHT = Decimal("0.5")


class Muscle(Base):
    __tablename__ = "muscle"
    __table_args__ = (enum_check("muscle_group", MuscleGroup), enum_check("region", BodyRegion))

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # "group" is a reserved word; the attribute keeps the spec name, the column does not.
    group: Mapped[str] = enum_column(MuscleGroup, "muscle_group", nullable=False)
    region: Mapped[str] = enum_column(BodyRegion, nullable=False)


exercise_tag = Table(
    "exercise_tag",
    Base.metadata,
    Column("exercise_id", ForeignKey("exercise.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_exercise_tag_tag_id", "tag_id"),
)


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


class Exercise(Base):
    __tablename__ = "exercise"
    __table_args__ = (
        enum_check("load_type", LoadType),
        CheckConstraint(
            "default_rest_s IS NULL OR default_rest_s >= 0", name="default_rest_s_non_negative"
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)  # FitNotes category text
    equipment: Mapped[str | None] = mapped_column(String(64))
    load_type: Mapped[str] = enum_column(
        LoadType, nullable=False, default=LoadType.EXTERNAL, server_default="external"
    )
    default_rest_s: Mapped[int | None] = mapped_column(Integer)
    archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    muscles: Mapped[list["ExerciseMuscle"]] = relationship(
        back_populates="exercise", cascade="all, delete-orphan"
    )
    tags: Mapped[list[Tag]] = relationship(secondary=exercise_tag)


def _default_muscle_weight(context: DefaultExecutionContext) -> Decimal:
    role = context.get_current_parameters().get("role")
    return SECONDARY_MUSCLE_WEIGHT if role == MuscleRole.SECONDARY else PRIMARY_MUSCLE_WEIGHT


class ExerciseMuscle(Base):
    __tablename__ = "exercise_muscle"
    __table_args__ = (
        enum_check("role", MuscleRole),
        CheckConstraint("weight > 0 AND weight <= 1", name="weight_range"),
        Index("ix_exercise_muscle_muscle_id", "muscle_id"),
    )

    exercise_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exercise.id", ondelete="CASCADE"), primary_key=True
    )
    muscle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("muscle.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = enum_column(MuscleRole, nullable=False)
    # Fraction of a set credited to this muscle: primary 1.0, secondary 0.5 unless overridden.
    weight: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, default=_default_muscle_weight, server_default="1.0"
    )

    exercise: Mapped[Exercise] = relationship(back_populates="muscles")
    muscle: Mapped[Muscle] = relationship()
