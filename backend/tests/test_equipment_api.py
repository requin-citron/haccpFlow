from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings

pytestmark = pytest.mark.integration

EQUIPMENT_URL = "/api/v1/equipment"


def _payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": "Frigo cuisine", "type": "fridge"}
    payload.update(overrides)
    return payload


def test_create_uses_the_configured_default_thresholds(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = api_client.post(EQUIPMENT_URL, json=_payload(), headers=admin_headers)

    assert response.status_code == 201
    body = response.json()
    settings = get_settings()
    assert body["type"] == "fridge"
    assert body["min_temperature_celsius"] == settings.default_fridge_min_temperature_c
    assert body["max_temperature_celsius"] == settings.default_fridge_max_temperature_c
    assert body["location"] is None
    assert body["notes"] is None
    assert body["created_at"]
    assert "deleted_at" not in body


def test_create_keeps_explicit_thresholds(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = api_client.post(
        EQUIPMENT_URL,
        json=_payload(type="freezer", min_temperature_celsius=-22.5, max_temperature_celsius=-19),
        headers=admin_headers,
    )

    assert response.status_code == 201
    assert response.json()["min_temperature_celsius"] == -22.5
    assert response.json()["max_temperature_celsius"] == -19


def test_defaults_follow_the_environment(
    api_client: TestClient, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEFAULT_FRIDGE_MAX_TEMPERATURE_C", "7")
    get_settings.cache_clear()
    try:
        response = api_client.post(EQUIPMENT_URL, json=_payload(), headers=admin_headers)
        assert response.json()["max_temperature_celsius"] == 7
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize(
    "thresholds",
    [
        {"min_temperature_celsius": 5, "max_temperature_celsius": 2},
        {"min_temperature_celsius": 2, "max_temperature_celsius": 2},
        {"min_temperature_celsius": 2},
        {"max_temperature_celsius": 8},
    ],
)
def test_create_rejects_inconsistent_thresholds(
    api_client: TestClient,
    admin_headers: dict[str, str],
    thresholds: dict[str, float],
) -> None:
    response = api_client.post(EQUIPMENT_URL, json=_payload(**thresholds), headers=admin_headers)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_create_rejects_a_blank_name(api_client: TestClient, admin_headers: dict[str, str]) -> None:
    response = api_client.post(EQUIPMENT_URL, json=_payload(name="   "), headers=admin_headers)

    assert response.status_code == 422


def test_create_rejects_unknown_fields(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = api_client.post(
        EQUIPMENT_URL, json=_payload(unexpected="nope"), headers=admin_headers
    )

    assert response.status_code == 422


def test_create_normalises_optional_text(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = api_client.post(
        EQUIPMENT_URL, json=_payload(location="  ", notes=""), headers=admin_headers
    )

    assert response.status_code == 201
    assert response.json()["location"] is None
    assert response.json()["notes"] is None


def test_create_rejects_a_duplicate_name(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    assert api_client.post(EQUIPMENT_URL, json=_payload(), headers=admin_headers).status_code == 201

    response = api_client.post(EQUIPMENT_URL, json=_payload(), headers=admin_headers)

    assert response.status_code == 409
    assert response.json()["code"] == "equipment_name_conflict"


def test_duplicate_name_detection_ignores_case(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    api_client.post(EQUIPMENT_URL, json=_payload(name="Frigo Cuisine"), headers=admin_headers)

    response = api_client.post(
        EQUIPMENT_URL, json=_payload(name="frigo cuisine"), headers=admin_headers
    )

    assert response.status_code == 409


def test_soft_deleted_name_can_be_reused(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    created = api_client.post(EQUIPMENT_URL, json=_payload(), headers=admin_headers).json()
    assert (
        api_client.delete(f"{EQUIPMENT_URL}/{created['id']}", headers=admin_headers).status_code
        == 204
    )

    response = api_client.post(EQUIPMENT_URL, json=_payload(), headers=admin_headers)

    assert response.status_code == 201
    assert response.json()["id"] != created["id"]


def test_list_returns_only_active_equipment_sorted_by_name(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    api_client.post(EQUIPMENT_URL, json=_payload(name="Zeta"), headers=admin_headers)
    removed = api_client.post(
        EQUIPMENT_URL, json=_payload(name="Beta"), headers=admin_headers
    ).json()
    api_client.post(EQUIPMENT_URL, json=_payload(name="alpha"), headers=admin_headers)
    api_client.delete(f"{EQUIPMENT_URL}/{removed['id']}", headers=admin_headers)

    response = api_client.get(EQUIPMENT_URL, headers=admin_headers)

    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["alpha", "Zeta"]


def test_delete_returns_204_then_404(api_client: TestClient, admin_headers: dict[str, str]) -> None:
    created = api_client.post(EQUIPMENT_URL, json=_payload(), headers=admin_headers).json()

    deleted = api_client.delete(f"{EQUIPMENT_URL}/{created['id']}", headers=admin_headers)
    assert deleted.status_code == 204

    response = api_client.delete(f"{EQUIPMENT_URL}/{created['id']}", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["code"] == "equipment_not_found"


def test_delete_unknown_equipment_returns_404(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = api_client.delete(f"{EQUIPMENT_URL}/{uuid.uuid4()}", headers=admin_headers)

    assert response.status_code == 404


def test_delete_rejects_an_invalid_identifier(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = api_client.delete(f"{EQUIPMENT_URL}/not-a-uuid", headers=admin_headers)

    assert response.status_code == 422


def test_operator_can_create_and_list(
    api_client: TestClient, operator_headers: dict[str, str]
) -> None:
    assert (
        api_client.post(EQUIPMENT_URL, json=_payload(), headers=operator_headers).status_code == 201
    )
    assert api_client.get(EQUIPMENT_URL, headers=operator_headers).status_code == 200


def test_operator_cannot_delete(
    api_client: TestClient, admin_headers: dict[str, str], operator_headers: dict[str, str]
) -> None:
    created = api_client.post(EQUIPMENT_URL, json=_payload(), headers=admin_headers).json()

    response = api_client.delete(f"{EQUIPMENT_URL}/{created['id']}", headers=operator_headers)

    assert response.status_code == 403
    assert response.json()["code"] == "insufficient_role"


def test_list_requires_authentication(api_client: TestClient) -> None:
    assert api_client.get(EQUIPMENT_URL).status_code == 401


def test_create_requires_authentication(api_client: TestClient) -> None:
    assert api_client.post(EQUIPMENT_URL, json=_payload()).status_code == 401


def test_delete_requires_authentication(api_client: TestClient) -> None:
    assert api_client.delete(f"{EQUIPMENT_URL}/{uuid.uuid4()}").status_code == 401
