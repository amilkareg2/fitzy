"""The Alembic migrations and the SQLAlchemy models must describe the same schema."""

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.models import Base
from app.models.kb import KB_TABLES


def test_models_match_migrations(engine, has_pgvector) -> None:
    def include_object(obj, name, type_, reflected, compare_to):
        table = name if type_ == "table" else getattr(getattr(obj, "table", None), "name", None)
        return has_pgvector or table not in KB_TABLES

    with engine.connect() as conn:
        ctx = MigrationContext.configure(
            conn,
            opts={
                "include_object": include_object,
                "compare_type": True,
                "compare_server_default": False,  # server defaults render differently; not diffed
            },
        )
        diff = compare_metadata(ctx, Base.metadata)
    assert diff == [], f"models and migrations differ: {diff}"
