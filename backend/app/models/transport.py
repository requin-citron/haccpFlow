from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Time,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, enum_values


class TransportEditAction(enum.StrEnum):
    CREATED = "created"
    UPDATED = "updated"


class Transport(TimestampMixin, Base):
    """One movement of goods, with its cold-chain checkpoints."""

    __tablename__ = "transports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transport_date: Mapped[date] = mapped_column(Date, nullable=False)
    place: Mapped[str] = mapped_column(String(160), nullable=False)
    product_name: Mapped[str] = mapped_column(String(160), nullable=False)
    lot_number: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    # Either a vehicle from the registry, or a free label for a one-off carrier.
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    vehicle_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    departure_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    departure_temperature_celsius: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    arrival_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    arrival_temperature_celsius: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    observation: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TransportEdit(Base):
    """Audit trail: every change applied to a transport's readings."""

    __tablename__ = "transport_edits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    transport_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transports.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    action: Mapped[TransportEditAction] = mapped_column(
        Enum(
            TransportEditAction,
            name="transport_edit_action",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    previous_departure_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    new_departure_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    previous_departure_temperature_celsius: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    new_departure_temperature_celsius: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    previous_arrival_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    new_arrival_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    previous_arrival_temperature_celsius: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    new_arrival_temperature_celsius: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    previous_observation: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    new_observation: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
