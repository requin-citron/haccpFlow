from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


def _make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "secret_key": "unit-test-secret",
        "database_url": "postgresql+asyncpg://user:pass@localhost:5432/db",
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)


def test_required_values_come_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "from-env")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://env/db")

    settings = Settings(_env_file=None)

    assert settings.secret_key.get_secret_value() == "from-env"
    assert settings.database_url == "postgresql+asyncpg://env/db"


def test_missing_required_values_are_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_defaults_are_stable() -> None:
    settings = _make_settings()

    assert settings.access_token_expire_minutes == 60
    assert settings.refresh_token_expire_days == 30
    assert settings.jwt_algorithm == "HS256"
    assert settings.docs_enabled is True
    assert settings.is_production is False


def test_cors_origins_are_split_and_trimmed() -> None:
    settings = _make_settings(cors_origins="http://a.test, http://b.test ,")

    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]


def test_docs_can_be_disabled_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCS_ENABLED", "false")

    assert _make_settings().docs_enabled is False
