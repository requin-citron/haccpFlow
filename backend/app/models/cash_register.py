from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

#: Counted denominations, as (column name, value in cents). The order is the
#: one used everywhere, from the columns to the total computation.
DENOMINATIONS: tuple[tuple[str, int], ...] = (
    ("coins_1_cent", 1),
    ("coins_2_cent", 2),
    ("coins_5_cent", 5),
    ("coins_10_cent", 10),
    ("coins_20_cent", 20),
    ("coins_50_cent", 50),
    ("coins_1_euro", 100),
    ("coins_2_euro", 200),
    ("notes_5_euro", 500),
    ("notes_10_euro", 1000),
    ("notes_20_euro", 2000),
    ("notes_50_euro", 5000),
)

DENOMINATION_FIELDS: tuple[str, ...] = tuple(name for name, _ in DENOMINATIONS)


class CashRegister(TimestampMixin, Base):
    """A cash register, enrolled with the count of its opening float."""

    __tablename__ = "cash_registers"
    __table_args__ = (
        Index(
            "uq_cash_registers_name_active",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

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

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
