from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import Settings, get_settings
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole

# The app factory reads the settings when `app.main` is imported, which happens
# after this file. Unit tests never talk to a real service, so the two required
# values are provided here.
os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-with-32-bytes-minimum")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
UNIT_DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/db"

TABLE_CLEANUP = "TRUNCATE equipment, refresh_tokens, users CASCADE"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        secret_key="unit-test-secret-key",
        database_url=UNIT_DATABASE_URL,
        _env_file=None,
    )


# --- Integration database --------------------------------------------------


@pytest.fixture(scope="session")
def integration_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip(
            "TEST_DATABASE_URL is not set: run `docker compose up -d db` then "
            "export TEST_DATABASE_URL=postgresql+asyncpg://haccp:<password>@localhost:5432/haccp_test"
        )
    return url


@pytest.fixture(scope="session")
def prepared_database(integration_database_url: str) -> Iterator[str]:
    # Each pytest session gets its own database: two runs (or a run started
    # while another is finishing) can never truncate each other's rows.
    base = make_url(integration_database_url)
    if not base.database:
        pytest.skip("TEST_DATABASE_URL must include a database name")
    url = base.set(database=f"{base.database}_{os.getpid()}").render_as_string(hide_password=False)

    try:
        asyncio.run(_ensure_database_exists(url))
    except Exception as exc:
        pytest.skip(f"Cannot reach the integration database: {exc}")
    _run_migrations(url)
    try:
        yield url
    finally:
        asyncio.run(_drop_database(url))


@pytest.fixture
def integration_engine(prepared_database: str) -> Iterator[AsyncEngine]:
    # No pooling: each helper opens its own connection, so the several event
    # loops created by asyncio.run() never share a connection.
    engine = create_async_engine(prepared_database, poolclass=NullPool)
    try:
        yield engine
    finally:
        asyncio.run(engine.dispose())


@pytest.fixture
def session_factory(integration_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(integration_engine, expire_on_commit=False)


@pytest.fixture
def clean_database(integration_engine: AsyncEngine) -> None:
    async def _run() -> None:
        async with integration_engine.begin() as connection:
            await connection.execute(text(TABLE_CLEANUP))

    asyncio.run(_run())


@pytest.fixture
def api_client(
    clean_database: None,
    session_factory: async_sessionmaker[AsyncSession],
) -> Iterator[TestClient]:
    from app.db.session import get_db
    from app.main import create_app

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers(
    clean_database: None,
    session_factory: async_sessionmaker[AsyncSession],
) -> dict[str, str]:
    return _auth_headers(session_factory, "admin@test.local", UserRole.ADMIN)


@pytest.fixture
def operator_headers(
    clean_database: None, session_factory: async_sessionmaker[AsyncSession]
) -> dict[str, str]:
    return _auth_headers(session_factory, "operator@test.local", UserRole.OPERATOR)


# --- Integration helpers ---------------------------------------------------


async def _ensure_database_exists(url: str) -> None:
    target = make_url(url)
    engine = create_async_engine(
        target.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
        connect_args={"timeout": 5},
    )
    try:
        async with engine.connect() as connection:
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": target.database},
            )
            if not exists:
                await connection.execute(text(f'CREATE DATABASE "{target.database}"'))
    finally:
        await engine.dispose()


async def _drop_database(url: str) -> None:
    target = make_url(url)
    engine = create_async_engine(
        target.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
        connect_args={"timeout": 5},
    )
    try:
        async with engine.connect() as connection:
            statement = f'DROP DATABASE IF EXISTS "{target.database}" WITH (FORCE)'
            await connection.execute(text(statement))
    finally:
        await engine.dispose()


def _run_migrations(url: str) -> None:
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    try:
        config = AlembicConfig(str(BACKEND_ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()


def _auth_headers(
    session_factory: async_sessionmaker[AsyncSession],
    email: str,
    role: UserRole,
) -> dict[str, str]:
    async def _create_user() -> uuid.UUID:
        async with session_factory() as session:
            user = User(
                email=email,
                hashed_password=hash_password("not-used-by-these-tests"),
                role=role,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            return user.id

    user_id = asyncio.run(_create_user())
    token, _ = create_access_token(get_settings(), subject=str(user_id), role=role.value)
    return {"Authorization": f"Bearer {token}"}
