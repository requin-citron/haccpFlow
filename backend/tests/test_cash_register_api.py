from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

CASH_REGISTERS = "/api/v1/cash-registers"


def _create(api_client: TestClient, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": "Caisse principale"}
    payload.update(overrides)
    response = api_client.post(CASH_REGISTERS, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_a_register_can_be_enrolled_with_its_opening_count(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create(
        api_client,
        admin_headers,
        coins_1_cent=12,
        coins_50_cent=2,
        coins_1_euro=3,
        notes_50_euro=1,
    )

    assert cash_register["name"] == "Caisse principale"
    assert cash_register["coins_1_cent"] == 12
    assert cash_register["coins_50_cent"] == 2
    assert cash_register["notes_50_euro"] == 1
    # 12 + 100 + 300 + 5000
    assert cash_register["total_cents"] == 5412


def test_missing_denominations_default_to_zero(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create(api_client, admin_headers, coins_2_euro=4)

    assert cash_register["coins_2_euro"] == 4
    assert cash_register["total_cents"] == 800
    for field in (
        "coins_1_cent",
        "coins_5_cent",
        "coins_50_cent",
        "notes_10_euro",
        "notes_50_euro",
    ):
        assert cash_register[field] == 0


def test_a_register_without_any_count_is_allowed(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create(api_client, admin_headers, name="Caisse vide")

    assert cash_register["total_cents"] == 0


def test_registers_are_listed_by_name(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _create(api_client, admin_headers, name="Caisse bar")
    _create(api_client, admin_headers, name="caisse accueil")

    response = api_client.get(CASH_REGISTERS, headers=admin_headers)

    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["caisse accueil", "Caisse bar"]


def test_the_name_is_unique_among_active_registers(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    _create(api_client, admin_headers, name="Caisse principale")

    response = api_client.post(
        CASH_REGISTERS, json={"name": "caisse PRINCIPALE"}, headers=admin_headers
    )

    assert response.status_code == 409
    assert response.json()["code"] == "cash_register_name_conflict"


def test_a_count_can_be_corrected(api_client: TestClient, admin_headers: dict[str, str]) -> None:
    cash_register = _create(api_client, admin_headers, coins_1_euro=3)

    response = api_client.put(
        f"{CASH_REGISTERS}/{cash_register['id']}",
        json={"name": "Caisse principale", "coins_1_euro": 5, "notes_10_euro": 2},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["coins_1_euro"] == 5
    assert response.json()["notes_10_euro"] == 2
    assert response.json()["total_cents"] == 2500


def test_the_name_can_be_changed_and_kept(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create(api_client, admin_headers, name="Caisse 1")

    kept = api_client.put(
        f"{CASH_REGISTERS}/{cash_register['id']}",
        json={"name": "Caisse 1", "coins_1_cent": 1},
        headers=admin_headers,
    )
    renamed = api_client.put(
        f"{CASH_REGISTERS}/{cash_register['id']}",
        json={"name": "Caisse comptoir", "coins_1_cent": 1},
        headers=admin_headers,
    )

    assert kept.status_code == 200
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Caisse comptoir"


def test_deactivation_hides_the_register_and_frees_its_name(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create(api_client, admin_headers)

    assert (
        api_client.delete(
            f"{CASH_REGISTERS}/{cash_register['id']}", headers=admin_headers
        ).status_code
        == 204
    )
    assert api_client.get(CASH_REGISTERS, headers=admin_headers).json() == []
    assert (
        api_client.put(
            f"{CASH_REGISTERS}/{cash_register['id']}",
            json={"name": "Caisse principale"},
            headers=admin_headers,
        ).status_code
        == 404
    )

    again = api_client.post(
        CASH_REGISTERS, json={"name": "Caisse principale"}, headers=admin_headers
    )
    assert again.status_code == 201


@pytest.mark.parametrize("count", [-1, 1_000_001])
def test_a_count_out_of_range_is_rejected(
    api_client: TestClient, admin_headers: dict[str, str], count: int
) -> None:
    response = api_client.post(
        CASH_REGISTERS,
        json={"name": "Caisse hors bornes", "coins_1_euro": count},
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_an_unknown_denomination_is_rejected(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = api_client.post(
        CASH_REGISTERS,
        json={"name": "Caisse", "notes_100_euro": 2},
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_unknown_register_returns_404(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = api_client.put(
        f"{CASH_REGISTERS}/{uuid.uuid4()}",
        json={"name": "Caisse"},
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["code"] == "cash_register_not_found"


def test_deactivation_is_reserved_to_admins(
    api_client: TestClient, admin_headers: dict[str, str], operator_headers: dict[str, str]
) -> None:
    cash_register = _create(api_client, admin_headers)

    response = api_client.delete(
        f"{CASH_REGISTERS}/{cash_register['id']}", headers=operator_headers
    )

    assert response.status_code == 403


def test_an_operator_can_enrol_a_register(
    api_client: TestClient, operator_headers: dict[str, str]
) -> None:
    cash_register = _create(api_client, operator_headers, name="Caisse opérateur", notes_5_euro=1)

    assert cash_register["total_cents"] == 500
    assert (
        api_client.put(
            f"{CASH_REGISTERS}/{cash_register['id']}",
            json={"name": "Caisse opérateur", "notes_5_euro": 2},
            headers=operator_headers,
        ).status_code
        == 200
    )
    assert api_client.get(CASH_REGISTERS, headers=operator_headers).status_code == 200


def test_cash_registers_require_authentication(api_client: TestClient) -> None:
    assert api_client.get(CASH_REGISTERS).status_code == 401
    assert api_client.post(CASH_REGISTERS, json={"name": "Caisse"}).status_code == 401
