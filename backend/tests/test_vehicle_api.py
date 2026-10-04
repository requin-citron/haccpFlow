from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

VEHICLES = "/api/v1/vehicles"


def _create(api_client: TestClient, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": "Camion frigo 1", "plate": "AB-123-CD"}
    payload.update(overrides)
    response = api_client.post(VEHICLES, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_a_vehicle_can_be_created_with_a_name_only(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    vehicle = _create(api_client, admin_headers, name="Camion frigo 1", plate=None)

    assert vehicle["name"] == "Camion frigo 1"
    assert vehicle["plate"] is None


def test_a_vehicle_can_be_created_with_a_plate_only(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    vehicle = _create(api_client, admin_headers, name=None, plate="AB-123-CD")

    assert vehicle["name"] is None
    assert vehicle["plate"] == "AB-123-CD"


def test_a_vehicle_needs_a_name_or_a_plate(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = api_client.post(VEHICLES, json={"name": None, "plate": "   "}, headers=admin_headers)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_a_plate_and_a_name_are_unique_among_active_vehicles(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _create(api_client, admin_headers, name="Camion frigo 1", plate="AB-123-CD")

    same_plate = api_client.post(
        VEHICLES, json={"name": "Autre", "plate": "ab-123-cd"}, headers=admin_headers
    )
    same_name = api_client.post(
        VEHICLES, json={"name": "camion FRIGO 1", "plate": "ZZ-999-ZZ"}, headers=admin_headers
    )

    assert same_plate.status_code == 409
    assert same_plate.json()["code"] == "vehicle_conflict"
    assert same_name.status_code == 409


def test_a_vehicle_can_be_listed_and_corrected(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    vehicle = _create(api_client, admin_headers)

    listing = api_client.get(VEHICLES, headers=admin_headers)
    assert listing.status_code == 200
    assert [item["plate"] for item in listing.json()] == ["AB-123-CD"]

    response = api_client.put(
        f"{VEHICLES}/{vehicle['id']}",
        json={"name": "Camion frigo 1", "plate": "EF-456-GH"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["plate"] == "EF-456-GH"


def test_deactivation_frees_the_name_and_the_plate(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    vehicle = _create(api_client, admin_headers)

    assert (
        api_client.delete(f"{VEHICLES}/{vehicle['id']}", headers=admin_headers).status_code == 204
    )
    assert api_client.get(VEHICLES, headers=admin_headers).json() == []
    assert (
        api_client.put(
            f"{VEHICLES}/{vehicle['id']}",
            json={"name": "Camion frigo 1", "plate": "AB-123-CD"},
            headers=admin_headers,
        ).status_code
        == 404
    )

    again = api_client.post(
        VEHICLES,
        json={"name": "Camion frigo 1", "plate": "AB-123-CD"},
        headers=admin_headers,
    )
    assert again.status_code == 201


def test_unknown_vehicle_returns_404(api_client: TestClient, admin_headers: dict[str, str]) -> None:
    response = api_client.put(
        f"{VEHICLES}/{uuid.uuid4()}",
        json={"name": "Camion", "plate": None},
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "vehicle_not_found"


def test_deactivation_is_reserved_to_admins(
    api_client: TestClient, admin_headers: dict[str, str], operator_headers: dict[str, str]
) -> None:
    vehicle = _create(api_client, admin_headers)

    response = api_client.delete(f"{VEHICLES}/{vehicle['id']}", headers=operator_headers)

    assert response.status_code == 403
    assert response.json()["code"] == "insufficient_role"


def test_an_operator_can_manage_vehicles(
    api_client: TestClient, operator_headers: dict[str, str]
) -> None:
    vehicle = _create(api_client, operator_headers, name="Camion opérateur", plate=None)

    assert api_client.get(VEHICLES, headers=operator_headers).status_code == 200
    assert (
        api_client.put(
            f"{VEHICLES}/{vehicle['id']}",
            json={"name": "Camion opérateur", "plate": "OP-000-OP"},
            headers=operator_headers,
        ).status_code
        == 200
    )


def test_vehicles_require_authentication(api_client: TestClient) -> None:
    assert api_client.get(VEHICLES).status_code == 401
    assert api_client.post(VEHICLES, json={"name": "Camion", "plate": None}).status_code == 401
