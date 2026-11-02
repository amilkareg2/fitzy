from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, create_engine, pool, text

from app.config import get_settings
from app.models import Base
from app.models.kb import KB_TABLES

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def _include_object_for(connection: Connection | None):
    """Hide the kb tables from autogenerate when the database has no pgvector (see 0002)."""
    has_vector = connection is None or bool(
        connection.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).scalar()
    )

    def include_object(obj, name, type_, reflected, compare_to):
        if type_ == "table" and name in KB_TABLES and not has_vector:
            return False
        return not (
            type_ == "index"
            and getattr(obj, "table", None) is not None
            and obj.table.name in KB_TABLES
            and not has_vector
        )

    return include_object


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=_include_object_for(connection),
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Tests (and scripts) may hand over an existing connection.
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    engine = create_engine(_database_url(), poolclass=pool.NullPool)
    with engine.connect() as conn:
        _run(conn)
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
