from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.core.errors import ApiError

# Tolerate one day of timezone skew between the client and the server.
MAX_FUTURE_DAYS = 1


def ensure_not_in_the_future(
    value: date,
    *,
    code: str,
    today: date | None = None,
) -> None:
    """Reject dates clearly in the future, tolerating one day of skew."""

    limit = (today or datetime.now(UTC).date()) + timedelta(days=MAX_FUTURE_DAYS)
    if value > limit:
        raise ApiError(422, code, f"A date cannot be later than {limit.isoformat()}")
