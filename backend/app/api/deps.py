from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import API_V1_PREFIX, get_settings
from app.core.errors import ApiError
from app.core.security import TokenError, decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole

DbSession = Annotated[AsyncSession, Depends(get_db)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{API_V1_PREFIX}/auth/login")

_UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    try:
        payload = decode_access_token(get_settings(), token)
    except TokenError as exc:
        raise ApiError(
            401,
            "invalid_token",
            "Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        ) from exc

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise ApiError(
            401,
            "invalid_token",
            "Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        )

    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise ApiError(
            401,
            "invalid_token",
            "Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        ) from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise ApiError(
            401,
            "invalid_token",
            "Could not validate credentials",
            headers=_UNAUTHORIZED_HEADERS,
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: UserRole) -> Callable[[CurrentUser], User]:
    """Build a dependency that only lets the given roles through."""

    allowed = frozenset(roles)

    def dependency(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise ApiError(403, "insufficient_role", "Insufficient permissions")
        return user

    return dependency
