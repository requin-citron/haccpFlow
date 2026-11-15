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
    "initial_time",
    "initial_temperature_celsius",
    "in_progress_time",
    "in_progress_temperature_celsius",
    "observation",
)


def transport_is_complete(
    *,
    initial_time: time | None,
    initial_temperature_celsius: Decimal | None,
    in_progress_time: time | None,
    in_progress_temperature_celsius: Decimal | None,
) -> bool:
    return (
        initial_time is not None
        and initial_temperature_celsius is not None
        and in_progress_time is not None
        and in_progress_temperature_celsius is not None
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
