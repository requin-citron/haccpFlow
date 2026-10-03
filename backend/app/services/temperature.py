from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.core.errors import ApiError
from app.models.temperature_reading import ReadingSlot
from app.schemas.temperature_reading import TemperatureReadingWrite

MAX_FUTURE_DAYS = 1
DEFAULT_RANGE_DAYS = 7
MAX_RANGE_DAYS = 366

_TWO_DECIMALS = Decimal("0.01")


def as_celsius(value: float) -> Decimal:
    """Convert an API value to the NUMERIC(5,2) stored in the database."""

    return Decimal(str(value)).quantize(_TWO_DECIMALS)


def evaluate_compliance(value: Decimal, minimum: Decimal, maximum: Decimal) -> bool:
    """A reading is compliant when it sits inside the equipment thresholds."""

    return minimum <= value <= maximum


def requested_slots(payload: TemperatureReadingWrite) -> dict[ReadingSlot, Decimal]:
    """Map the payload to the slots it actually carries a value for."""

    slots: dict[ReadingSlot, Decimal] = {}
    if payload.morning_celsius is not None:
        slots[ReadingSlot.MORNING] = as_celsius(payload.morning_celsius)
    if payload.evening_celsius is not None:
        slots[ReadingSlot.EVENING] = as_celsius(payload.evening_celsius)
    return slots


def validate_reading_date(reading_date: date, *, today: date | None = None) -> None:
    """Reject dates clearly in the future, tolerating one day of timezone skew."""

    limit = (today or datetime.now(UTC).date()) + timedelta(days=MAX_FUTURE_DAYS)
    if reading_date > limit:
        raise ApiError(
            422,
            "reading_date_out_of_range",
            f"A reading date cannot be later than {limit.isoformat()}",
        )


def resolve_range(
    from_date: date | None,
    to_date: date | None,
    *,
    today: date | None = None,
) -> tuple[date, date]:
    """Resolve an inclusive date range, defaulting to the last seven days."""

    end = to_date or (today or datetime.now(UTC).date())
    start = from_date or end - timedelta(days=DEFAULT_RANGE_DAYS - 1)
    if start > end:
        raise ApiError(422, "reading_range_invalid", "'from' must not be after 'to'")
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise ApiError(
            422,
            "reading_range_too_wide",
            f"A range cannot exceed {MAX_RANGE_DAYS} days",
        )
    return start, end
