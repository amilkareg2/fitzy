import datetime as dt
import uuid
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class ImportRun(Base):
    __tablename__ = "import_run"
    __table_args__ = (
        CheckConstraint("rows_read >= 0 AND rows_loaded >= 0", name="row_counts_non_negative"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    source: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. 'fitnotes_csv'
    file_name: Mapped[str | None] = mapped_column(String(255))
    rows_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    rows_loaded: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    issues: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
