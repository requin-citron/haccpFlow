from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

EQUIPMENT_URL = "/api/v1/equipment"


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def _create_equipment(
    api_client: TestClient,
    headers: dict[str, str],
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Frigo relevés",
        "type": "fridge",
        "min_temperature_celsius": 0,
        "max_temperature_celsius": 4,
    }
    payload.update(overrides)
    response = api_client.post(EQUIPMENT_URL, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _readings_url(equipment_id: str, reading_date: str | None = None) -> str:
    base = f"{EQUIPMENT_URL}/{equipment_id}/readings"
    return base if reading_date is None else f"{base}/{reading_date}"


def test_morning_can_be_completed_with_evening_later(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    equipment = _create_equipment(api_client, admin_headers)
    url = _readings_url(equipment["id"], _today())

    first = api_client.put(url, json={"morning_celsius": 2.5}, headers=admin_headers)
    assert first.status_code == 200
    assert first.json()["morning"]["temperature_celsius"] == 2.5
    assert first.json()["evening"] is None

    second = api_client.put(url, json={"evening_celsius": 3.5}, headers=admin_headers)
    assert second.status_code == 200
    assert second.json()["morning"]["temperature_celsius"] == 2.5
    assert second.json()["evening"]["temperature_celsius"] == 3.5


def test_evening_can_be_completed_with_morning_later(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    equipment = _create_equipment(api_client, admin_headers)
    url = _readings_url(equipment["id"], _today())

    api_client.put(url, json={"evening_celsius": 3}, headers=admin_headers)
    response = api_client.put(url, json={"morning_celsius": 1}, headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["morning"]["temperature_celsius"] == 1
    assert response.json()["evening"]["temperature_celsius"] == 3


def test_both_slots_can_be_sent_at_once(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    equipment = _create_equipment(api_client, admin_headers)

    response = api_client.put(
        _readings_url(equipment["id"], _today()),
        json={"morning_celsius": 1, "evening_celsius": 3},
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["morning"]["temperature_celsius"] == 1
    assert body["evening"]["temperature_celsius"] == 3
    assert body["morning"]["source"] == "manual"


def test_update_records_the_previous_value_in_the_history(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    equipment = _create_equipment(api_client, admin_headers)
    url = _readings_url(equipment["id"], _today())
    api_client.put(url, json={"morning_celsius": 2}, headers=admin_headers)

    response = api_client.put(url, json={"morning_celsius": 3.5}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["morning"]["temperature_celsius"] == 3.5

    history = api_client.get(f"{url}/history", headers=admin_headers)
    assert history.status_code == 200
    entries = history.json()
    assert [entry["action"] for entry in entries] == ["updated", "created"]
    assert entries[0]["slot"] == "morning"
    assert entries[0]["previous_celsius"] == 2
    assert entries[0]["new_celsius"] == 3.5
    assert entries[0]["changed_by_email"] == "admin@test.local"
    assert entries[0]["changed_at"]
    assert entries[1]["previous_celsius"] is None


def test_rewriting_the_same_value_adds_no_audit_line(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    equipment = _create_equipment(api_client, admin_headers)
    url = _readings_url(equipment["id"], _today())
    api_client.put(url, json={"morning_celsius": 2}, headers=admin_headers)

    response = api_client.put(url, json={"morning_celsius": 2}, headers=admin_headers)

    assert response.status_code == 200
    history = api_client.get(f"{url}/history", headers=admin_headers).json()
    assert [entry["action"] for entry in history] == ["created"]


def test_compliance_is_frozen_when_the_reading_is_recorded(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    equipment = _create_equipment(api_client, admin_headers)

    response = api_client.put(
        _readings_url(equipment["id"], _today()),
        json={"morning_celsius": 8, "evening_celsius": 2},
        headers=admin_headers,
    )

    body = response.json()
    assert body["morning"]["is_compliant"] is False
    assert body["evening"]["is_compliant"] is True


def test_compliance_is_recomputed_when_a_reading_is_edited(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    equipment = _create_equipment(api_client, admin_headers)
    url = _readings_url(equipment["id"], _today())
    api_client.put(url, json={"morning_celsius": 2}, headers=admin_headers)

    response = api_client.put(url, json={"morning_celsius": 9}, headers=admin_headers)

    assert response.json()["morning"]["is_compliant"] is False


def test_a_past_date_can_be_filled_in(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    equipment = _create_equipment(api_client, admin_headers)
    yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()

    response = api_client.put(
        _readings_url(equipment["id"], yesterday),
        json={"morning_celsius": 1, "evening_celsius": 2},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["reading_date"] == yesterday


@pytest.mark.parametrize(("offset", "expected"), [(0, 200), (1, 200), (2, 422)])
def test_future_dates_are_tolerated_up_to_one_day(
    api_client: TestClient,
    admin_headers: dict[str, str],
    offset: int,
    expected: int,
) -> None:
    equipment = _create_equipment(api_client, admin_headers)
    target = (datetime.now(UTC).date() + timedelta(days=offset)).isoformat()

    response = api_client.put(
        _readings_url(equipment["id"], target),
        json={"morning_celsius": 1},
        headers=admin_headers,
    )

    assert response.status_code == expected
    if expected == 422:
        assert response.json()["code"] == "reading_date_out_of_range"


@pytest.mark.parametrize("payload", [{}, {"morning_celsius": None}, {"evening_celsius": None}])
def test_a_payload_without_any_value_is_rejected(
    api_client: TestClient,
    admin_headers: dict[str, str],
    payload: dict[str, Any],
) -> None:
    equipment = _create_equipment(api_client, admin_headers)

    response = api_client.put(
        _readings_url(equipment["id"], _today()),
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "reading_value_required"


def test_a_physically_impossible_temperature_is_rejected(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    equipment = _create_equipment(api_client, admin_headers)

    response = api_client.put(
        _readings_url(equipment["id"], _today()),
        json={"morning_celsius": -300},
        headers=admin_headers,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_an_empty_day_is_not_an_error(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    equipment = _create_equipment(api_client, admin_headers)

    response = api_client.get(
        _readings_url(equipment["id"], _today()),
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json() == {"reading_date": _today(), "morning": None, "evening": None}


def test_unknown_equipment_returns_404(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    url = _readings_url(str(uuid.uuid4()), _today())

    assert api_client.get(url, headers=admin_headers).status_code == 404
    assert (
        api_client.put(url, json={"morning_celsius": 1}, headers=admin_headers).status_code == 404
    )


def test_soft_deleted_equipment_returns_404(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    equipment = _create_equipment(api_client, admin_headers)
    api_client.delete(f"{EQUIPMENT_URL}/{equipment['id']}", headers=admin_headers)

    response = api_client.get(_readings_url(equipment["id"], _today()), headers=admin_headers)

    assert response.status_code == 404


def test_range_is_dense_sorted_and_shows_missing_slots(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    equipment = _create_equipment(api_client, admin_headers)
    today = datetime.now(UTC).date()
    yesterday = today - timedelta(days=1)
    api_client.put(
        _readings_url(equipment["id"], yesterday.isoformat()),
        json={"evening_celsius": 1},
        headers=admin_headers,
    )

    response = api_client.get(
        f"{_readings_url(equipment['id'])}?from={yesterday.isoformat()}&to={today.isoformat()}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert [day["reading_date"] for day in body] == [yesterday.isoformat(), today.isoformat()]
    assert body[0]["morning"] is None
    assert body[0]["evening"]["temperature_celsius"] == 1
    assert body[1]["morning"] is None
    assert body[1]["evening"] is None


def test_range_defaults_to_the_last_seven_days(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    equipment = _create_equipment(api_client, admin_headers)

    response = api_client.get(_readings_url(equipment["id"]), headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 7
    assert body[-1]["reading_date"] == _today()


def test_range_rejects_inverted_and_too_wide_windows(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    equipment = _create_equipment(api_client, admin_headers)
    base = _readings_url(equipment["id"])
    today = datetime.now(UTC).date()

    inverted = api_client.get(
        f"{base}?from={today.isoformat()}&to={(today - timedelta(days=1)).isoformat()}",
        headers=admin_headers,
    )
    assert inverted.status_code == 422
    assert inverted.json()["code"] == "reading_range_invalid"

    too_wide = api_client.get(
        f"{base}?from={(today - timedelta(days=400)).isoformat()}&to={today.isoformat()}",
        headers=admin_headers,
    )
    assert too_wide.status_code == 422
    assert too_wide.json()["code"] == "reading_range_too_wide"


def test_operator_can_write_and_read(
    api_client: TestClient, operator_headers: dict[str, str]
) -> None:
    equipment = _create_equipment(api_client, operator_headers)
    url = _readings_url(equipment["id"], _today())

    written = api_client.put(url, json={"morning_celsius": 2}, headers=operator_headers)
    assert written.status_code == 200
    assert api_client.get(url, headers=operator_headers).status_code == 200
    assert api_client.get(f"{url}/history", headers=operator_headers).status_code == 200


def test_readings_require_authentication(api_client: TestClient) -> None:
    url = _readings_url(str(uuid.uuid4()), _today())

    assert api_client.get(url).status_code == 401
    assert api_client.put(url, json={"morning_celsius": 1}).status_code == 401
