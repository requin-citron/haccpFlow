from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, Index, Numeric, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, enum_values


class EquipmentType(enum.StrEnum):
    FRIDGE = "fridge"
    FREEZER = "freezer"


class Equipment(TimestampMixin, Base):
    """A monitored cold unit (fridge, freezer)."""

    __tablename__ = "equipment"
    __table_args__ = (
        # A name is unique among active equipment only, so a deleted unit
        # frees its name while the history stays auditable.
        Index(
            "uq_equipment_name_active",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[EquipmentType] = mapped_column(
        Enum(
            EquipmentType,
            name="equipment_type",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    min_temperature_celsius: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    max_temperature_celsius: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
