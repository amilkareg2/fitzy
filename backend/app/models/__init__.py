"""All models, imported here so Base.metadata is complete for Alembic and tests."""

from app.models.base import Base
from app.models.exercise import Exercise, ExerciseMuscle, Muscle, Tag, exercise_tag
from app.models.goal import Goal
from app.models.import_run import ImportRun
from app.models.kb import KbChunk, KbDocument
from app.models.record import PersonalRecord
from app.models.routine import Routine, RoutineExercise
from app.models.user import BodyWeightLog, User
from app.models.workout import Workout, WorkoutExercise, WorkoutSet

__all__ = [
    "Base",
    "BodyWeightLog",
    "Exercise",
    "ExerciseMuscle",
    "Goal",
    "ImportRun",
    "KbChunk",
    "KbDocument",
    "Muscle",
    "PersonalRecord",
    "Routine",
    "RoutineExercise",
    "Tag",
    "User",
    "Workout",
    "WorkoutExercise",
    "WorkoutSet",
    "exercise_tag",
]
