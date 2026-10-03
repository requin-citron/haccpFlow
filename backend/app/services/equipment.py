from __future__ import annotations

from decimal import Decimal
from typing import assert_never

from app.config import Settings
from app.core.errors import ApiError
from app.models.equipment import EquipmentType
from app.schemas.equipment import EquipmentWrite

_TWO_DECIMALS = Decimal("0.01")


def as_celsius(value: float) -> Decimal:
    """Convert an API value to the NUMERIC(5,2) stored in the database."""

    return Decimal(str(value)).quantize(_TWO_DECIMALS)


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
