from __future__ import annotations

from datetime import time
from decimal import Decimal

import pytest

from app.models.pasteurisation import PasteurisationPhase
from app.services.pasteurisation import (
    PHASE_ORDER,
    compute_duration_minutes,
    phase_is_complete,
    phase_is_filled,
)


def test_phases_are_declared_in_run_order() -> None:
    assert PHASE_ORDER == (
        PasteurisationPhase.PREHEATING,
        PasteurisationPhase.HOLDING,
        PasteurisationPhase.COOLING,
    )


@pytest.mark.parametrize(
    ("started_at", "ended_at", "expected"),
    [
        (None, None, None),
        (time(9, 0), None, None),
        (None, time(10, 0), None),
        (time(9, 0), time(10, 30), 90),
        (time(8, 15), time(8, 45), 30),
        (time(10, 0), time(10, 0), None),
        (time(10, 0), time(9, 0), None),
    ],
)
def test_duration_is_derived_from_the_times(
    started_at: time | None,
    ended_at: time | None,
    expected: int | None,
) -> None:
    assert compute_duration_minutes(started_at, ended_at) == expected


def test_a_phase_is_filled_as_soon_as_one_value_exists() -> None:
    assert not phase_is_filled(
        started_at=None,
        ended_at=None,
        target_temperature_celsius=None,
        observation=None,
    )
    assert phase_is_filled(
        started_at=time(9, 0),
        ended_at=None,
        target_temperature_celsius=None,
        observation=None,
    )
    assert phase_is_filled(
        started_at=None,
        ended_at=None,
        target_temperature_celsius=None,
        observation="RAS",
    )


def test_a_phase_is_complete_only_with_times_and_target() -> None:
    assert not phase_is_complete(
        started_at=time(9, 0),
        ended_at=None,
        target_temperature_celsius=Decimal("85.00"),
    )
    assert not phase_is_complete(
        started_at=time(9, 0),
        ended_at=time(9, 30),
        target_temperature_celsius=None,
    )
    assert phase_is_complete(
        started_at=time(9, 0),
        ended_at=time(9, 30),
        target_temperature_celsius=Decimal("85.00"),
    )
