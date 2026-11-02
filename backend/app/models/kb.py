"""Knowledge base for the coach's retrieval (milestone M4). Requires the pgvector extension;
see migrations/versions/0002_kb_pgvector.py for how environments without it are handled."""

import uuid
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, uuid_pk

EMBEDDING_DIM = 1024
KB_TABLES = frozenset({"kb_document", "kb_chunk"})


class KbDocument(Base):
    __tablename__ = "kb_document"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, unique=True)
    license: Mapped[str | None] = mapped_column(String(100))
    topics: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, default=list, server_default=sql_text("'{}'::text[]")
    )

    chunks: Mapped[list["KbChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="KbChunk.chunk_index"
    )


class KbChunk(Base):
    __tablename__ = "kb_chunk"
    __table_args__ = (
        Index("ix_kb_chunk_document_id_chunk_index", "document_id", "chunk_index", unique=True),
        Index(
            "ix_kb_chunk_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("kb_document.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Nullable so chunks can be stored before they are embedded.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    # "metadata" is reserved on declarative classes; the column keeps the spec name.
    meta: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=sql_text("'{}'::jsonb")
    )

    document: Mapped[KbDocument] = relationship(back_populates="chunks")
