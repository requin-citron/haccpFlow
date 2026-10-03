from __future__ import annotations

import os

import pytest

from app.config import Settings

# The app factory reads the settings when `app.main` is imported, which happens
# after this file. Unit tests never talk to a real service, so the two required
# values are provided here.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")

TEST_DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/db"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        secret_key="unit-test-secret-key",
        database_url=TEST_DATABASE_URL,
        _env_file=None,
    )
