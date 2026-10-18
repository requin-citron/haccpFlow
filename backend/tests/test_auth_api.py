from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import hash_password, hash_refresh_token
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"


def _create_user(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    email: str = "auth-test@example.com",
    password: str = "correct horse battery staple",
) -> None:
    async def run() -> None:
        async with session_factory() as session:
            session.add(
                User(
                    email=email,
                    hashed_password=hash_password(password),
                    role=UserRole.ADMIN,
                    is_active=True,
                )
            )
            await session.commit()

    asyncio.run(run())


def _login(client: TestClient, *, email: str, password: str) -> dict[str, object]:
    response = client.post(LOGIN, data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def _expire_rotation_grace(
    session_factory: async_sessionmaker[AsyncSession],
    refresh_token: str,
) -> None:
    async def run() -> None:
        async with session_factory() as session:
            await session.execute(
                update(RefreshToken)
                .where(RefreshToken.token_hash == hash_refresh_token(refresh_token))
                .values(revoked_at=datetime.now(UTC) - timedelta(seconds=30))
            )
            await session.commit()

    asyncio.run(run())


def test_login_returns_both_token_lifetimes(
    api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _create_user(session_factory)

    body = _login(
        api_client,
        email="auth-test@example.com",
        password="correct horse battery staple",
    )

    assert body["expires_in"] > 0
    assert body["refresh_expires_in"] > body["expires_in"]


def test_rotated_refresh_token_can_be_reused_during_the_grace_window(
    api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _create_user(session_factory)
    login = _login(
        api_client,
        email="auth-test@example.com",
        password="correct horse battery staple",
    )
    old_refresh = str(login["refresh_token"])

    first = api_client.post(REFRESH, json={"refresh_token": old_refresh})
    second = api_client.post(REFRESH, json={"refresh_token": old_refresh})

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["refresh_token"] != second.json()["refresh_token"]


def test_replay_after_the_grace_window_revokes_active_tokens(
    api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _create_user(session_factory)
    login = _login(
        api_client,
        email="auth-test@example.com",
        password="correct horse battery staple",
    )
    old_refresh = str(login["refresh_token"])
    first = api_client.post(REFRESH, json={"refresh_token": old_refresh})
    assert first.status_code == 200
    newest_refresh = str(first.json()["refresh_token"])

    _expire_rotation_grace(session_factory, old_refresh)

    replay = api_client.post(REFRESH, json={"refresh_token": old_refresh})
    assert replay.status_code == 401
    assert api_client.post(REFRESH, json={"refresh_token": newest_refresh}).status_code == 401


def test_logout_revokes_the_refresh_token(
    api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _create_user(session_factory)
    login = _login(
        api_client,
        email="auth-test@example.com",
        password="correct horse battery staple",
    )
    refresh_token = str(login["refresh_token"])

    assert api_client.post(LOGOUT, json={"refresh_token": refresh_token}).status_code == 204
    assert api_client.post(REFRESH, json={"refresh_token": refresh_token}).status_code == 401


def test_logout_revokes_the_whole_rotation_family(
    api_client: TestClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _create_user(session_factory)
    login = _login(
        api_client,
        email="auth-test@example.com",
        password="correct horse battery staple",
    )
    old_refresh = str(login["refresh_token"])
    first = api_client.post(REFRESH, json={"refresh_token": old_refresh})
    second = api_client.post(REFRESH, json={"refresh_token": old_refresh})
    assert first.status_code == 200
    assert second.status_code == 200

    assert api_client.post(LOGOUT, json={"refresh_token": old_refresh}).status_code == 204
    assert (
        api_client.post(REFRESH, json={"refresh_token": first.json()["refresh_token"]}).status_code
        == 401
    )
    assert (
        api_client.post(REFRESH, json={"refresh_token": second.json()["refresh_token"]}).status_code
        == 401
    )
