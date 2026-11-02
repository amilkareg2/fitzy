import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, created_at, enum_check, enum_column, uuid_pk
from app.models.enums import Unit


class User(Base):
    # "user" is a reserved word in Postgres.
    __tablename__ = "app_user"
    __table_args__ = (enum_check("unit_pref", Unit),)

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    unit_pref: Mapped[str] = enum_column(Unit, nullable=False, default=Unit.KG, server_default="kg")
    created_at: Mapped[dt.datetime] = created_at()


class BodyWeightLog(Base):
    __tablename__ = "body_weight_log"
    __table_args__ = (
        UniqueConstraint("user_id", "date"),
        CheckConstraint("weight_kg > 0", name="weight_kg_positive"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(7, 3), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, server_default="app")
