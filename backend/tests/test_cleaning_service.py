from __future__ import annotations

from datetime import date

import pytest

from app.models.cleaning_plan import CleaningFrequency, CleaningStatus
from app.services.cleaning import next_due_date, schedule_status


def test_after_each_use_is_never_scheduled() -> None:
    assert (
        next_due_date(CleaningFrequency.AFTER_EACH_USE, date(2026, 10, 3), date(2026, 9, 1)) is None
    )
    assert next_due_date(CleaningFrequency.AFTER_EACH_USE, None, date(2026, 9, 1)) is None


def test_a_never_cleaned_plan_is_due_since_its_creation() -> None:
    assert next_due_date(CleaningFrequency.DAILY, None, date(2026, 10, 3)) == date(2026, 10, 3)
    assert next_due_date(CleaningFrequency.WEEKLY, None, date(2026, 10, 3)) == date(2026, 10, 3)


def test_daily_plan_is_due_the_day_after_the_last_cleaning() -> None:
    assert next_due_date(CleaningFrequency.DAILY, date(2026, 10, 3), date(2026, 9, 1)) == date(
        2026, 10, 4
    )


def test_weekly_plan_is_due_seven_days_after_the_last_cleaning() -> None:
    assert next_due_date(CleaningFrequency.WEEKLY, date(2026, 10, 3), date(2026, 9, 1)) == date(
        2026, 10, 10
    )


@pytest.mark.parametrize(
    ("due", "on_date", "expected_status", "expected_days_late"),
    [
        (date(2026, 10, 1), date(2026, 10, 3), CleaningStatus.OVERDUE, 2),
        (date(2026, 10, 3), date(2026, 10, 3), CleaningStatus.DUE_TODAY, 0),
        (date(2026, 10, 5), date(2026, 10, 3), CleaningStatus.UPCOMING, 0),
    ],
)
def test_schedule_status(
    due: date,
    on_date: date,
    expected_status: CleaningStatus,
    expected_days_late: int,
) -> None:
    assert schedule_status(due, on_date) == (expected_status, expected_days_late)
