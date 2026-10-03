from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def enum_values(enum_class: type[enum.Enum]) -> list[str]:
    """Use member values (lowercase) as database labels, not member names."""

    return [str(member.value) for member in enum_class]


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """UTC timestamps maintained by the database."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
