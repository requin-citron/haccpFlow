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
    Integer,
    Numeric,
    String,
    Time,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, enum_values


class PasteurisationPhase(enum.StrEnum):
    """Phases of a pasteurisation run, in their canonical order."""

    PREHEATING = "preheating"
    HOLDING = "holding"
    COOLING = "cooling"


class PasteurisationPhaseEditAction(enum.StrEnum):
    CREATED = "created"
    UPDATED = "updated"


class PasteurisationBatch(TimestampMixin, Base):
    """One pasteurised production lot."""

    __tablename__ = "pasteurisation_batches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    batch_date: Mapped[date] = mapped_column(Date, nullable=False)
    product_name: Mapped[str] = mapped_column(String(160), nullable=False)
    # Not unique: a lot may legitimately be pasteurised twice.
    lot_number: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PasteurisationPhaseRecord(TimestampMixin, Base):
    """Values recorded for one phase of one batch.

    Phases are rows, not columns: adding a phase later only needs a new enum
    value, everything else iterates over the enum.
    """

    __tablename__ = "pasteurisation_phases"
    __table_args__ = (UniqueConstraint("batch_id", "phase", name="uq_pasteurisation_phases_slot"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pasteurisation_batches.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    phase: Mapped[PasteurisationPhase] = mapped_column(
        Enum(
            PasteurisationPhase,
            name="pasteurisation_phase",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    # Local wall-clock times on the batch day, not UTC instants.
    started_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    ended_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    target_temperature_celsius: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    observation: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class PasteurisationPhaseEdit(Base):
    """Audit trail: every change applied to a phase."""

    __tablename__ = "pasteurisation_phase_edits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    phase_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pasteurisation_phases.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    action: Mapped[PasteurisationPhaseEditAction] = mapped_column(
        Enum(
            PasteurisationPhaseEditAction,
            name="pasteurisation_phase_edit_action",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    previous_started_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    new_started_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    previous_ended_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    new_ended_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    previous_target_temperature_celsius: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    new_target_temperature_celsius: Mapped[Decimal | None] = mapped_column(
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
