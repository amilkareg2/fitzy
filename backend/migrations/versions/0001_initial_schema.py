"""Initial schema (M0-M2): users, exercises/muscles, workouts and sets, routines, goals,
personal records and import runs.

The knowledge-base tables (pgvector) live in 0002 so this revision runs on any Postgres 13+.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id() -> sa.Column:
    return sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False)


def _in(table: str, column: str, *values: str) -> sa.CheckConstraint:
    allowed = ", ".join(f"'{v}'" for v in values)
    return sa.CheckConstraint(f"{column} IN ({allowed})", name=op.f(f"ck_{table}_{column}_valid"))


def _fk(table: str, column: str, ref: str, ondelete: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{ref}.id"], name=op.f(f"fk_{table}_{column}_{ref}"), ondelete=ondelete
    )


def upgrade() -> None:
    op.create_table(
        "app_user",
        _id(),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("unit_pref", sa.String(2), server_default="kg", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        _in("app_user", "unit_pref", "kg", "lb"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_app_user")),
        sa.UniqueConstraint("email", name=op.f("uq_app_user_email")),
    )

    op.create_table(
        "body_weight_log",
        _id(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("weight_kg", sa.Numeric(7, 3), nullable=False),
        sa.Column("source", sa.String(32), server_default="app", nullable=False),
        sa.CheckConstraint("weight_kg > 0", name=op.f("ck_body_weight_log_weight_kg_positive")),
        _fk("body_weight_log", "user_id", "app_user", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_body_weight_log")),
        sa.UniqueConstraint("user_id", "date", name=op.f("uq_body_weight_log_user_id_date")),
    )

    op.create_table(
        "muscle",
        _id(),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("muscle_group", sa.String(4), nullable=False),
        sa.Column("region", sa.String(5), nullable=False),
        _in("muscle", "muscle_group", "push", "pull", "legs", "core"),
        _in("muscle", "region", "upper", "lower"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_muscle")),
        sa.UniqueConstraint("name", name=op.f("uq_muscle_name")),
    )

    op.create_table(
        "exercise",
        _id(),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("equipment", sa.String(64), nullable=True),
        sa.Column("load_type", sa.String(15), server_default="external", nullable=False),
        sa.Column("default_rest_s", sa.Integer(), nullable=True),
        sa.Column("archived", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        _in("exercise", "load_type", "external", "bodyweight", "bodyweight_plus", "assisted"),
        sa.CheckConstraint(
            "default_rest_s IS NULL OR default_rest_s >= 0",
            name=op.f("ck_exercise_default_rest_s_non_negative"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_exercise")),
        sa.UniqueConstraint("name", name=op.f("uq_exercise_name")),
    )

    op.create_table(
        "exercise_muscle",
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("muscle_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(9), nullable=False),
        sa.Column("weight", sa.Numeric(3, 2), server_default="1.0", nullable=False),
        _in("exercise_muscle", "role", "primary", "secondary"),
        sa.CheckConstraint(
            "weight > 0 AND weight <= 1", name=op.f("ck_exercise_muscle_weight_range")
        ),
        _fk("exercise_muscle", "exercise_id", "exercise", "CASCADE"),
        _fk("exercise_muscle", "muscle_id", "muscle", "CASCADE"),
        sa.PrimaryKeyConstraint("exercise_id", "muscle_id", name=op.f("pk_exercise_muscle")),
    )
    op.create_index("ix_exercise_muscle_muscle_id", "exercise_muscle", ["muscle_id"])

    op.create_table(
        "tag",
        _id(),
        sa.Column("name", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tag")),
        sa.UniqueConstraint("name", name=op.f("uq_tag_name")),
    )

    op.create_table(
        "exercise_tag",
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        _fk("exercise_tag", "exercise_id", "exercise", "CASCADE"),
        _fk("exercise_tag", "tag_id", "tag", "CASCADE"),
        sa.PrimaryKeyConstraint("exercise_id", "tag_id", name=op.f("pk_exercise_tag")),
    )
    op.create_index("ix_exercise_tag_tag_id", "exercise_tag", ["tag_id"])

    op.create_table(
        "workout",
        _id(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source", sa.String(6), server_default="app", nullable=False),
        sa.Column("copied_from_id", sa.Uuid(), nullable=True),
        _in("workout", "source", "app", "import", "mcp", "coach"),
        sa.CheckConstraint(
            "ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at",
            name=op.f("ck_workout_ended_after_started"),
        ),
        _fk("workout", "user_id", "app_user", "CASCADE"),
        _fk("workout", "copied_from_id", "workout", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workout")),
    )
    op.create_index("ix_workout_user_id_date", "workout", ["user_id", "date"])

    op.create_table(
        "workout_exercise",
        _id(),
        sa.Column("workout_id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("position >= 0", name=op.f("ck_workout_exercise_position_non_negative")),
        _fk("workout_exercise", "workout_id", "workout", "CASCADE"),
        _fk("workout_exercise", "exercise_id", "exercise", "RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workout_exercise")),
    )
    op.create_index(
        "ix_workout_exercise_workout_id_position", "workout_exercise", ["workout_id", "position"]
    )
    op.create_index("ix_workout_exercise_exercise_id", "workout_exercise", ["exercise_id"])

    op.create_table(
        "workout_set",
        _id(),
        sa.Column("workout_exercise_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("weight_kg", sa.Numeric(9, 4), nullable=True),
        sa.Column("entered_unit", sa.String(2), server_default="kg", nullable=False),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("rpe", sa.Numeric(3, 1), nullable=True),
        sa.Column("set_type", sa.String(7), server_default="working", nullable=False),
        sa.Column("distance_m", sa.Numeric(10, 2), nullable=True),
        sa.Column("duration_s", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "logged_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.Column("import_hash", sa.String(64), nullable=True),
        _in("workout_set", "entered_unit", "kg", "lb"),
        _in("workout_set", "set_type", "warmup", "working", "drop"),
        sa.CheckConstraint("position >= 0", name=op.f("ck_workout_set_position_non_negative")),
        sa.CheckConstraint(
            "weight_kg IS NULL OR weight_kg >= 0",
            name=op.f("ck_workout_set_weight_kg_non_negative"),
        ),
        sa.CheckConstraint(
            "reps IS NULL OR reps >= 0", name=op.f("ck_workout_set_reps_non_negative")
        ),
        sa.CheckConstraint(
            "rpe IS NULL OR (rpe >= 0 AND rpe <= 10)", name=op.f("ck_workout_set_rpe_range")
        ),
        sa.CheckConstraint(
            "distance_m IS NULL OR distance_m >= 0",
            name=op.f("ck_workout_set_distance_m_non_negative"),
        ),
        sa.CheckConstraint(
            "duration_s IS NULL OR duration_s >= 0",
            name=op.f("ck_workout_set_duration_s_non_negative"),
        ),
        sa.CheckConstraint(
            "weight_kg IS NOT NULL OR reps IS NOT NULL "
            "OR distance_m IS NOT NULL OR duration_s IS NOT NULL",
            name=op.f("ck_workout_set_has_measurement"),
        ),
        _fk("workout_set", "workout_exercise_id", "workout_exercise", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workout_set")),
        sa.UniqueConstraint("import_hash", name=op.f("uq_workout_set_import_hash")),
    )
    op.create_index(
        "ix_workout_set_workout_exercise_id_position",
        "workout_set",
        ["workout_exercise_id", "position"],
    )

    op.create_table(
        "routine",
        _id(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        _fk("routine", "user_id", "app_user", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_routine")),
    )
    op.create_index("ix_routine_user_id", "routine", ["user_id"])

    op.create_table(
        "routine_exercise",
        _id(),
        sa.Column("routine_id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("target_sets", sa.Integer(), nullable=True),
        sa.Column("target_reps", sa.Integer(), nullable=True),
        sa.Column("target_weight_kg", sa.Numeric(9, 4), nullable=True),
        sa.CheckConstraint("position >= 0", name=op.f("ck_routine_exercise_position_non_negative")),
        sa.CheckConstraint(
            "target_sets IS NULL OR target_sets >= 0",
            name=op.f("ck_routine_exercise_target_sets_non_negative"),
        ),
        sa.CheckConstraint(
            "target_reps IS NULL OR target_reps >= 0",
            name=op.f("ck_routine_exercise_target_reps_non_negative"),
        ),
        sa.CheckConstraint(
            "target_weight_kg IS NULL OR target_weight_kg >= 0",
            name=op.f("ck_routine_exercise_target_weight_kg_non_negative"),
        ),
        _fk("routine_exercise", "routine_id", "routine", "CASCADE"),
        _fk("routine_exercise", "exercise_id", "exercise", "RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_routine_exercise")),
    )
    op.create_index(
        "ix_routine_exercise_routine_id_position", "routine_exercise", ["routine_id", "position"]
    )

    op.create_table(
        "goal",
        _id(),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(11), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=True),
        sa.Column("muscle_id", sa.Uuid(), nullable=True),
        sa.Column("direction", sa.String(8), nullable=True),
        sa.Column("metric", sa.String(17), nullable=True),
        sa.Column("target_value", sa.Numeric(12, 4), nullable=True),
        sa.Column("start_date", sa.Date(), server_default=sa.func.current_date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column(
            "valid_from", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.Uuid(), nullable=True),
        _in("goal", "kind", "priority", "challenge", "consistency", "performance"),
        _in("goal", "direction", "up", "maintain", "down"),
        _in(
            "goal",
            "metric",
            "reps",
            "sets",
            "tonnage",
            "e1rm",
            "weight_at_reps",
            "sessions_per_week",
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date", name=op.f("ck_goal_end_after_start")
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from", name=op.f("ck_goal_valid_range")
        ),
        _fk("goal", "user_id", "app_user", "CASCADE"),
        _fk("goal", "exercise_id", "exercise", "RESTRICT"),
        _fk("goal", "muscle_id", "muscle", "RESTRICT"),
        _fk("goal", "replaced_by_id", "goal", "SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_goal")),
    )
    op.create_index(
        "ix_goal_user_id_active",
        "goal",
        ["user_id"],
        postgresql_where=sa.text("valid_to IS NULL"),
    )

    op.create_table(
        "personal_record",
        _id(),
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("record_type", sa.String(15), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("value", sa.Numeric(12, 4), nullable=False),
        sa.Column("set_id", sa.Uuid(), nullable=False),
        sa.Column("achieved_on", sa.Date(), nullable=False),
        _in("personal_record", "record_type", "e1rm", "weight_at_reps", "session_tonnage"),
        sa.CheckConstraint(
            "record_type <> 'weight_at_reps' OR reps IS NOT NULL",
            name=op.f("ck_personal_record_reps_required"),
        ),
        sa.CheckConstraint(
            "reps IS NULL OR reps >= 1", name=op.f("ck_personal_record_reps_positive")
        ),
        sa.CheckConstraint("value >= 0", name=op.f("ck_personal_record_value_non_negative")),
        _fk("personal_record", "exercise_id", "exercise", "CASCADE"),
        _fk("personal_record", "set_id", "workout_set", "CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_personal_record")),
    )
    op.create_index(
        "ix_personal_record_exercise_id_record_type",
        "personal_record",
        ["exercise_id", "record_type", "reps"],
    )
    op.create_index("ix_personal_record_set_id", "personal_record", ["set_id"])

    op.create_table(
        "import_run",
        _id(),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("rows_read", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_loaded", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "issues",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "rows_read >= 0 AND rows_loaded >= 0",
            name=op.f("ck_import_run_row_counts_non_negative"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_run")),
    )


def downgrade() -> None:
    for table in (
        "import_run",
        "personal_record",
        "goal",
        "routine_exercise",
        "routine",
        "workout_set",
        "workout_exercise",
        "workout",
        "exercise_tag",
        "tag",
        "exercise_muscle",
        "exercise",
        "muscle",
        "body_weight_log",
        "app_user",
    ):
        op.drop_table(table)
