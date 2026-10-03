from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.core.errors import ApiError
from app.models.equipment import EquipmentType
from app.schemas.equipment import EquipmentWrite
from app.services.equipment import resolve_thresholds


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "secret_key": "unit-test-secret",
        "database_url": "postgresql+asyncpg://user:pass@localhost:5432/db",
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)


def test_resolve_keeps_explicit_thresholds() -> None:
    payload = EquipmentWrite(
        name="Frigo",
        type=EquipmentType.FRIDGE,
        min_temperature_celsius=1.5,
        max_temperature_celsius=3,
    )

    assert resolve_thresholds(payload, _settings()) == (Decimal("1.50"), Decimal("3.00"))


def test_resolve_uses_fridge_defaults() -> None:
    payload = EquipmentWrite(name="Frigo", type=EquipmentType.FRIDGE)
    settings = _settings(
        default_fridge_min_temperature_c=2,
        default_fridge_max_temperature_c=6,
    )

    assert resolve_thresholds(payload, settings) == (Decimal("2.00"), Decimal("6.00"))


def test_resolve_uses_freezer_defaults() -> None:
    payload = EquipmentWrite(name="Congelateur", type=EquipmentType.FREEZER)
    settings = _settings(
        default_freezer_min_temperature_c=-24,
        default_freezer_max_temperature_c=-18,
    )

    assert resolve_thresholds(payload, settings) == (Decimal("-24.00"), Decimal("-18.00"))


def test_resolve_rejects_inconsistent_default_configuration() -> None:
    payload = EquipmentWrite(name="Frigo", type=EquipmentType.FRIDGE)
    settings = _settings(
        default_fridge_min_temperature_c=6,
        default_fridge_max_temperature_c=2,
    )

    with pytest.raises(ApiError) as excinfo:
        resolve_thresholds(payload, settings)

    assert excinfo.value.status_code == 500
    assert excinfo.value.code == "invalid_threshold_configuration"


def test_payload_rejects_a_single_threshold() -> None:
    with pytest.raises(ValidationError):
        EquipmentWrite(name="Frigo", type=EquipmentType.FRIDGE, min_temperature_celsius=1)


def test_payload_rejects_min_above_max() -> None:
    with pytest.raises(ValidationError):
        EquipmentWrite(
            name="Frigo",
            type=EquipmentType.FRIDGE,
            min_temperature_celsius=5,
            max_temperature_celsius=1,
        )


def test_payload_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        EquipmentWrite(name="   ", type=EquipmentType.FRIDGE)


def test_payload_trims_text_and_blanks_optional_fields() -> None:
    payload = EquipmentWrite(
        name="  Frigo cuisine  ",
        type=EquipmentType.FRIDGE,
        location="   ",
        notes="  sous le plan de travail  ",
    )

    assert payload.name == "Frigo cuisine"
    assert payload.location is None
    assert payload.notes == "sous le plan de travail"


def test_payload_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        EquipmentWrite(name="Frigo", type=EquipmentType.FRIDGE, unexpected="nope")  # type: ignore[call-arg]
