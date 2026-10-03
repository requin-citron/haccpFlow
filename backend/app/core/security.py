from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error

from app.config import Settings

ACCESS_TOKEN_TYPE: Final = "access"
REFRESH_TOKEN_BYTES: Final = 48

_hasher = PasswordHasher()


class TokenError(Exception):
    """Raised when a token cannot be trusted."""


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return _hasher.verify(hashed_password, password)
    except (Argon2Error, ValueError):
        return False


def create_access_token(
    settings: Settings,
    *,
    subject: str,
    role: str,
    now: datetime | None = None,
) -> tuple[str, int]:
    """Return the encoded access token and its lifetime in seconds."""

    issued_at = now or datetime.now(UTC)
    lifetime = timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": ACCESS_TOKEN_TYPE,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + lifetime).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    encoded = jwt.encode(
        payload,
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return encoded, int(lifetime.total_seconds())


def decode_access_token(settings: Settings, token: str) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise TokenError("unexpected token type")
    return payload


def generate_refresh_token() -> str:
    """Opaque, high-entropy refresh token. Only its hash is persisted."""

    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
