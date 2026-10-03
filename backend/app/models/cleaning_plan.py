from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, enum_values


class CleaningFrequency(enum.StrEnum):
    AFTER_EACH_USE = "after_each_use"
    DAILY = "daily"
    WEEKLY = "weekly"


class CleaningStatus(enum.StrEnum):
    """Computed status of a scheduled cleaning plan (never stored)."""

    OVERDUE = "overdue"
    DUE_TODAY = "due_today"
    UPCOMING = "upcoming"


class CleaningRecordEditAction(enum.StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"


class CleaningPlan(TimestampMixin, Base):
    """A cleaning and disinfection plan entry: a zone or a piece of equipment."""

    __tablename__ = "cleaning_plans"
    __table_args__ = (
        Index(
            "uq_cleaning_plans_name_active",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    frequency: Mapped[CleaningFrequency] = mapped_column(
        Enum(
            CleaningFrequency,
            name="cleaning_frequency",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    products: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CleaningRecord(TimestampMixin, Base):
    """A declared cleaning: it happened on that day, whatever the frequency."""

    __tablename__ = "cleaning_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cleaning_plans.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    cleaning_date: Mapped[date] = mapped_column(Date, nullable=False)
    comment: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    performed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CleaningRecordEdit(Base):
    """Audit trail: every change applied to a declared cleaning."""

    __tablename__ = "cleaning_record_edits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cleaning_records.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    action: Mapped[CleaningRecordEditAction] = mapped_column(
        Enum(
            CleaningRecordEditAction,
            name="cleaning_record_edit_action",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    previous_cleaning_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    new_cleaning_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    previous_comment: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    new_comment: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
