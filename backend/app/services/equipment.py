from __future__ import annotations

import uuid
from decimal import Decimal
from typing import assert_never

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.errors import ApiError
from app.models.equipment import Equipment, EquipmentType
from app.schemas.equipment import EquipmentWrite
from app.services.temperature import as_celsius


async def get_active_equipment(
    db: AsyncSession,
    equipment_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> Equipment:
    query = select(Equipment).where(
        Equipment.id == equipment_id,
        Equipment.deleted_at.is_(None),
    )
    if for_update:
        query = query.with_for_update()
    equipment = await db.scalar(query)
    if equipment is None:
        raise ApiError(404, "equipment_not_found", "Equipment not found")
    return equipment


def resolve_thresholds(payload: EquipmentWrite, settings: Settings) -> tuple[Decimal, Decimal]:
    """Return the thresholds to persist: explicit values, or the per-type defaults."""

    if payload.min_temperature_celsius is not None and payload.max_temperature_celsius is not None:
        minimum = as_celsius(payload.min_temperature_celsius)
        maximum = as_celsius(payload.max_temperature_celsius)
    else:
        match payload.type:
            case EquipmentType.FRIDGE:
                minimum = as_celsius(settings.default_fridge_min_temperature_c)
                maximum = as_celsius(settings.default_fridge_max_temperature_c)
            case EquipmentType.FREEZER:
                minimum = as_celsius(settings.default_freezer_min_temperature_c)
                maximum = as_celsius(settings.default_freezer_max_temperature_c)
            case _ as unreachable:
                assert_never(unreachable)

    if minimum >= maximum:
        raise ApiError(
            500,
            "invalid_threshold_configuration",
            "The configured default thresholds are inconsistent",
        )
    return minimum, maximum
