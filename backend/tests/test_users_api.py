from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import ApiError
from app.models.user import User, UserRole
from app.schemas.user import UserUpdate
from app.services.users import update_user

USERS = "/api/v1/users"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
ME = "/api/v1/auth/me"


def _create_user(
    client: TestClient,
    headers: dict[str, str],
    *,
    email: str,
    role: str = "operator",
) -> dict[str, object]:
    response = client.post(
        USERS,
        headers=headers,
        json={"email": email, "role": role},
    )
    assert response.status_code == 201, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()


def _login(client: TestClient, *, email: str, password: str) -> dict[str, object]:
    response = client.post(LOGIN, data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def test_user_management_is_admin_only(
    api_client: TestClient,
    admin_headers: dict[str, str],
    operator_headers: dict[str, str],
) -> None:
    assert api_client.get(USERS, headers=admin_headers).status_code == 200
    assert api_client.get(USERS, headers=operator_headers).status_code == 403
    assert api_client.post(USERS, json={"email": "new@example.com"}).status_code == 401
    assert (
        api_client.post(
            USERS,
            headers=operator_headers,
            json={"email": "new@example.com"},
        ).status_code
        == 403
    )


def test_create_user_returns_a_one_time_password_and_supports_login(
    api_client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    created = _create_user(
        api_client,
        admin_headers,
        email="Nouvel.Operateur@Example.com",
    )
    password = str(created["temporary_password"])

    assert created["email"] == "nouvel.operateur@example.com"
    assert created["role"] == "operator"
    assert password
    assert "hashed_password" not in created

    login = _login(
        api_client,
        email="nouvel.operateur@example.com",
        password=password,
    )
    assert login["access_token"]

    listed = api_client.get(USERS, headers=admin_headers)
    assert listed.status_code == 200
    for user in listed.json():
        assert "hashed_password" not in user
        assert "temporary_password" not in user


def test_create_user_rejects_duplicate_email_with_different_case(
    api_client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    _create_user(api_client, admin_headers, email="Unique@Example.com")

    response = api_client.post(
        USERS,
        headers=admin_headers,
        json={"email": "unique@example.com"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "user_email_taken"


def test_create_and_update_payloads_are_validated(
    api_client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    assert (
        api_client.post(USERS, headers=admin_headers, json={"email": "not-an-email"}).status_code
        == 422
    )

    created = _create_user(api_client, admin_headers, email="valid@example.com")
    user_id = str(created["id"])

    assert (
        api_client.patch(
            f"{USERS}/{user_id}",
            headers=admin_headers,
            json={},
        ).status_code
        == 422
    )
    assert (
        api_client.patch(
            f"{USERS}/{user_id}",
            headers=admin_headers,
            json={"role": None},
        ).status_code
        == 422
    )


def test_role_change_invalidates_existing_access_token(
    api_client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    created = _create_user(api_client, admin_headers, email="promote@example.com")
    user_id = str(created["id"])
    password = str(created["temporary_password"])
    login = _login(api_client, email="promote@example.com", password=password)
    old_access = str(login["access_token"])

    assert api_client.get(ME, headers={"Authorization": f"Bearer {old_access}"}).status_code == 200

    promoted = api_client.patch(
        f"{USERS}/{user_id}",
        headers=admin_headers,
        json={"role": "admin"},
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["role"] == "admin"

    assert api_client.get(ME, headers={"Authorization": f"Bearer {old_access}"}).status_code == 401
    new_login = _login(api_client, email="promote@example.com", password=password)
    me = api_client.get(
        ME,
        headers={"Authorization": f"Bearer {new_login['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["role"] == "admin"


def test_deactivation_revokes_access_and_refresh_tokens(
    api_client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    created = _create_user(api_client, admin_headers, email="deactivate@example.com")
    user_id = str(created["id"])
    password = str(created["temporary_password"])
    login = _login(api_client, email="deactivate@example.com", password=password)
    access = str(login["access_token"])
    refresh = str(login["refresh_token"])

    response = api_client.patch(
        f"{USERS}/{user_id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False

    assert api_client.get(ME, headers={"Authorization": f"Bearer {access}"}).status_code == 401
    assert api_client.post(REFRESH, json={"refresh_token": refresh}).status_code == 401
    assert (
        api_client.post(
            LOGIN, data={"username": "deactivate@example.com", "password": password}
        ).status_code
        == 401
    )


def test_password_reset_revokes_old_credentials(
    api_client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    created = _create_user(api_client, admin_headers, email="reset@example.com")
    user_id = str(created["id"])
    old_password = str(created["temporary_password"])
    login = _login(api_client, email="reset@example.com", password=old_password)
    old_access = str(login["access_token"])
    old_refresh = str(login["refresh_token"])

    reset = api_client.post(f"{USERS}/{user_id}/reset-password", headers=admin_headers)
    assert reset.status_code == 200, reset.text
    assert reset.headers["cache-control"] == "no-store"
    new_password = str(reset.json()["temporary_password"])
    assert new_password != old_password

    assert api_client.get(ME, headers={"Authorization": f"Bearer {old_access}"}).status_code == 401
    assert api_client.post(REFRESH, json={"refresh_token": old_refresh}).status_code == 401
    assert (
        api_client.post(
            LOGIN, data={"username": "reset@example.com", "password": old_password}
        ).status_code
        == 401
    )
    assert (
        api_client.post(
            LOGIN, data={"username": "reset@example.com", "password": new_password}
        ).status_code
        == 200
    )


def test_admin_cannot_lock_themselves_out(
    api_client: TestClient,
    admin_headers: dict[str, str],
) -> None:
    me = api_client.get(ME, headers=admin_headers).json()
    admin_id = str(me["id"])

    role_change = api_client.patch(
        f"{USERS}/{admin_id}",
        headers=admin_headers,
        json={"role": "operator"},
    )
    deactivation = api_client.patch(
        f"{USERS}/{admin_id}",
        headers=admin_headers,
        json={"is_active": False},
    )

    assert role_change.status_code == 409
    assert role_change.json()["code"] == "user_self_lockout"
    assert deactivation.status_code == 409
    assert deactivation.json()["code"] == "user_self_lockout"


def test_last_admin_guard_is_enforced_at_the_service_layer(
    admin_headers: dict[str, str],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    del admin_headers

    async def run() -> None:
        async with session_factory() as session:
            target = await session.scalar(select(User).where(User.email == "admin@test.local"))
            assert target is not None
            actor = SimpleNamespace(id=uuid.uuid4())
            with pytest.raises(ApiError) as excinfo:
                await update_user(
                    session,
                    actor=actor,  # type: ignore[arg-type]
                    target_id=target.id,
                    payload=UserUpdate(role=UserRole.OPERATOR),
                )
            assert excinfo.value.code == "user_last_admin"

    asyncio.run(run())
