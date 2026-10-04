from __future__ import annotations

from datetime import time
from decimal import Decimal

from app.services.transport import transport_is_complete


def _complete(**overrides: object) -> bool:
    values: dict[str, object] = {
        "departure_time": time(8, 0),
        "departure_temperature_celsius": Decimal("3.00"),
        "arrival_time": time(10, 30),
        "arrival_temperature_celsius": Decimal("4.00"),
    }
    values.update(overrides)
    return transport_is_complete(**values)  # type: ignore[arg-type]


def test_a_transport_is_complete_with_both_checkpoints() -> None:
    assert _complete() is True


def test_a_transport_missing_a_departure_is_incomplete() -> None:
    assert _complete(departure_time=None) is False
    assert _complete(departure_temperature_celsius=None) is False
    assert _complete(arrival_time=None) is False
    assert _complete(arrival_temperature_celsius=None) is False


def test_an_observation_alone_does_not_complete_a_transport() -> None:
    assert (
        _complete(
            departure_time=None,
            departure_temperature_celsius=None,
            arrival_time=None,
            arrival_temperature_celsius=None,
        )
        is False
    )
