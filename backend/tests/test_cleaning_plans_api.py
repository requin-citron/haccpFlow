from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

PLANS_URL = "/api/v1/cleaning-plans"
SCHEDULE_URL = "/api/v1/cleaning-schedule"


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def _days_ago(days: int) -> str:
    return (datetime.now(UTC).date() - timedelta(days=days)).isoformat()


def _days_ahead(days: int) -> str:
    return (datetime.now(UTC).date() + timedelta(days=days)).isoformat()


def _create_plan(
    api_client: TestClient,
    headers: dict[str, str],
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": "Zone de préparation", "frequency": "daily"}
    payload.update(overrides)
    response = api_client.post(PLANS_URL, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _declare(
    api_client: TestClient,
    headers: dict[str, str],
    plan_id: str,
    cleaning_date: str,
    comment: str | None = None,
) -> dict[str, Any]:
    response = api_client.post(
        f"{PLANS_URL}/{plan_id}/records",
        json={"cleaning_date": cleaning_date, "comment": comment},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_plan_lifecycle(api_client: TestClient, admin_headers: dict[str, str]) -> None:
    plan = _create_plan(api_client, admin_headers, products="Savon + javel")

    assert plan["frequency"] == "daily"
    assert plan["products"] == "Savon + javel"
    assert plan["last_cleaning_date"] is None
    # Never cleaned: due since the day it was created.
    assert plan["next_due_date"] == _today()

    listing = api_client.get(PLANS_URL, headers=admin_headers)
    assert listing.status_code == 200
    assert [item["name"] for item in listing.json()] == ["Zone de préparation"]

    updated = api_client.put(
        f"{PLANS_URL}/{plan['id']}",
        json={"name": "Zone cuisine", "frequency": "weekly", "products": None},
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["frequency"] == "weekly"
    assert updated.json()["products"] is None

    assert api_client.delete(f"{PLANS_URL}/{plan['id']}", headers=admin_headers).status_code == 204
    assert api_client.get(PLANS_URL, headers=admin_headers).json() == []
    assert (
        api_client.put(
            f"{PLANS_URL}/{plan['id']}",
            json={"name": "Zone cuisine", "frequency": "weekly"},
            headers=admin_headers,
        ).status_code
        == 404
    )


def test_plan_name_must_be_unique_ignoring_case(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _create_plan(api_client, admin_headers, name="Zone de préparation")

    response = api_client.post(
        PLANS_URL,
        json={"name": "zone de PRÉPARATION", "frequency": "daily"},
        headers=admin_headers,
    )

    assert response.status_code == 409
    assert response.json()["code"] == "cleaning_plan_name_conflict"


def test_a_deactivated_plan_frees_its_name(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    plan = _create_plan(api_client, admin_headers)
    api_client.delete(f"{PLANS_URL}/{plan['id']}", headers=admin_headers)

    response = api_client.post(
        PLANS_URL,
        json={"name": plan["name"], "frequency": "weekly"},
        headers=admin_headers,
    )

    assert response.status_code == 201


def test_a_never_cleaned_plan_is_due_today_and_not_late(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    plan = _create_plan(api_client, admin_headers)

    schedule = api_client.get(SCHEDULE_URL, headers=admin_headers)
    assert schedule.status_code == 200
    entries = schedule.json()
    assert [(entry["name"], entry["status"], entry["days_late"]) for entry in entries] == [
        (plan["name"], "due_today", 0)
    ]
    assert api_client.get(f"{SCHEDULE_URL}/overdue", headers=admin_headers).json() == []


def test_a_daily_plan_is_due_the_day_after_a_cleaning(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    plan = _create_plan(api_client, admin_headers)
    _declare(api_client, admin_headers, plan["id"], _today())

    entries = api_client.get(SCHEDULE_URL, headers=admin_headers).json()

    assert entries[0]["last_cleaning_date"] == _today()
    assert entries[0]["next_due_date"] == _days_ahead(1)
    assert entries[0]["status"] == "upcoming"


def test_after_each_use_plans_are_never_scheduled(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _create_plan(api_client, admin_headers, name="Trancheuse", frequency="after_each_use")

    assert api_client.get(SCHEDULE_URL, headers=admin_headers).json() == []
    assert api_client.get(f"{SCHEDULE_URL}/overdue", headers=admin_headers).json() == []

    plans = api_client.get(PLANS_URL, headers=admin_headers).json()
    assert plans[0]["next_due_date"] is None


def test_overdue_lists_only_strictly_late_plans(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _create_plan(api_client, admin_headers, name="Zone à jour")
    late = _create_plan(api_client, admin_headers, name="Zone en retard")
    _declare(api_client, admin_headers, late["id"], _days_ago(3))

    overdue = api_client.get(f"{SCHEDULE_URL}/overdue", headers=admin_headers).json()

    assert [entry["name"] for entry in overdue] == ["Zone en retard"]
    assert overdue[0]["days_late"] == 2


def test_schedule_is_sorted_with_late_plans_first(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _create_plan(api_client, admin_headers, name="Zone à jour")
    late = _create_plan(api_client, admin_headers, name="Zone en retard")
    _declare(api_client, admin_headers, late["id"], _days_ago(3))

    entries = api_client.get(SCHEDULE_URL, headers=admin_headers).json()

    assert [entry["name"] for entry in entries] == ["Zone en retard", "Zone à jour"]
    assert [entry["status"] for entry in entries] == ["overdue", "due_today"]


def test_schedule_accepts_a_reference_date(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _create_plan(api_client, admin_headers)

    entries = api_client.get(f"{SCHEDULE_URL}?on={_days_ahead(3)}", headers=admin_headers).json()

    assert entries[0]["status"] == "overdue"
    assert entries[0]["days_late"] == 3


def test_declaring_a_cleaning_records_author_and_comment(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    plan = _create_plan(api_client, admin_headers)

    record = _declare(api_client, admin_headers, plan["id"], _today(), comment="  javel diluée  ")

    assert record["cleaning_date"] == _today()
    assert record["comment"] == "javel diluée"
    assert record["performed_by_email"] == "admin@test.local"
    assert record["recorded_at"]


def test_several_cleanings_can_be_declared_the_same_day(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    plan = _create_plan(api_client, admin_headers, frequency="after_each_use")

    _declare(api_client, admin_headers, plan["id"], _today())
    _declare(api_client, admin_headers, plan["id"], _today())

    records = api_client.get(f"{PLANS_URL}/{plan['id']}/records", headers=admin_headers).json()
    assert len(records) == 2


def test_records_are_listed_most_recent_first(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    plan = _create_plan(api_client, admin_headers, frequency="after_each_use")
    for offset in (2, 0, 1):
        _declare(api_client, admin_headers, plan["id"], _days_ago(offset))

    records = api_client.get(f"{PLANS_URL}/{plan['id']}/records", headers=admin_headers).json()

    assert [record["cleaning_date"] for record in records] == [
        _today(),
        _days_ago(1),
        _days_ago(2),
    ]


def test_a_cleaning_can_be_corrected_with_an_audit_trail(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    plan = _create_plan(api_client, admin_headers)
    record = _declare(api_client, admin_headers, plan["id"], _days_ago(1), comment="RAS")

    response = api_client.put(
        f"{PLANS_URL}/{plan['id']}/records/{record['id']}",
        json={"cleaning_date": _today()},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["cleaning_date"] == _today()
    assert response.json()["comment"] == "RAS"

    history = api_client.get(
        f"{PLANS_URL}/{plan['id']}/records/{record['id']}/history", headers=admin_headers
    ).json()
    assert [entry["action"] for entry in history] == ["updated", "created"]
    assert history[0]["previous_cleaning_date"] == _days_ago(1)
    assert history[0]["new_cleaning_date"] == _today()
    assert history[0]["changed_by_email"] == "admin@test.local"
    assert history[1]["previous_cleaning_date"] is None


def test_a_comment_can_be_cleared(api_client: TestClient, admin_headers: dict[str, str]) -> None:
    plan = _create_plan(api_client, admin_headers)
    record = _declare(api_client, admin_headers, plan["id"], _today(), comment="RAS")

    response = api_client.put(
        f"{PLANS_URL}/{plan['id']}/records/{record['id']}",
        json={"comment": None},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["comment"] is None
    history = api_client.get(
        f"{PLANS_URL}/{plan['id']}/records/{record['id']}/history", headers=admin_headers
    ).json()
    assert history[0]["previous_comment"] == "RAS"
    assert history[0]["new_comment"] is None


def test_a_no_op_correction_adds_no_audit_line(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    plan = _create_plan(api_client, admin_headers)
    record = _declare(api_client, admin_headers, plan["id"], _today())

    response = api_client.put(
        f"{PLANS_URL}/{plan['id']}/records/{record['id']}",
        json={"cleaning_date": _today()},
        headers=admin_headers,
    )

    assert response.status_code == 200
    history = api_client.get(
        f"{PLANS_URL}/{plan['id']}/records/{record['id']}/history", headers=admin_headers
    ).json()
    assert [entry["action"] for entry in history] == ["created"]


def test_deleting_a_cleaning_keeps_it_in_the_audit_trail(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    plan = _create_plan(api_client, admin_headers)
    record = _declare(api_client, admin_headers, plan["id"], _today(), comment="RAS")

    deleted = api_client.delete(
        f"{PLANS_URL}/{plan['id']}/records/{record['id']}", headers=admin_headers
    )
    assert deleted.status_code == 204
    assert api_client.get(f"{PLANS_URL}/{plan['id']}/records", headers=admin_headers).json() == []

    history = api_client.get(
        f"{PLANS_URL}/{plan['id']}/records/{record['id']}/history", headers=admin_headers
    ).json()
    assert [entry["action"] for entry in history] == ["deleted", "created"]
    assert history[0]["previous_cleaning_date"] == _today()
    assert history[0]["new_cleaning_date"] is None


def test_a_deleted_cleaning_no_longer_counts_for_the_schedule(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    plan = _create_plan(api_client, admin_headers)
    record = _declare(api_client, admin_headers, plan["id"], _today())
    assert api_client.get(SCHEDULE_URL, headers=admin_headers).json()[0]["status"] == "upcoming"

    api_client.delete(f"{PLANS_URL}/{plan['id']}/records/{record['id']}", headers=admin_headers)

    entries = api_client.get(SCHEDULE_URL, headers=admin_headers).json()
    assert entries[0]["last_cleaning_date"] is None
    assert entries[0]["status"] == "due_today"


def test_a_future_cleaning_date_is_rejected(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    plan = _create_plan(api_client, admin_headers)

    response = api_client.post(
        f"{PLANS_URL}/{plan['id']}/records",
        json={"cleaning_date": _days_ahead(2)},
        headers=admin_headers,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "cleaning_date_out_of_range"


def test_unknown_plan_and_record_return_404(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    missing_plan = str(uuid.uuid4())
    plan = _create_plan(api_client, admin_headers)

    assert (
        api_client.get(f"{PLANS_URL}/{missing_plan}/records", headers=admin_headers).status_code
        == 404
    )
    assert (
        api_client.post(
            f"{PLANS_URL}/{missing_plan}/records",
            json={"cleaning_date": _today()},
            headers=admin_headers,
        ).status_code
        == 404
    )

    missing_record = str(uuid.uuid4())
    assert (
        api_client.put(
            f"{PLANS_URL}/{plan['id']}/records/{missing_record}",
            json={"cleaning_date": _today()},
            headers=admin_headers,
        ).status_code
        == 404
    )
    assert (
        api_client.get(
            f"{PLANS_URL}/{plan['id']}/records/{missing_record}/history", headers=admin_headers
        ).status_code
        == 404
    )


def test_plan_deletion_is_reserved_to_admins(
    api_client: TestClient, admin_headers: dict[str, str], operator_headers: dict[str, str]
) -> None:
    plan = _create_plan(api_client, admin_headers)

    response = api_client.delete(f"{PLANS_URL}/{plan['id']}", headers=operator_headers)

    assert response.status_code == 403
    assert response.json()["code"] == "insufficient_role"
    assert len(api_client.get(PLANS_URL, headers=admin_headers).json()) == 1


def test_operator_can_manage_plans_and_cleanings(
    api_client: TestClient, operator_headers: dict[str, str]
) -> None:
    plan = _create_plan(api_client, operator_headers, name="Zone opérateur")

    assert (
        api_client.put(
            f"{PLANS_URL}/{plan['id']}",
            json={"name": "Zone opérateur", "frequency": "weekly"},
            headers=operator_headers,
        ).status_code
        == 200
    )
    record = _declare(api_client, operator_headers, plan["id"], _today())
    assert (
        api_client.delete(
            f"{PLANS_URL}/{plan['id']}/records/{record['id']}", headers=operator_headers
        ).status_code
        == 204
    )
    assert api_client.get(SCHEDULE_URL, headers=operator_headers).status_code == 200


def test_cleaning_plans_require_authentication(api_client: TestClient) -> None:
    payload = {"name": "Zone", "frequency": "daily"}
    plan_id = str(uuid.uuid4())

    assert api_client.get(PLANS_URL).status_code == 401
    assert api_client.post(PLANS_URL, json=payload).status_code == 401
    assert api_client.get(SCHEDULE_URL).status_code == 401
    assert (
        api_client.post(
            f"{PLANS_URL}/{plan_id}/records", json={"cleaning_date": _today()}
        ).status_code
        == 401
    )
