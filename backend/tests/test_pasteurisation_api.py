from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

BATCHES = "/api/v1/pasteurisations"


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def _days_ago(days: int) -> str:
    return (datetime.now(UTC).date() - timedelta(days=days)).isoformat()


def _days_ahead(days: int) -> str:
    return (datetime.now(UTC).date() + timedelta(days=days)).isoformat()


def _payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "batch_date": _today(),
        "product_name": "Crème anglaise",
        "lot_number": "LOT-2026-001",
        "quantity": 120,
    }
    payload.update(overrides)
    return payload


def _create(api_client: TestClient, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    response = api_client.post(BATCHES, json=_payload(**overrides), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _phase_url(batch_id: str, phase: str) -> str:
    return f"{BATCHES}/{batch_id}/phases/{phase}"


def _phase(body: dict[str, Any], name: str) -> dict[str, Any]:
    return next(item for item in body["phases"] if item["phase"] == name)


def test_a_new_batch_exposes_three_empty_phases(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    batch = _create(api_client, admin_headers)

    assert batch["lot_number"] == "LOT-2026-001"
    assert batch["quantity"] == 120
    assert [item["phase"] for item in batch["phases"]] == [
        "preheating",
        "holding",
        "cooling",
    ]
    assert all(item["started_at"] is None for item in batch["phases"])
    assert all(item["duration_minutes"] is None for item in batch["phases"])
    assert batch["filled_phases"] == 0
    assert batch["is_complete"] is False


def test_a_phase_is_filled_progressively(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    batch = _create(api_client, admin_headers)
    url = _phase_url(batch["id"], "preheating")

    started = api_client.put(url, json={"started_at": "09:00"}, headers=admin_headers)
    assert started.status_code == 200
    preheating = _phase(started.json(), "preheating")
    assert preheating["started_at"] == "09:00:00"
    assert preheating["ended_at"] is None
    assert preheating["duration_minutes"] is None
    assert started.json()["filled_phases"] == 1

    ended = api_client.put(url, json={"ended_at": "09:30"}, headers=admin_headers)
    preheating = _phase(ended.json(), "preheating")
    assert preheating["started_at"] == "09:00:00"
    assert preheating["ended_at"] == "09:30:00"
    assert preheating["duration_minutes"] == 30

    targeted = api_client.put(url, json={"target_temperature_celsius": 85}, headers=admin_headers)
    preheating = _phase(targeted.json(), "preheating")
    assert preheating["target_temperature_celsius"] == 85
    assert targeted.json()["filled_phases"] == 1
    assert targeted.json()["is_complete"] is False


def test_the_batch_is_complete_once_the_three_phases_are(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    batch = _create(api_client, admin_headers)
    steps = (
        ("preheating", "09:00", "09:30", 85),
        ("holding", "09:30", "10:00", 85),
        ("cooling", "10:00", "10:45", 4),
    )

    response = None
    for phase, start, end, temperature in steps:
        response = api_client.put(
            _phase_url(batch["id"], phase),
            json={
                "started_at": start,
                "ended_at": end,
                "target_temperature_celsius": temperature,
            },
            headers=admin_headers,
        )
        assert response.status_code == 200

    assert response is not None
    body = response.json()
    assert body["filled_phases"] == 3
    assert body["is_complete"] is True
    assert _phase(body, "holding")["duration_minutes"] == 30


def test_a_null_field_clears_the_value(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    batch = _create(api_client, admin_headers)
    url = _phase_url(batch["id"], "holding")
    api_client.put(
        url,
        json={"started_at": "09:30", "observation": "RAS"},
        headers=admin_headers,
    )

    response = api_client.put(url, json={"observation": None}, headers=admin_headers)

    holding = _phase(response.json(), "holding")
    assert holding["observation"] is None
    assert holding["started_at"] == "09:30:00"


def test_corrections_are_audited(api_client: TestClient, admin_headers: dict[str, str]) -> None:
    batch = _create(api_client, admin_headers)
    url = _phase_url(batch["id"], "holding")
    api_client.put(url, json={"started_at": "09:30", "ended_at": "10:00"}, headers=admin_headers)

    api_client.put(url, json={"started_at": "09:45"}, headers=admin_headers)

    history = api_client.get(f"{url}/history", headers=admin_headers)
    assert history.status_code == 200
    entries = history.json()
    assert [entry["action"] for entry in entries] == ["updated", "created"]
    assert entries[0]["previous_started_at"] == "09:30:00"
    assert entries[0]["new_started_at"] == "09:45:00"
    assert entries[0]["new_ended_at"] == "10:00:00"
    assert entries[0]["changed_by_email"] == "admin@test.local"
    assert entries[1]["previous_started_at"] is None


def test_rewriting_the_same_value_adds_no_audit_line(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    batch = _create(api_client, admin_headers)
    url = _phase_url(batch["id"], "holding")
    api_client.put(url, json={"started_at": "09:30"}, headers=admin_headers)

    response = api_client.put(url, json={"started_at": "09:30"}, headers=admin_headers)

    assert response.status_code == 200
    history = api_client.get(f"{url}/history", headers=admin_headers).json()
    assert [entry["action"] for entry in history] == ["created"]


def test_setting_null_on_an_empty_phase_stores_nothing(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    batch = _create(api_client, admin_headers)
    url = _phase_url(batch["id"], "cooling")

    response = api_client.put(url, json={"observation": None}, headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["filled_phases"] == 0
    assert api_client.get(f"{url}/history", headers=admin_headers).json() == []


def test_the_end_time_must_follow_the_start_time(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    batch = _create(api_client, admin_headers)
    url = _phase_url(batch["id"], "holding")

    response = api_client.put(
        url, json={"started_at": "10:00", "ended_at": "09:00"}, headers=admin_headers
    )

    assert response.status_code == 422
    assert response.json()["code"] == "pasteurisation_phase_time_invalid"
    # The rejected write must not leave a half-filled phase behind.
    assert (
        api_client.get(f"{BATCHES}/{batch['id']}", headers=admin_headers).json()["filled_phases"]
        == 0
    )


@pytest.mark.parametrize("payload", [{}, {"unknown": "x"}])
def test_a_phase_payload_without_any_field_is_rejected(
    api_client: TestClient,
    admin_headers: dict[str, str],
    payload: dict[str, Any],
) -> None:
    batch = _create(api_client, admin_headers)

    response = api_client.put(
        _phase_url(batch["id"], "holding"), json=payload, headers=admin_headers
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_an_unknown_phase_is_rejected(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    batch = _create(api_client, admin_headers)

    response = api_client.put(
        _phase_url(batch["id"], "fermentation"),
        json={"observation": "x"},
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_the_batch_date_cannot_be_too_far_in_the_future(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = api_client.post(
        BATCHES, json=_payload(batch_date=_days_ahead(2)), headers=admin_headers
    )

    assert response.status_code == 422
    assert response.json()["code"] == "pasteurisation_date_out_of_range"


@pytest.mark.parametrize("quantity", [0, -1])
def test_the_quantity_must_be_positive(
    api_client: TestClient, admin_headers: dict[str, str], quantity: int
) -> None:
    response = api_client.post(BATCHES, json=_payload(quantity=quantity), headers=admin_headers)

    assert response.status_code == 422


def test_the_header_can_be_corrected(api_client: TestClient, admin_headers: dict[str, str]) -> None:
    batch = _create(api_client, admin_headers)

    response = api_client.put(
        f"{BATCHES}/{batch['id']}",
        json=_payload(product_name="Crème vanille", quantity=140),
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["product_name"] == "Crème vanille"
    assert response.json()["quantity"] == 140
    assert response.json()["lot_number"] == "LOT-2026-001"


def test_the_list_filters_by_lot_and_date_range(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _create(api_client, admin_headers, lot_number="LOT-A-001")
    _create(
        api_client,
        admin_headers,
        lot_number="LOT-B-002",
        product_name="Glace vanille",
        batch_date=_days_ago(3),
    )

    by_lot = api_client.get(f"{BATCHES}?lot=lot-a", headers=admin_headers)
    assert by_lot.status_code == 200
    assert [batch["lot_number"] for batch in by_lot.json()] == ["LOT-A-001"]

    recent = api_client.get(f"{BATCHES}?from={_days_ago(1)}", headers=admin_headers)
    assert [batch["lot_number"] for batch in recent.json()] == ["LOT-A-001"]

    everything = api_client.get(BATCHES, headers=admin_headers)
    assert [batch["lot_number"] for batch in everything.json()] == [
        "LOT-A-001",
        "LOT-B-002",
    ]


def test_deactivation_hides_the_batch(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    batch = _create(api_client, admin_headers)

    assert api_client.delete(f"{BATCHES}/{batch['id']}", headers=admin_headers).status_code == 204

    assert api_client.get(f"{BATCHES}/{batch['id']}", headers=admin_headers).status_code == 404
    assert api_client.get(BATCHES, headers=admin_headers).json() == []


def test_deactivation_is_reserved_to_admins(
    api_client: TestClient, admin_headers: dict[str, str], operator_headers: dict[str, str]
) -> None:
    batch = _create(api_client, admin_headers)

    response = api_client.delete(f"{BATCHES}/{batch['id']}", headers=operator_headers)

    assert response.status_code == 403
    assert response.json()["code"] == "insufficient_role"


def test_an_operator_can_record_a_pasteurisation(
    api_client: TestClient, operator_headers: dict[str, str]
) -> None:
    batch = _create(api_client, operator_headers, lot_number="LOT-OP-1")

    response = api_client.put(
        _phase_url(batch["id"], "preheating"),
        json={"started_at": "09:00", "target_temperature_celsius": 85},
        headers=operator_headers,
    )

    assert response.status_code == 200
    assert response.json()["filled_phases"] == 1
    assert api_client.get(BATCHES, headers=operator_headers).status_code == 200


def test_unknown_batch_returns_404(api_client: TestClient, admin_headers: dict[str, str]) -> None:
    missing = str(uuid.uuid4())

    assert api_client.get(f"{BATCHES}/{missing}", headers=admin_headers).status_code == 404
    assert (
        api_client.put(
            _phase_url(missing, "holding"), json={"started_at": "09:00"}, headers=admin_headers
        ).status_code
        == 404
    )
    assert (
        api_client.get(
            f"{_phase_url(missing, 'holding')}/history", headers=admin_headers
        ).status_code
        == 404
    )


def test_pasteurisations_require_authentication(api_client: TestClient) -> None:
    batch_id = str(uuid.uuid4())

    assert api_client.get(BATCHES).status_code == 401
    assert api_client.post(BATCHES, json=_payload()).status_code == 401
    assert (
        api_client.put(_phase_url(batch_id, "holding"), json={"started_at": "09:00"}).status_code
        == 401
    )
