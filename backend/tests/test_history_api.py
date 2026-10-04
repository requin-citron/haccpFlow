from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

HISTORY = "/api/v1/history"
EQUIPMENT = "/api/v1/equipment"
PLANS = "/api/v1/cleaning-plans"
BATCHES = "/api/v1/pasteurisations"
ENTITIES = {"temperature_reading", "cleaning_record", "pasteurisation_phase"}


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def _days_ago(days: int) -> str:
    return (datetime.now(UTC).date() - timedelta(days=days)).isoformat()


def _days_ahead(days: int) -> str:
    return (datetime.now(UTC).date() + timedelta(days=days)).isoformat()


def _seed_one_of_each(api_client: TestClient, headers: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Create one audited change in each of the three sources."""

    response = api_client.post(
        EQUIPMENT, json={"name": "Frigo historique", "type": "fridge"}, headers=headers
    )
    assert response.status_code == 201
    equipment = response.json()
    api_client.put(
        f"{EQUIPMENT}/{equipment['id']}/readings/{_today()}",
        json={"morning_celsius": 2},
        headers=headers,
    )

    response = api_client.post(
        PLANS, json={"name": "Zone historique", "frequency": "daily"}, headers=headers
    )
    assert response.status_code == 201
    plan = response.json()
    api_client.post(
        f"{PLANS}/{plan['id']}/records",
        json={"cleaning_date": _today()},
        headers=headers,
    )

    response = api_client.post(
        BATCHES,
        json={
            "batch_date": _today(),
            "product_name": "Crème historique",
            "lot_number": "LOT-HISTO",
            "quantity": 10,
        },
        headers=headers,
    )
    assert response.status_code == 201
    batch = response.json()
    api_client.put(
        f"{BATCHES}/{batch['id']}/phases/holding",
        json={"started_at": "09:00"},
        headers=headers,
    )

    return {"equipment": equipment, "plan": plan, "batch": batch}


def test_the_history_merges_the_three_sources(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _seed_one_of_each(api_client, admin_headers)

    response = api_client.get(HISTORY, headers=admin_headers)

    assert response.status_code == 200
    entries = response.json()
    assert {entry["entity"] for entry in entries} == ENTITIES
    assert all(entry["actor_email"] == "admin@test.local" for entry in entries)
    assert all(entry["action"] == "created" for entry in entries)
    timestamps = [entry["occurred_at"] for entry in entries]
    assert timestamps == sorted(timestamps, reverse=True)


def test_the_history_explains_what_changed(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    seeded = _seed_one_of_each(api_client, admin_headers)
    equipment = seeded["equipment"]
    api_client.put(
        f"{EQUIPMENT}/{equipment['id']}/readings/{_today()}",
        json={"morning_celsius": 9},
        headers=admin_headers,
    )

    entries = api_client.get(f"{HISTORY}?entity=temperature_reading", headers=admin_headers).json()

    correction = next(entry for entry in entries if entry["action"] == "updated")
    assert correction["subject"] == "Frigo historique"
    assert correction["detail"] == f"Relevé du {_today()} · matin"
    assert correction["target_id"] == equipment["id"]
    assert correction["changes"] == [
        {
            "field": "temperature_celsius",
            "label": "Température",
            "previous": "2.00",
            "new": "9.00",
        }
    ]


def test_a_deleted_cleaning_is_reported(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    seeded = _seed_one_of_each(api_client, admin_headers)
    plan = seeded["plan"]
    record = api_client.get(f"{PLANS}/{plan['id']}/records", headers=admin_headers).json()[0]
    api_client.delete(f"{PLANS}/{plan['id']}/records/{record['id']}", headers=admin_headers)

    entries = api_client.get(f"{HISTORY}?entity=cleaning_record", headers=admin_headers).json()

    deleted = next(entry for entry in entries if entry["action"] == "deleted")
    assert deleted["subject"] == "Zone historique"
    assert deleted["detail"] == f"Nettoyage du {_today()}"
    assert deleted["target_id"] == plan["id"]


def test_the_history_filters_by_entity(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _seed_one_of_each(api_client, admin_headers)

    entries = api_client.get(f"{HISTORY}?entity=pasteurisation_phase", headers=admin_headers).json()

    assert entries
    assert {entry["entity"] for entry in entries} == {"pasteurisation_phase"}
    assert entries[0]["subject"] == "Crème historique · lot LOT-HISTO"


def test_the_history_filters_by_date(api_client: TestClient, admin_headers: dict[str, str]) -> None:
    _seed_one_of_each(api_client, admin_headers)

    window = api_client.get(f"{HISTORY}?from={_days_ago(1)}&to={_today()}", headers=admin_headers)
    assert window.status_code == 200
    assert len(window.json()) == 3

    future = api_client.get(f"{HISTORY}?from={_days_ahead(1)}", headers=admin_headers)
    assert future.json() == []


def test_the_history_respects_the_limit(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _seed_one_of_each(api_client, admin_headers)

    entries = api_client.get(f"{HISTORY}?limit=2", headers=admin_headers).json()

    assert len(entries) == 2


@pytest.mark.parametrize("limit", [0, 500])
def test_the_history_validates_the_limit(
    api_client: TestClient, admin_headers: dict[str, str], limit: int
) -> None:
    response = api_client.get(f"{HISTORY}?limit={limit}", headers=admin_headers)

    assert response.status_code == 422


def test_the_history_is_reserved_to_admins(
    api_client: TestClient, admin_headers: dict[str, str], operator_headers: dict[str, str]
) -> None:
    _seed_one_of_each(api_client, admin_headers)

    response = api_client.get(HISTORY, headers=operator_headers)

    assert response.status_code == 403
    assert response.json()["code"] == "insufficient_role"


def test_the_history_requires_authentication(api_client: TestClient) -> None:
    assert api_client.get(HISTORY).status_code == 401
