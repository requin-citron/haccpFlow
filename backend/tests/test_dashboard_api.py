from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.cash_register import DENOMINATION_FIELDS
from app.models.dashboard_layout import DashboardLayout

pytestmark = pytest.mark.integration

CASH_REGISTERS = "/api/v1/cash-registers"
CASH_SESSIONS = "/api/v1/cash-sessions"
DASHBOARD_REVENUE = "/api/v1/dashboard/revenue"
DASHBOARD_LAYOUT = "/api/v1/dashboard/layout"


def _counts(**overrides: int) -> dict[str, int]:
    counts = dict.fromkeys(DENOMINATION_FIELDS, 0)
    counts.update(overrides)
    return counts


def _today() -> date:
    return datetime.now(UTC).date()


def _register(
    api_client: TestClient,
    headers: dict[str, str],
    *,
    name: str,
    kind: str = "cash",
    **counts: int,
) -> dict[str, Any]:
    response = api_client.post(
        CASH_REGISTERS,
        json={"name": name, "kind": kind, **counts},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _open(
    api_client: TestClient,
    headers: dict[str, str],
    register_id: str,
    session_date: date | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"cash_register_id": register_id}
    if session_date is not None:
        payload["session_date"] = session_date.isoformat()
    response = api_client.post(CASH_SESSIONS, json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _close_cash(
    api_client: TestClient,
    headers: dict[str, str],
    session_id: str,
    **counts: int,
) -> dict[str, Any]:
    response = api_client.post(
        f"{CASH_SESSIONS}/{session_id}/close",
        json={"closing_counts": _counts(**counts)},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _close_amount(
    api_client: TestClient,
    headers: dict[str, str],
    session_id: str,
    amount_cents: int,
) -> dict[str, Any]:
    response = api_client.post(
        f"{CASH_SESSIONS}/{session_id}/close",
        json={"collected_amount_cents": amount_cents},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _expense(
    api_client: TestClient,
    headers: dict[str, str],
    session_id: str,
    *,
    kind: str,
    amount_cents: int,
) -> None:
    response = api_client.post(
        f"{CASH_SESSIONS}/{session_id}/expenses",
        json={
            "kind": kind,
            "name": "Dépense",
            "quantity": 1,
            "unit_price_cents": amount_cents,
            "vat_rate": "0.00",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text


def _revenue(
    api_client: TestClient,
    headers: dict[str, str],
    from_date: date,
    to_date: date,
) -> dict[str, Any]:
    response = api_client.get(
        f"{DASHBOARD_REVENUE}?from={from_date.isoformat()}&to={to_date.isoformat()}",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_cash_revenue_uses_float_change_and_adds_expenses(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    register = _register(
        api_client,
        admin_headers,
        name="Caisse CA",
        notes_10_euro=1,
    )
    session = _open(api_client, admin_headers, register["id"])
    _expense(api_client, admin_headers, session["id"], kind="professional", amount_cents=200)
    _expense(api_client, admin_headers, session["id"], kind="personal", amount_cents=300)
    _close_cash(api_client, admin_headers, session["id"], notes_20_euro=1)

    today = _today()
    revenue = _revenue(api_client, admin_headers, today, today)

    assert revenue["from"] == today.isoformat()
    assert revenue["to"] == today.isoformat()
    # 2000 closing - 1000 opening + 500 expenses
    assert revenue["cash_cents"] == 1500
    assert revenue["cash_expenses_cents"] == 500
    assert revenue["cheque_cents"] == 0
    assert revenue["card_cents"] == 0
    assert revenue["total_cents"] == 1500
    assert revenue["closed_session_count"] == 1


def test_cheque_and_card_revenue_use_collected_amounts(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    cheque = _register(api_client, admin_headers, name="Chèques CA", kind="cheque")
    card = _register(api_client, admin_headers, name="Cartes CA", kind="card")
    cheque_session = _open(api_client, admin_headers, cheque["id"])
    card_session = _open(api_client, admin_headers, card["id"])
    _close_amount(api_client, admin_headers, cheque_session["id"], 1250)
    _close_amount(api_client, admin_headers, card_session["id"], 2750)

    today = _today()
    revenue = _revenue(api_client, admin_headers, today, today)

    assert revenue["cash_cents"] == 0
    assert revenue["cheque_cents"] == 1250
    assert revenue["card_cents"] == 2750
    assert revenue["total_cents"] == 4000
    assert revenue["closed_session_count"] == 2


def test_a_negative_cash_result_is_preserved(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    register = _register(
        api_client,
        admin_headers,
        name="Caisse négative",
        notes_10_euro=1,
    )
    session = _open(api_client, admin_headers, register["id"])
    _expense(api_client, admin_headers, session["id"], kind="professional", amount_cents=100)
    _close_cash(api_client, admin_headers, session["id"])

    today = _today()
    revenue = _revenue(api_client, admin_headers, today, today)

    # 0 closing - 1000 opening + 100 expenses
    assert revenue["cash_cents"] == -900
    assert revenue["total_cents"] == -900


def test_revenue_uses_inclusive_bounds_and_excludes_open_or_deleted_sessions(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    today = _today()
    yesterday = today - timedelta(days=1)

    included = _register(api_client, admin_headers, name="Caisse incluse")
    included_session = _open(api_client, admin_headers, included["id"], yesterday)
    _close_cash(api_client, admin_headers, included_session["id"], notes_5_euro=3)

    open_register = _register(api_client, admin_headers, name="Caisse ouverte")
    _open(api_client, admin_headers, open_register["id"], today)

    deleted_register = _register(api_client, admin_headers, name="Caisse supprimée")
    deleted_session = _open(api_client, admin_headers, deleted_register["id"], today)
    _close_cash(api_client, admin_headers, deleted_session["id"], notes_10_euro=5)
    assert (
        api_client.delete(
            f"{CASH_SESSIONS}/{deleted_session['id']}",
            headers=admin_headers,
        ).status_code
        == 204
    )

    outside_register = _register(api_client, admin_headers, name="Caisse hors période")
    outside_session = _open(
        api_client,
        admin_headers,
        outside_register["id"],
        today - timedelta(days=2),
    )
    _close_cash(api_client, admin_headers, outside_session["id"], notes_20_euro=4)

    revenue = _revenue(api_client, admin_headers, yesterday, today)

    assert revenue["cash_cents"] == 1500
    assert revenue["total_cents"] == 1500
    assert revenue["closed_session_count"] == 1


def test_revenue_keeps_history_after_register_deactivation(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    register = _register(api_client, admin_headers, name="Caisse historique")
    session = _open(api_client, admin_headers, register["id"])
    _close_cash(api_client, admin_headers, session["id"], notes_5_euro=4)
    assert (
        api_client.delete(
            f"{CASH_REGISTERS}/{register['id']}",
            headers=admin_headers,
        ).status_code
        == 204
    )

    today = _today()
    revenue = _revenue(api_client, admin_headers, today, today)

    assert revenue["cash_cents"] == 2000
    assert revenue["closed_session_count"] == 1


def test_an_empty_period_returns_zero_revenue(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    today = _today()
    revenue = _revenue(api_client, admin_headers, today, today)

    assert revenue == {
        "from": today.isoformat(),
        "to": today.isoformat(),
        "total_cents": 0,
        "cash_cents": 0,
        "cheque_cents": 0,
        "card_cents": 0,
        "cash_expenses_cents": 0,
        "closed_session_count": 0,
    }


def test_an_invalid_revenue_range_is_rejected(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    today = _today()
    yesterday = today - timedelta(days=1)
    response = api_client.get(
        f"{DASHBOARD_REVENUE}?from={today.isoformat()}&to={yesterday.isoformat()}",
        headers=admin_headers,
    )

    assert response.status_code == 422
    assert response.json()["code"] == "dashboard_range_invalid"


def test_the_default_layout_is_virtual(
    api_client: TestClient,
    admin_headers: dict[str, str],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    response = api_client.get(DASHBOARD_LAYOUT, headers=admin_headers)

    assert response.status_code == 200
    assert response.json() == {
        "widgets": [
            {
                "key": "revenue",
                "column_start": 1,
                "width_columns": 12,
                "row_span": 6,
            }
        ]
    }

    async def count_layouts() -> int:
        async with session_factory() as db:
            return int(await db.scalar(select(func.count()).select_from(DashboardLayout)) or 0)

    import asyncio

    assert asyncio.run(count_layouts()) == 0


def test_a_layout_can_be_saved_reloaded_and_emptied(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    saved = api_client.put(
        DASHBOARD_LAYOUT,
        json={
            "widgets": [
                {
                    "key": "revenue",
                    "column_start": 4,
                    "width_columns": 6,
                    "row_span": 7,
                }
            ]
        },
        headers=admin_headers,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["widgets"][0]["width_columns"] == 6
    assert saved.json()["widgets"][0]["row_span"] == 7

    loaded = api_client.get(DASHBOARD_LAYOUT, headers=admin_headers)
    assert loaded.json() == saved.json()

    emptied = api_client.put(DASHBOARD_LAYOUT, json={"widgets": []}, headers=admin_headers)
    assert emptied.status_code == 200
    assert emptied.json() == {"widgets": []}
    assert api_client.get(DASHBOARD_LAYOUT, headers=admin_headers).json() == {"widgets": []}


def test_layouts_are_isolated_per_user(
    api_client: TestClient,
    admin_headers: dict[str, str],
    operator_headers: dict[str, str],
) -> None:
    admin_layout = {
        "widgets": [
            {
                "key": "revenue",
                "column_start": 1,
                "width_columns": 5,
                "row_span": 6,
            }
        ]
    }
    operator_layout = {
        "widgets": [
            {
                "key": "revenue",
                "column_start": 3,
                "width_columns": 8,
                "row_span": 8,
            }
        ]
    }
    assert (
        api_client.put(DASHBOARD_LAYOUT, json=admin_layout, headers=admin_headers).status_code
        == 200
    )
    assert (
        api_client.put(
            DASHBOARD_LAYOUT,
            json=operator_layout,
            headers=operator_headers,
        ).status_code
        == 200
    )

    assert api_client.get(DASHBOARD_LAYOUT, headers=admin_headers).json() == admin_layout
    assert api_client.get(DASHBOARD_LAYOUT, headers=operator_headers).json() == operator_layout


@pytest.mark.parametrize(
    "widget",
    [
        {"key": "unknown", "column_start": 1, "width_columns": 6},
        {"key": "revenue", "column_start": 0, "width_columns": 6},
        {"key": "revenue", "column_start": 8, "width_columns": 6},
        {"key": "revenue", "column_start": 1, "width_columns": 2},
        {"key": "revenue", "column_start": 1, "width_columns": 13},
        {"key": "revenue", "column_start": 1, "width_columns": 6, "row_span": 2},
    ],
)
def test_an_invalid_layout_widget_is_rejected(
    api_client: TestClient,
    admin_headers: dict[str, str],
    widget: dict[str, Any],
) -> None:
    response = api_client.put(
        DASHBOARD_LAYOUT,
        json={"widgets": [widget]},
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_duplicate_layout_widgets_are_rejected(
    api_client: TestClient, admin_headers: dict[str, str]
) -> None:
    widget = {"key": "revenue", "column_start": 1, "width_columns": 6}
    response = api_client.put(
        DASHBOARD_LAYOUT,
        json={"widgets": [widget, widget]},
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_dashboard_routes_require_authentication(api_client: TestClient) -> None:
    today = _today().isoformat()

    assert api_client.get(f"{DASHBOARD_REVENUE}?from={today}&to={today}").status_code == 401
    assert api_client.get(DASHBOARD_LAYOUT).status_code == 401
    assert api_client.put(DASHBOARD_LAYOUT, json={"widgets": []}).status_code == 401
