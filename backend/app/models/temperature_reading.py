from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, enum_values


class ReadingSlot(enum.StrEnum):
    MORNING = "morning"
    EVENING = "evening"


class ReadingSource(enum.StrEnum):
    MANUAL = "manual"
    SENSOR = "sensor"


class ReadingEditAction(enum.StrEnum):
    CREATED = "created"
    UPDATED = "updated"


class TemperatureReading(TimestampMixin, Base):
    """One temperature value for one equipment, one day and one slot."""

    __tablename__ = "temperature_readings"
    __table_args__ = (
        UniqueConstraint(
            "equipment_id",
            "reading_date",
            "slot",
            name="uq_temperature_readings_slot",
        ),
        CheckConstraint(
            """
            (
                corrected_at IS NULL
                AND corrected_temperature_celsius IS NULL
                AND corrected_is_compliant IS NULL
                AND correction_justification IS NULL
                AND corrected_by IS NULL
            )
            OR
            (
                corrected_at IS NOT NULL
                AND corrected_temperature_celsius IS NOT NULL
                AND corrected_is_compliant IS NOT NULL
                AND correction_justification IS NOT NULL
                AND btrim(correction_justification) <> ''
            )
            """,
            name="ck_temperature_readings_correction_complete",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # Calendar day as sent by the client, not derived from UTC.
    reading_date: Mapped[date] = mapped_column(Date, nullable=False)
    slot: Mapped[ReadingSlot] = mapped_column(
        Enum(
            ReadingSlot,
            name="reading_slot",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    temperature_celsius: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    # Frozen at write time so the history does not move when thresholds change.
    is_compliant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source: Mapped[ReadingSource] = mapped_column(
        Enum(
            ReadingSource,
            name="reading_source",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=ReadingSource.MANUAL,
    )
    # When the measurement was taken: set once, never moved by an edit.
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # The initial author is kept separately so creation remains auditable
    # without writing an event row to the legacy edits table.
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # One optional final correction lives on the slot row itself. A later
    # correction overwrites these values; the original measurement above stays
    # immutable.
    corrected_temperature_celsius: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    corrected_is_compliant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    correction_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    corrected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class TemperatureReadingEdit(Base):
    """Legacy audit trail retained for pre-migration correction history."""

    __tablename__ = "temperature_reading_edits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    reading_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("temperature_readings.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    action: Mapped[ReadingEditAction] = mapped_column(
        Enum(
            ReadingEditAction,
            name="reading_edit_action",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    previous_celsius: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    new_celsius: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
