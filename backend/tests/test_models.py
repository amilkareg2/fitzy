"""Smoke tests for the schema: relationships, defaults and the constraints that guard invariants."""

import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import (
    Exercise,
    ExerciseMuscle,
    Goal,
    Muscle,
    PersonalRecord,
    User,
    Workout,
    WorkoutExercise,
    WorkoutSet,
)
from app.models.enums import GoalKind, MuscleRole, SetType, WorkoutSource
from app.services.units import normalize_weight


@pytest.fixture
def user(db_session) -> User:
    u = User(email="owner@example.com")
    db_session.add(u)
    db_session.flush()
    return u


@pytest.fixture
def bench(db_session) -> Exercise:
    ex = Exercise(name="Flat Barbell Bench Press", category="Chest", equipment="barbell")
    db_session.add(ex)
    db_session.flush()
    return ex


def _workout_with_sets(user: User, exercise: Exercise) -> Workout:
    w = Workout(user_id=user.id, date=dt.date(2026, 10, 30), source=WorkoutSource.APP)
    we = WorkoutExercise(exercise=exercise, position=0)
    w.exercises.append(we)
    for i, (value, unit, reps) in enumerate([(20, "kg", 10), (135, "lb", 8), (225, "lb", 5)]):
        stored = normalize_weight(value, unit)
        we.sets.append(
            WorkoutSet(
                position=i,
                weight_kg=stored.weight_kg,
                entered_unit=stored.entered_unit,
                reps=reps,
                set_type=SetType.WARMUP if i == 0 else SetType.WORKING,
            )
        )
    return w


def test_workout_with_sets_round_trip(db_session, user, bench) -> None:
    db_session.add(_workout_with_sets(user, bench))
    db_session.flush()
    db_session.expire_all()

    workout = db_session.scalars(select(Workout).where(Workout.user_id == user.id)).one()
    [we] = workout.exercises
    assert we.exercise.name == "Flat Barbell Bench Press"
    assert [s.reps for s in we.sets] == [10, 8, 5]
    top = we.sets[-1]
    assert top.weight_kg == Decimal("102.0583")
    assert top.entered_unit == "lb"
    assert top.set_type == "working"
    assert top.logged_at is not None  # server default
    assert workout.source == "app"


def test_server_side_defaults(db_session, user) -> None:
    assert user.unit_pref == "kg"
    db_session.refresh(user)
    assert user.created_at is not None


def test_deleting_workout_cascades_to_sets(db_session, user, bench) -> None:
    workout = _workout_with_sets(user, bench)
    db_session.add(workout)
    db_session.flush()
    we_id = workout.exercises[0].id
    db_session.delete(workout)
    db_session.flush()
    remaining = select(func.count()).where(WorkoutSet.workout_exercise_id == we_id)
    assert db_session.scalar(remaining) == 0


@pytest.mark.parametrize(
    "bad",
    [
        {"reps": -1, "weight_kg": Decimal(20)},
        {"reps": 5, "weight_kg": Decimal(-20)},
        {"reps": 5, "weight_kg": Decimal(20), "rpe": Decimal("11")},
        {"reps": 5, "weight_kg": Decimal(20), "set_type": "superset"},
        {"reps": 5, "weight_kg": Decimal(20), "entered_unit": "stone"},
        {},  # no measurement at all
    ],
)
def test_set_check_constraints(db_session, user, bench, bad) -> None:
    w = Workout(user_id=user.id, date=dt.date(2026, 10, 30))
    we = WorkoutExercise(exercise=bench, position=0)
    w.exercises.append(we)
    we.sets.append(WorkoutSet(position=0, **bad))
    db_session.add(w)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_import_hash_is_unique(db_session, user, bench) -> None:
    w = Workout(user_id=user.id, date=dt.date(2026, 10, 30), source=WorkoutSource.IMPORT)
    we = WorkoutExercise(exercise=bench, position=0)
    w.exercises.append(we)
    we.sets.extend(
        WorkoutSet(position=i, weight_kg=Decimal(60), reps=5, import_hash="a" * 64)
        for i in range(2)
    )
    db_session.add(w)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_exercise_muscle_weight_defaults_by_role(db_session, bench) -> None:
    chest = Muscle(name="Chest", group="push", region="upper")
    triceps = Muscle(name="Triceps", group="push", region="upper")
    bench.muscles.extend(
        [
            ExerciseMuscle(muscle=chest, role=MuscleRole.PRIMARY),
            ExerciseMuscle(muscle=triceps, role=MuscleRole.SECONDARY),
        ]
    )
    db_session.flush()
    db_session.expire_all()
    weights = {em.muscle.name: em.weight for em in bench.muscles}
    assert weights == {"Chest": Decimal("1.00"), "Triceps": Decimal("0.50")}


def test_goal_versioning(db_session, user, bench) -> None:
    v1 = Goal(
        user_id=user.id,
        kind=GoalKind.PERFORMANCE,
        title="Bench 100 kg",
        exercise_id=bench.id,
        direction="up",
        metric="e1rm",
        target_value=Decimal(100),
    )
    db_session.add(v1)
    db_session.flush()
    v2 = Goal(
        user_id=user.id,
        kind=GoalKind.PERFORMANCE,
        title="Bench 110 kg",
        exercise_id=bench.id,
        direction="up",
        metric="e1rm",
        target_value=Decimal(110),
    )
    db_session.add(v2)
    db_session.flush()
    v1.valid_to = func.now()
    v1.replaced_by_id = v2.id
    db_session.flush()
    db_session.expire_all()

    active = db_session.scalars(
        select(Goal).where(Goal.user_id == user.id, Goal.valid_to.is_(None))
    ).all()
    assert [g.title for g in active] == ["Bench 110 kg"]
    assert active[0].tags == []
    assert db_session.get(Goal, v1.id).replaced_by_id == v2.id


def test_weight_at_reps_record_requires_reps(db_session, user, bench) -> None:
    workout = _workout_with_sets(user, bench)
    db_session.add(workout)
    db_session.flush()
    top = workout.exercises[0].sets[-1]
    db_session.add(
        PersonalRecord(
            exercise_id=bench.id,
            record_type="weight_at_reps",
            value=top.weight_kg,
            set_id=top.id,
            achieved_on=workout.date,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_kb_tables_when_pgvector_present(db_session, has_pgvector) -> None:
    if not has_pgvector:
        pytest.skip("pgvector not installed on the test database (kb tables are M4)")
    from app.models import KbChunk, KbDocument

    doc = KbDocument(title="Volume landmarks", topics=["hypertrophy"])
    doc.chunks.append(
        KbChunk(
            chunk_index=0,
            text="10-20 sets per muscle per week",
            embedding=[0.0] * 1023 + [1.0],
            meta={"page": 1},
        )
    )
    db_session.add(doc)
    db_session.flush()
    nearest = db_session.scalars(
        select(KbChunk).order_by(KbChunk.embedding.cosine_distance([0.0] * 1023 + [1.0])).limit(1)
    ).one()
    assert nearest.meta == {"page": 1}
