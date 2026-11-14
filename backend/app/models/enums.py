"""Closed value sets. Stored as text columns guarded by CHECK constraints (see base.enum_check),
which are easier to evolve with Alembic than native Postgres enum types."""

from enum import StrEnum

from app.services.units import WeightUnit as Unit

__all__ = [
    "BodyRegion",
    "GoalDirection",
    "GoalKind",
    "GoalMetric",
    "LoadType",
    "MuscleGroup",
    "MuscleRole",
    "RecordType",
    "SetType",
    "Unit",
    "WorkoutSource",
]


class MuscleGroup(StrEnum):
    PUSH = "push"
    PULL = "pull"
    LEGS = "legs"
    CORE = "core"


class BodyRegion(StrEnum):
    UPPER = "upper"
    LOWER = "lower"


class LoadType(StrEnum):
    EXTERNAL = "external"  # barbell, dumbbell, machine: weight_kg is the load
    BODYWEIGHT = "bodyweight"  # no load logged
    BODYWEIGHT_PLUS = "bodyweight_plus"  # body weight logged as load, or belt/vest added
    ASSISTED = "assisted"  # weight_kg is the assistance (subtracts from body weight)


class MuscleRole(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"


class WorkoutSource(StrEnum):
    APP = "app"
    IMPORT = "import"
    MCP = "mcp"
    COACH = "coach"


class SetType(StrEnum):
    WARMUP = "warmup"
    WORKING = "working"
    DROP = "drop"


class GoalKind(StrEnum):
    PRIORITY = "priority"
    CHALLENGE = "challenge"
    CONSISTENCY = "consistency"
    PERFORMANCE = "performance"


class GoalDirection(StrEnum):
    UP = "up"
    MAINTAIN = "maintain"
    DOWN = "down"


class GoalMetric(StrEnum):
    REPS = "reps"
    SETS = "sets"
    TONNAGE = "tonnage"
    E1RM = "e1rm"
    WEIGHT_AT_REPS = "weight_at_reps"
    SESSIONS_PER_WEEK = "sessions_per_week"


class RecordType(StrEnum):
    E1RM = "e1rm"
    WEIGHT_AT_REPS = "weight_at_reps"
    SESSION_TONNAGE = "session_tonnage"
