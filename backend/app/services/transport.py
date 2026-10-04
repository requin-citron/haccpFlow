from __future__ import annotations

import uuid
from datetime import time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models.transport import Transport

#: Fields covered by the readings audit.
TRANSPORT_READING_FIELDS = (
    "departure_time",
    "departure_temperature_celsius",
    "arrival_time",
    "arrival_temperature_celsius",
    "observation",
)


def transport_is_complete(
    *,
    departure_time: time | None,
    departure_temperature_celsius: Decimal | None,
    arrival_time: time | None,
    arrival_temperature_celsius: Decimal | None,
) -> bool:
    return (
        departure_time is not None
        and departure_temperature_celsius is not None
        and arrival_time is not None
        and arrival_temperature_celsius is not None
    )


async def get_active_transport(
    db: AsyncSession,
    transport_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> Transport:
    query = select(Transport).where(
        Transport.id == transport_id,
        Transport.deleted_at.is_(None),
    )
    if for_update:
        query = query.with_for_update()
    transport = await db.scalar(query)
    if transport is None:
        raise ApiError(404, "transport_not_found", "Transport not found")
    return transport
