"""M4: knowledge-base tables for the coach (pgvector).

Needs the ``vector`` extension (the pgvector/pgvector:pg16 image and Cloud SQL both ship it).
If the server does not have pgvector available, the revision is skipped with a warning in
``local``/``test`` environments, so the rest of the schema still works on a plain Postgres.
In ``dev``/``prod`` it fails instead. After installing pgvector on a database where this was
skipped, re-apply with ``alembic downgrade 0001_initial_schema && alembic upgrade head``.

Revision ID: 0002_kb_pgvector
Revises: 0001_initial_schema
Create Date: 2026-10-30
"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from app.config import get_settings

revision: str = "0002_kb_pgvector"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 1024
logger = logging.getLogger("alembic.runtime.migration")


def _pgvector_available() -> bool:
    return bool(
        op.get_bind()
        .execute(sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"))
        .scalar()
    )


def upgrade() -> None:
    if not _pgvector_available():
        if get_settings().is_deployed:
            raise RuntimeError("pgvector extension is not available on this database server")
        logger.warning("pgvector not available: skipping kb_document/kb_chunk (M4) tables")
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "kb_document",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("license", sa.String(100), nullable=True),
        sa.Column(
            "topics",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kb_document")),
        sa.UniqueConstraint("url", name=op.f("uq_kb_document_url")),
    )

    op.create_table(
        "kb_chunk",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["kb_document.id"],
            name=op.f("fk_kb_chunk_document_id_kb_document"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kb_chunk")),
    )
    op.create_index(
        "ix_kb_chunk_document_id_chunk_index",
        "kb_chunk",
        ["document_id", "chunk_index"],
        unique=True,
    )
    op.create_index(
        "ix_kb_chunk_embedding_hnsw",
        "kb_chunk",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS kb_chunk")
    op.execute("DROP TABLE IF EXISTS kb_document")
    # The extension is left installed: dropping it needs superuser and may be shared.
