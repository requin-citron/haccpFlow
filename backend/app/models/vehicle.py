from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Vehicle(TimestampMixin, Base):
    """A vehicle used for transports: a readable name and/or a plate number."""

    __tablename__ = "vehicles"
    __table_args__ = (
        # A name and a plate are unique among active vehicles only, and a null
        # value stays out of the index.
        Index(
            "uq_vehicles_name_active",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND name IS NOT NULL"),
        ),
        Index(
            "uq_vehicles_plate_active",
            text("lower(plate)"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND plate IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    plate: Mapped[str | None] = mapped_column(String(32), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
