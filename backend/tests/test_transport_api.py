from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

TRANSPORTS = "/api/v1/transports"
VEHICLES = "/api/v1/vehicles"
HISTORY = "/api/v1/history"


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def _days_ago(days: int) -> str:
    return (datetime.now(UTC).date() - timedelta(days=days)).isoformat()


def _days_ahead(days: int) -> str:
    return (datetime.now(UTC).date() + timedelta(days=days)).isoformat()


def _vehicle(
    api_client: TestClient,
    headers: dict[str, str],
    name: str = "Camion frigo 1",
    plate: str = "AB-123-CD",
) -> dict[str, Any]:
    response = api_client.post(VEHICLES, json={"name": name, "plate": plate}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "transport_date": _today(),
        "place": "Boulangerie Martin",
        "product_name": "Crème anglaise",
        "lot_number": "LOT-2026-100",
        "vehicle_label": "Transporteur externe 1234 XYZ",
    }
    payload.update(overrides)
    return payload


def _create(api_client: TestClient, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    response = api_client.post(TRANSPORTS, json=_payload(**overrides), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _readings_url(transport_id: str) -> str:
    return f"{TRANSPORTS}/{transport_id}/readings"


def test_a_transport_can_use_a_registered_vehicle(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    vehicle = _vehicle(api_client, admin_headers)

    transport = _create(
        api_client,
        admin_headers,
        vehicle_label=None,
        vehicle_id=vehicle["id"],
        departure_time="08:00",
        departure_temperature_celsius=3.5,
    )

    assert transport["vehicle"] == {
        "id": vehicle["id"],
        "name": "Camion frigo 1",
        "plate": "AB-123-CD",
    }
    assert transport["departure_time"] == "08:00:00"
    assert transport["departure_temperature_celsius"] == 3.5
    assert transport["arrival_time"] is None
    assert transport["is_complete"] is False


def test_a_transport_can_use_a_free_label(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    transport = _create(api_client, admin_headers)

    assert transport["vehicle"] == {
        "id": None,
        "name": "Transporteur externe 1234 XYZ",
        "plate": None,
    }


@pytest.mark.parametrize(
    "vehicle",
    [{"vehicle_label": None}, {"vehicle_id": str(uuid.uuid4()), "vehicle_label": "Camion"}],
)
def test_a_transport_needs_exactly_one_vehicle(
    api_client: TestClient,
    admin_headers: dict[str, str],
    vehicle: dict[str, Any],
) -> None:
    # Both cases are rejected before any database lookup happens.
    response = api_client.post(TRANSPORTS, json=_payload(**vehicle), headers=admin_headers)

    assert response.status_code in {422, 404}


def test_an_unknown_vehicle_is_rejected(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = api_client.post(
        TRANSPORTS,
        json=_payload(vehicle_label=None, vehicle_id=str(uuid.uuid4())),
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "vehicle_not_found"


def test_the_arrival_completes_the_transport(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    transport = _create(
        api_client,
        admin_headers,
        departure_time="08:00",
        departure_temperature_celsius=3.5,
    )

    response = api_client.put(
        _readings_url(transport["id"]),
        json={"arrival_time": "10:15", "arrival_temperature_celsius": 4},
        headers=admin_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_complete"] is True
    assert body["departure_time"] == "08:00:00"
    assert body["departure_temperature_celsius"] == 3.5
    assert body["arrival_temperature_celsius"] == 4


def test_a_night_delivery_is_accepted(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    transport = _create(
        api_client,
        admin_headers,
        departure_time="23:30",
        departure_temperature_celsius=3,
        arrival_time="01:15",
        arrival_temperature_celsius=4,
    )

    assert transport["is_complete"] is True


def test_a_readings_edit_does_not_touch_the_other_checkpoint(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    transport = _create(
        api_client,
        admin_headers,
        departure_time="08:00",
        departure_temperature_celsius=3.5,
        arrival_time="10:15",
    )

    response = api_client.put(
        _readings_url(transport["id"]),
        json={"arrival_temperature_celsius": 5},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["departure_temperature_celsius"] == 3.5
    assert response.json()["arrival_temperature_celsius"] == 5


def test_an_empty_readings_body_is_rejected(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    transport = _create(api_client, admin_headers)

    response = api_client.put(_readings_url(transport["id"]), json={}, headers=admin_headers)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_a_correction_is_audited(api_client: TestClient, admin_headers: dict[str, str]) -> None:
    transport = _create(
        api_client,
        admin_headers,
        departure_time="08:00",
        departure_temperature_celsius=3.5,
    )

    api_client.put(
        _readings_url(transport["id"]),
        json={"departure_temperature_celsius": 8},
        headers=admin_headers,
    )

    entries = api_client.get(f"{HISTORY}?entity=transport", headers=admin_headers).json()
    correction = next(entry for entry in entries if entry["action"] == "updated")
    assert correction["subject"] == "Crème anglaise · Boulangerie Martin"
    assert correction["target_id"] == transport["id"]
    assert correction["changes"] == [
        {
            "field": "departure_temperature_celsius",
            "label": "Température de départ",
            "previous": "3.50",
            "new": "8.00",
        }
    ]


def test_a_no_op_readings_edit_adds_no_audit_line(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    transport = _create(
        api_client,
        admin_headers,
        departure_time="08:00",
        departure_temperature_celsius=3.5,
    )
    before = len(api_client.get(f"{HISTORY}?entity=transport", headers=admin_headers).json())

    response = api_client.put(
        _readings_url(transport["id"]),
        json={"departure_time": "08:00"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    after = len(api_client.get(f"{HISTORY}?entity=transport", headers=admin_headers).json())
    assert after == before


def test_the_header_can_be_corrected_without_touching_the_readings(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    transport = _create(
        api_client,
        admin_headers,
        departure_time="08:00",
        departure_temperature_celsius=3.5,
    )

    response = api_client.put(
        f"{TRANSPORTS}/{transport['id']}",
        json=_payload(place="Épicerie Dubois"),
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["place"] == "Épicerie Dubois"
    assert response.json()["departure_temperature_celsius"] == 3.5


def test_the_list_filters_by_lot_and_date(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _create(api_client, admin_headers, lot_number="LOT-A-001")
    _create(
        api_client,
        admin_headers,
        lot_number="LOT-B-002",
        product_name="Glace vanille",
        transport_date=_days_ago(3),
    )

    by_lot = api_client.get(f"{TRANSPORTS}?lot=lot-a", headers=admin_headers)
    assert by_lot.status_code == 200
    assert [item["lot_number"] for item in by_lot.json()] == ["LOT-A-001"]

    recent = api_client.get(f"{TRANSPORTS}?from={_days_ago(1)}", headers=admin_headers)
    assert [item["lot_number"] for item in recent.json()] == ["LOT-A-001"]

    everything = api_client.get(TRANSPORTS, headers=admin_headers)
    assert [item["lot_number"] for item in everything.json()] == [
        "LOT-A-001",
        "LOT-B-002",
    ]


def test_a_transport_stays_readable_after_its_vehicle_is_deactivated(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    vehicle = _vehicle(api_client, admin_headers)
    transport = _create(
        api_client,
        admin_headers,
        vehicle_label=None,
        vehicle_id=vehicle["id"],
        departure_time="08:00",
    )
    api_client.delete(f"{VEHICLES}/{vehicle['id']}", headers=admin_headers)

    detail = api_client.get(f"{TRANSPORTS}/{transport['id']}", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["vehicle"]["name"] == "Camion frigo 1"

    edited = api_client.put(
        _readings_url(transport["id"]),
        json={"arrival_temperature_celsius": 4},
        headers=admin_headers,
    )
    assert edited.status_code == 200


def test_the_date_cannot_be_too_far_in_the_future(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = api_client.post(
        TRANSPORTS, json=_payload(transport_date=_days_ahead(2)), headers=admin_headers
    )

    assert response.status_code == 422
    assert response.json()["code"] == "transport_date_out_of_range"


def test_a_temperature_out_of_bounds_is_rejected(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = api_client.post(
        TRANSPORTS,
        json=_payload(departure_temperature_celsius=-300),
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_deactivation_hides_the_transport(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    transport = _create(api_client, admin_headers)

    assert (
        api_client.delete(f"{TRANSPORTS}/{transport['id']}", headers=admin_headers).status_code
        == 204
    )
    assert (
        api_client.get(f"{TRANSPORTS}/{transport['id']}", headers=admin_headers).status_code == 404
    )
    assert api_client.get(TRANSPORTS, headers=admin_headers).json() == []


def test_deactivation_is_reserved_to_admins(
    api_client: TestClient, admin_headers: dict[str, str], operator_headers: dict[str, str]
) -> None:
    transport = _create(api_client, admin_headers, vehicle_label="Camion")

    response = api_client.delete(f"{TRANSPORTS}/{transport['id']}", headers=operator_headers)

    assert response.status_code == 403


def test_an_operator_can_record_a_transport(
    api_client: TestClient, operator_headers: dict[str, str]
) -> None:
    transport = _create(
        api_client,
        operator_headers,
        vehicle_label="Camion opérateur",
        departure_time="08:00",
    )

    assert transport["departure_time"] == "08:00:00"
    assert (
        api_client.put(
            _readings_url(transport["id"]),
            json={"arrival_time": "09:00"},
            headers=operator_headers,
        ).status_code
        == 200
    )
    assert api_client.get(TRANSPORTS, headers=operator_headers).status_code == 200


def test_unknown_transport_returns_404(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    missing = str(uuid.uuid4())

    assert api_client.get(f"{TRANSPORTS}/{missing}", headers=admin_headers).status_code == 404
    assert (
        api_client.put(
            _readings_url(missing), json={"arrival_time": "09:00"}, headers=admin_headers
        ).status_code
        == 404
    )


def test_transports_require_authentication(api_client: TestClient) -> None:
    assert api_client.get(TRANSPORTS).status_code == 401
    assert api_client.post(TRANSPORTS, json=_payload()).status_code == 401
