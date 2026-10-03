from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.core.errors import ApiError
from app.models.temperature_reading import ReadingSlot
from app.schemas.temperature_reading import TemperatureReadingWrite
from app.services.temperature import (
    as_celsius,
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
