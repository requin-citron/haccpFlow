from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.models.cash_register import DENOMINATION_FIELDS

pytestmark = pytest.mark.integration

CASH_REGISTERS = "/api/v1/cash-registers"
CASH_SESSIONS = "/api/v1/cash-sessions"


def _counts(**overrides: int) -> dict[str, int]:
    """Every denomination, so a payload is always complete."""

    counts = dict.fromkeys(DENOMINATION_FIELDS, 0)
    counts.update(overrides)
    return counts


def _today() -> date:
    """The server's day, as the API computes it."""

    return datetime.now(UTC).date()


def _create_register(
    api_client: TestClient, headers: dict[str, str], **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": "Caisse principale", **overrides}
    response = api_client.post(CASH_REGISTERS, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _open_session(
    api_client: TestClient,
    headers: dict[str, str],
    cash_register_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"cash_register_id": cash_register_id, **overrides}
    response = api_client.post(CASH_SESSIONS, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _add_expense(
    api_client: TestClient,
    headers: dict[str, str],
    session_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kind": "professional",
        "name": "Achat",
        "quantity": 1,
        "unit_price_cents": 100,
        "vat_rate": "20.00",
        **overrides,
    }
    response = api_client.post(
        f"{CASH_SESSIONS}/{session_id}/expenses", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def _close(
    api_client: TestClient,
    headers: dict[str, str],
    session_id: str,
    **overrides: int,
) -> Any:
    return api_client.post(
        f"{CASH_SESSIONS}/{session_id}/close",
        json={"closing_counts": _counts(**overrides)},
        headers=headers,
    )


def test_opening_a_session_copies_the_register_count(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers, coins_1_euro=3, notes_10_euro=2)

    session = _open_session(api_client, admin_headers, cash_register["id"])

    assert session["cash_register_name"] == "Caisse principale"
    assert session["opening_counts"]["coins_1_euro"] == 3
    assert session["opening_counts"]["notes_10_euro"] == 2
    assert session["opening_total_cents"] == 2300
    assert session["is_open"] is True
    assert session["closing_counts"] is None
    assert session["closing_total_cents"] is None
    assert session["expenses"] == []
    assert session["closed_at"] is None
    assert session["opened_by_email"] == "admin@test.local"


def test_the_opening_float_can_be_overridden(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers, coins_1_euro=3)

    session = _open_session(
        api_client,
        admin_headers,
        cash_register["id"],
        opening_counts=_counts(notes_20_euro=1),
    )

    assert session["opening_counts"]["notes_20_euro"] == 1
    assert session["opening_counts"]["coins_1_euro"] == 0
    # The register itself is untouched by the override.
    listing = api_client.get(CASH_REGISTERS, headers=admin_headers).json()
    assert listing[0]["coins_1_euro"] == 3


def test_the_session_date_defaults_to_today(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers)

    session = _open_session(api_client, admin_headers, cash_register["id"])

    assert session["session_date"] == datetime.now(UTC).date().isoformat()


def test_the_session_can_be_backdated(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers)
    yesterday = _today() - timedelta(days=1)

    session = _open_session(
        api_client, admin_headers, cash_register["id"], session_date=yesterday.isoformat()
    )

    assert session["session_date"] == yesterday.isoformat()


def test_a_date_far_in_the_future_is_rejected(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers)

    response = api_client.post(
        CASH_SESSIONS,
        json={
            "cash_register_id": cash_register["id"],
            "session_date": (_today() + timedelta(days=10)).isoformat(),
        },
        headers=admin_headers,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "cash_session_date_in_future"


def test_a_register_cannot_have_two_open_sessions(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers)
    _open_session(api_client, admin_headers, cash_register["id"])

    response = api_client.post(
        CASH_SESSIONS, json={"cash_register_id": cash_register["id"]}, headers=admin_headers
    )

    assert response.status_code == 409
    assert response.json()["code"] == "cash_session_already_open"


def test_the_same_register_can_be_opened_again_once_closed(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers, coins_1_euro=1)
    session = _open_session(api_client, admin_headers, cash_register["id"])
    assert _close(api_client, admin_headers, session["id"], notes_5_euro=1).status_code == 200

    second = _open_session(api_client, admin_headers, cash_register["id"])

    # The float of the new session is the count committed by the closing one.
    assert second["opening_counts"]["notes_5_euro"] == 1
    assert second["opening_counts"]["coins_1_euro"] == 0


def test_an_open_session_can_be_corrected(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers)
    session = _open_session(api_client, admin_headers, cash_register["id"])
    yesterday = (_today() - timedelta(days=1)).isoformat()

    response = api_client.put(
        f"{CASH_SESSIONS}/{session['id']}",
        json={"session_date": yesterday, "opening_counts": _counts(coins_2_euro=4)},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["session_date"] == yesterday
    assert response.json()["opening_total_cents"] == 800


def test_expenses_are_recorded_with_their_totals(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers)
    session = _open_session(api_client, admin_headers, cash_register["id"])

    session = _add_expense(
        api_client,
        admin_headers,
        session["id"],
        name="Sacs poubelle",
        quantity=3,
        unit_price_cents=250,
        vat_rate="20.00",
    )
    session = _add_expense(
        api_client,
        admin_headers,
        session["id"],
        kind="personal",
        name="Prélèvement patron",
        unit_price_cents=1000,
        vat_rate="0.00",
    )

    assert len(session["expenses"]) == 2
    assert session["expenses"][0]["total_cents"] == 750
    assert session["expenses"][0]["vat_rate"] == "20.00"
    assert session["expenses_total_cents"] == 1750
    assert session["expenses_professional_total_cents"] == 750
    assert session["expenses_personal_total_cents"] == 1000


def test_an_expense_can_be_changed_then_removed(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers)
    session = _open_session(api_client, admin_headers, cash_register["id"])
    session = _add_expense(api_client, admin_headers, session["id"], unit_price_cents=100)
    expense_id = session["expenses"][0]["id"]

    updated = api_client.put(
        f"{CASH_SESSIONS}/{session['id']}/expenses/{expense_id}",
        json={
            "kind": "personal",
            "name": "Corrigé",
            "quantity": 2,
            "unit_price_cents": 300,
            "vat_rate": "10.00",
        },
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["expenses_total_cents"] == 600
    assert updated.json()["expenses"][0]["name"] == "Corrigé"

    removed = api_client.delete(
        f"{CASH_SESSIONS}/{session['id']}/expenses/{expense_id}", headers=admin_headers
    )
    assert removed.status_code == 204
    assert (
        api_client.get(f"{CASH_SESSIONS}/{session['id']}", headers=admin_headers).json()["expenses"]
        == []
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "professional", "name": "Achat", "quantity": 0, "unit_price_cents": 100},
        {"kind": "professional", "name": "Achat", "quantity": 1, "unit_price_cents": -1},
        {
            "kind": "professional",
            "name": "Achat",
            "quantity": 1,
            "unit_price_cents": 1,
            "vat_rate": "101",
        },
        {"kind": "supplier", "name": "Achat", "quantity": 1, "unit_price_cents": 100},
        {"kind": "professional", "name": "  ", "quantity": 1, "unit_price_cents": 100},
    ],
)
def test_an_invalid_expense_is_rejected(
    api_client: TestClient,
    admin_headers: dict[str, str],
    payload: dict[str, Any],
) -> None:
    cash_register = _create_register(api_client, admin_headers)
    session = _open_session(api_client, admin_headers, cash_register["id"])

    response = api_client.post(
        f"{CASH_SESSIONS}/{session['id']}/expenses", json=payload, headers=admin_headers
    )

    assert response.status_code == 422


def test_closing_commits_the_count_to_the_register(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers, coins_1_euro=3)
    session = _open_session(api_client, admin_headers, cash_register["id"])
    _add_expense(api_client, admin_headers, session["id"], unit_price_cents=500)

    response = _close(
        api_client,
        admin_headers,
        session["id"],
        coins_1_euro=5,
        notes_10_euro=2,
        notes_50_euro=1,
    )

    assert response.status_code == 200, response.text
    closed = response.json()
    assert closed["is_open"] is False
    assert closed["closed_at"] is not None
    assert closed["closed_by_email"] == "admin@test.local"
    assert closed["closing_counts"]["notes_10_euro"] == 2
    assert closed["closing_total_cents"] == 7500
    # The expenses survive the closing: they are part of the session's record.
    assert closed["expenses_total_cents"] == 500

    register = api_client.get(CASH_REGISTERS, headers=admin_headers).json()[0]
    assert register["coins_1_euro"] == 5
    assert register["notes_10_euro"] == 2
    assert register["notes_50_euro"] == 1
    assert register["total_cents"] == 7500


def test_closing_requires_every_denomination(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers)
    session = _open_session(api_client, admin_headers, cash_register["id"])

    response = api_client.post(
        f"{CASH_SESSIONS}/{session['id']}/close",
        json={"closing_counts": {"coins_1_euro": 1}},
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_a_closed_session_is_frozen(api_client: TestClient, admin_headers: dict[str, str]) -> None:
    cash_register = _create_register(api_client, admin_headers)
    session = _open_session(api_client, admin_headers, cash_register["id"])
    closed = _close(api_client, admin_headers, session["id"]).json()

    assert _close(api_client, admin_headers, session["id"]).status_code == 409
    assert (
        api_client.put(
            f"{CASH_SESSIONS}/{session['id']}",
            json={"session_date": closed["session_date"], "opening_counts": _counts()},
            headers=admin_headers,
        ).status_code
        == 409
    )
    added = api_client.post(
        f"{CASH_SESSIONS}/{session['id']}/expenses",
        json={"kind": "professional", "name": "Trop tard", "unit_price_cents": 100},
        headers=admin_headers,
    )
    assert added.status_code == 409
    assert added.json()["code"] == "cash_session_closed"


def test_sessions_are_listed_and_filtered(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    first = _create_register(api_client, admin_headers, name="Caisse bar")
    second = _create_register(api_client, admin_headers, name="Caisse accueil")
    open_session = _open_session(api_client, admin_headers, first["id"])
    closed_session = _open_session(api_client, admin_headers, second["id"])
    _close(api_client, admin_headers, closed_session["id"], notes_5_euro=1)

    everything = api_client.get(CASH_SESSIONS, headers=admin_headers).json()
    assert {item["id"] for item in everything} == {open_session["id"], closed_session["id"]}

    only_open = api_client.get(f"{CASH_SESSIONS}?status=open", headers=admin_headers).json()
    assert [item["id"] for item in only_open] == [open_session["id"]]

    only_closed = api_client.get(f"{CASH_SESSIONS}?status=closed", headers=admin_headers).json()
    assert [item["id"] for item in only_closed] == [closed_session["id"]]

    of_first = api_client.get(
        f"{CASH_SESSIONS}?cash_register_id={first['id']}", headers=admin_headers
    ).json()
    assert [item["id"] for item in of_first] == [open_session["id"]]

    tomorrow = (_today() + timedelta(days=1)).isoformat()
    after_tomorrow = (_today() + timedelta(days=2)).isoformat()
    out_of_range = api_client.get(
        f"{CASH_SESSIONS}?from={tomorrow}&to={after_tomorrow}", headers=admin_headers
    ).json()
    assert out_of_range == []


def test_a_register_with_an_open_session_cannot_be_deactivated(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers)
    session = _open_session(api_client, admin_headers, cash_register["id"])

    blocked = api_client.delete(f"{CASH_REGISTERS}/{cash_register['id']}", headers=admin_headers)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "cash_register_has_open_session"

    _close(api_client, admin_headers, session["id"])
    assert (
        api_client.delete(
            f"{CASH_REGISTERS}/{cash_register['id']}", headers=admin_headers
        ).status_code
        == 204
    )


def test_deleting_a_session_is_reserved_to_admins_and_keeps_the_register(
    api_client: TestClient, admin_headers: dict[str, str], operator_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers, coins_1_euro=3)
    session = _open_session(api_client, admin_headers, cash_register["id"])
    closed = _close(api_client, admin_headers, session["id"], notes_5_euro=1).json()

    assert (
        api_client.delete(f"{CASH_SESSIONS}/{closed['id']}", headers=operator_headers).status_code
        == 403
    )
    assert (
        api_client.delete(f"{CASH_SESSIONS}/{closed['id']}", headers=admin_headers).status_code
        == 204
    )
    gone = api_client.get(f"{CASH_SESSIONS}/{closed['id']}", headers=admin_headers)
    assert gone.status_code == 404
    assert api_client.get(CASH_SESSIONS, headers=admin_headers).json() == []
    # The count committed at closing time is not rolled back.
    assert api_client.get(CASH_REGISTERS, headers=admin_headers).json()[0]["notes_5_euro"] == 1


def test_an_operator_can_run_a_session(
    api_client: TestClient, admin_headers: dict[str, str], operator_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers, coins_1_euro=1)

    session = _open_session(api_client, operator_headers, cash_register["id"])
    session = _add_expense(api_client, operator_headers, session["id"], unit_price_cents=50)
    closed = _close(api_client, operator_headers, session["id"], coins_1_euro=2)

    assert closed.status_code == 200
    assert closed.json()["opened_by_email"] == "operator@test.local"
    assert closed.json()["closed_by_email"] == "operator@test.local"
    assert closed.json()["expenses_total_cents"] == 50


def test_an_unknown_session_returns_404(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    unknown = uuid.uuid4()

    assert api_client.get(f"{CASH_SESSIONS}/{unknown}", headers=admin_headers).status_code == 404
    assert _close(api_client, admin_headers, str(unknown)).status_code == 404
    assert (
        api_client.post(
            f"{CASH_SESSIONS}/{unknown}/expenses",
            json={"kind": "professional", "name": "Achat", "unit_price_cents": 1},
            headers=admin_headers,
        ).status_code
        == 404
    )


def test_an_unknown_expense_returns_404(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers)
    session = _open_session(api_client, admin_headers, cash_register["id"])

    response = api_client.delete(
        f"{CASH_SESSIONS}/{session['id']}/expenses/{uuid.uuid4()}", headers=admin_headers
    )

    assert response.status_code == 404
    assert response.json()["code"] == "cash_expense_not_found"


def test_opening_on_a_deactivated_register_returns_404(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cash_register = _create_register(api_client, admin_headers)
    api_client.delete(f"{CASH_REGISTERS}/{cash_register['id']}", headers=admin_headers)

    response = api_client.post(
        CASH_SESSIONS, json={"cash_register_id": cash_register["id"]}, headers=admin_headers
    )

    assert response.status_code == 404
    assert response.json()["code"] == "cash_register_not_found"


def test_cash_sessions_require_authentication(api_client: TestClient) -> None:
    assert api_client.get(CASH_SESSIONS).status_code == 401
    assert (
        api_client.post(CASH_SESSIONS, json={"cash_register_id": str(uuid.uuid4())}).status_code
        == 401
    )
