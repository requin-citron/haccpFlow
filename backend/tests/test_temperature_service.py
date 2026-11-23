from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.errors import ApiError
from app.models.temperature_reading import ReadingSlot, ReadingSource, TemperatureReading
from app.schemas.temperature_reading import TemperatureReadingWrite
from app.services.temperature import (
    as_celsius,
    effective_compliance,
    effective_source,
    effective_temperature,
    evaluate_compliance,
    requested_slots,
    resolve_range,
    validate_reading_date,
)


def test_as_celsius_quantizes_to_two_decimals() -> None:
    assert as_celsius(-18) == Decimal("-18.00")
    assert as_celsius(3.456) == Decimal("3.46")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("0.00"), True),
        (Decimal("4.00"), True),
        (Decimal("2.50"), True),
        (Decimal("-0.01"), False),
        (Decimal("4.01"), False),
    ],
)
def test_evaluate_compliance_at_the_bounds(value: Decimal, expected: bool) -> None:
    assert evaluate_compliance(value, Decimal("0.00"), Decimal("4.00")) is expected


def test_requested_slots_keeps_only_provided_values() -> None:
    assert requested_slots(TemperatureReadingWrite(morning_celsius=3)) == {
        ReadingSlot.MORNING: Decimal("3.00")
    }
    assert requested_slots(TemperatureReadingWrite(evening_celsius=-19)) == {
        ReadingSlot.EVENING: Decimal("-19.00")
    }
    assert requested_slots(TemperatureReadingWrite(morning_celsius=3, evening_celsius=5)) == {
        ReadingSlot.MORNING: Decimal("3.00"),
        ReadingSlot.EVENING: Decimal("5.00"),
    }
    assert requested_slots(TemperatureReadingWrite()) == {}


def _reading(**overrides: object) -> TemperatureReading:
    values: dict[str, object] = {
        "equipment_id": "00000000-0000-0000-0000-000000000001",
        "reading_date": date(2026, 11, 23),
        "slot": ReadingSlot.MORNING,
        "temperature_celsius": Decimal("2.00"),
        "is_compliant": True,
        "source": ReadingSource.SENSOR,
        "recorded_at": datetime(2026, 11, 23, 8, tzinfo=UTC),
    }
    values.update(overrides)
    return TemperatureReading(**values)


def test_effective_temperature_uses_the_final_correction() -> None:
    original = _reading()
    corrected = _reading(corrected_temperature_celsius=Decimal("4.00"))

    assert effective_temperature(original) == Decimal("2.00")
    assert effective_temperature(corrected) == Decimal("4.00")


def test_effective_compliance_uses_the_frozen_correction_value() -> None:
    original = _reading()
    corrected = _reading(corrected_is_compliant=False)

    assert effective_compliance(original) is True
    assert effective_compliance(corrected) is False


def test_a_human_correction_makes_the_effective_source_manual() -> None:
    original = _reading()
    corrected = _reading(corrected_at=datetime(2026, 11, 23, 9, tzinfo=UTC))

    assert effective_source(original) is ReadingSource.SENSOR
    assert effective_source(corrected) is ReadingSource.MANUAL


def test_justifications_are_trimmed_and_blank_values_are_ignored() -> None:
    provided = TemperatureReadingWrite(
        morning_justification="  Thermomètre déplacé  ",
        evening_justification="   ",
    )

    assert provided.morning_justification == "Thermomètre déplacé"
    assert provided.evening_justification is None


def test_a_justification_longer_than_the_limit_is_rejected() -> None:
    with pytest.raises(ValueError):
        TemperatureReadingWrite(morning_justification="x" * 2001)


def test_validate_reading_date_accepts_past_today_and_tomorrow() -> None:
    today = date(2026, 10, 3)

    validate_reading_date(today - timedelta(days=30), today=today)
    validate_reading_date(today, today=today)
    validate_reading_date(today + timedelta(days=1), today=today)


def test_validate_reading_date_rejects_beyond_tomorrow() -> None:
    today = date(2026, 10, 3)

    with pytest.raises(ApiError) as excinfo:
        validate_reading_date(today + timedelta(days=2), today=today)

    assert excinfo.value.status_code == 422
    assert excinfo.value.code == "reading_date_out_of_range"


def test_resolve_range_defaults_to_the_last_seven_days() -> None:
    today = date(2026, 10, 3)

    assert resolve_range(None, None, today=today) == (date(2026, 9, 27), today)


def test_resolve_range_accepts_an_explicit_window() -> None:
    assert resolve_range(date(2026, 1, 5), date(2026, 1, 8)) == (
        date(2026, 1, 5),
        date(2026, 1, 8),
    )


def test_resolve_range_rejects_inverted_and_too_wide_windows() -> None:
    with pytest.raises(ApiError) as inverted:
        resolve_range(date(2026, 10, 5), date(2026, 10, 1))
    assert inverted.value.code == "reading_range_invalid"

    with pytest.raises(ApiError) as too_wide:
        resolve_range(date(2024, 1, 1), date(2026, 1, 1))
    assert too_wide.value.code == "reading_range_too_wide"
