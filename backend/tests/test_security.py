from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.config import Settings
from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

# PyJWT warns below 32 bytes for HS256, so tests use realistic-length keys.
SECRET_A = "unit-test-secret-key-aaaaaaaaaaaaaa"
SECRET_B = "unit-test-secret-key-bbbbbbbbbbbbbb"


def _settings(secret_key: str) -> Settings:
    return Settings(
        secret_key=secret_key,
        database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
        _env_file=None,
    )


def test_password_roundtrip() -> None:
    hashed = hash_password("s3cret-password")

    assert hashed != "s3cret-password"
    assert verify_password("s3cret-password", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_password_verification_rejects_a_malformed_hash() -> None:
    assert verify_password("whatever", "not-an-argon2-hash") is False


def test_access_token_roundtrip() -> None:
    settings = _settings(SECRET_A)

    token, expires_in = create_access_token(settings, subject="user-1", role="admin")
    payload = decode_access_token(settings, token)

    assert payload["sub"] == "user-1"
    assert payload["role"] == "admin"
    assert payload["type"] == "access"
    assert expires_in == 3600


def test_access_token_rejects_another_signature() -> None:
    token, _ = create_access_token(_settings(SECRET_A), subject="user-1", role="admin")

    with pytest.raises(TokenError):
        decode_access_token(_settings(SECRET_B), token)


def test_expired_access_token_is_rejected() -> None:
    settings = _settings(SECRET_A)
    issued_at = datetime.now(UTC) - timedelta(hours=2)

    token, _ = create_access_token(settings, subject="user-1", role="admin", now=issued_at)

    with pytest.raises(TokenError):
        decode_access_token(settings, token)


def test_refresh_token_hash_is_opaque_and_deterministic() -> None:
    token = generate_refresh_token()

    assert token != hash_refresh_token(token)
    assert len(hash_refresh_token(token)) == 64
    assert hash_refresh_token(token) == hash_refresh_token(token)


def test_refresh_tokens_are_unique() -> None:
    assert generate_refresh_token() != generate_refresh_token()
