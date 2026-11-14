"""Declarative base, naming convention and shared column helpers."""

import datetime as dt
import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, MetaData, String, Uuid, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Deterministic constraint names so Alembic migrations can reference (and drop) them.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def uuid_pk() -> Mapped[uuid.UUID]:
    """UUID v4 primary key, generated in Python and (for raw SQL inserts) by Postgres."""
    return mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )


def created_at() -> Mapped[dt.datetime]:
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def enum_column(enum_cls: type[StrEnum], column_name: str | None = None, **kwargs: Any) -> Mapped:
    """Text column holding a StrEnum value; pair with enum_check() in __table_args__."""
    length = max(len(m.value) for m in enum_cls)
    if column_name is not None:
        return mapped_column(column_name, String(length), **kwargs)
    return mapped_column(String(length), **kwargs)


def enum_check(column: str, enum_cls: type[StrEnum]) -> CheckConstraint:
    values = ", ".join(f"'{m.value}'" for m in enum_cls)
    return CheckConstraint(f"{column} IN ({values})", name=f"{column}_valid")
