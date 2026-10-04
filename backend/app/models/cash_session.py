from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, enum_values


class CashExpenseKind(enum.StrEnum):
    """Who the money was taken out for: the business or the owner."""

    PROFESSIONAL = "professional"
    PERSONAL = "personal"


class CashSession(TimestampMixin, Base):
    """One tracking period of a cash register.

    The session keeps its own copy of the opening float, so a later closing
    count never rewrites history. ``closed_at`` also tells whether it is open.
    """

    __tablename__ = "cash_sessions"
    __table_args__ = (
        # At most one open session per register: the previous one has to be
        # closed before another one can be opened.
        Index(
            "uq_cash_sessions_open_per_register",
            "cash_register_id",
            unique=True,
            postgresql_where=text("closed_at IS NULL AND deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cash_register_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cash_registers.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False)

    coins_1_cent: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    coins_2_cent: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    coins_5_cent: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    coins_10_cent: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    coins_20_cent: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    coins_50_cent: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    coins_1_euro: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    coins_2_euro: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    notes_5_euro: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    notes_10_euro: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    notes_20_euro: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    notes_50_euro: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    # Null until the register is counted again at closing time.
    closed_coins_1_cent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closed_coins_2_cent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closed_coins_5_cent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closed_coins_10_cent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closed_coins_20_cent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closed_coins_50_cent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closed_coins_1_euro: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closed_coins_2_euro: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closed_notes_5_euro: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closed_notes_10_euro: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closed_notes_20_euro: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closed_notes_50_euro: Mapped[int | None] = mapped_column(Integer, nullable=True)

    opened_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    closed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CashExpense(TimestampMixin, Base):
    """Money taken out of the till while a session is open."""

    __tablename__ = "cash_expenses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cash_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    kind: Mapped[CashExpenseKind] = mapped_column(
        Enum(
            CashExpenseKind,
            name="cash_expense_kind",
            native_enum=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    #: Unit price, in cents, as actually paid (VAT included).
    unit_price_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    #: VAT rate, as a percentage: kept for the record, never used to recompute.
    vat_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, server_default=text("0")
    )
