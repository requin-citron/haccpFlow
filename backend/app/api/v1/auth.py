from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, update

from app.api.deps import CurrentUser, DbSession
from app.config import get_settings
from app.core.errors import ApiError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User, normalize_email
from app.schemas.auth import RefreshRequest, TokenPair
from app.schemas.user import UserRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _invalid_credentials() -> ApiError:
    return ApiError(401, "invalid_credentials", "Incorrect email or password")


def _invalid_refresh_token() -> ApiError:
    return ApiError(401, "invalid_refresh_token", "Invalid or expired refresh token")


async def _issue_token_pair(db: DbSession, user: User) -> TokenPair:
    settings = get_settings()
    access_token, expires_in = create_access_token(
        settings,
        subject=str(user.id),
        role=user.role.value,
    )

    refresh_token = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    await db.commit()

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@router.post("/login", response_model=TokenPair)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> TokenPair:
    email = normalize_email(form.username)
    user = await db.scalar(select(User).where(User.email == email))
    if (
        user is None
        or not user.is_active
        or not verify_password(form.password, user.hashed_password)
    ):
        raise _invalid_credentials()
    return await _issue_token_pair(db, user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, db: DbSession) -> TokenPair:
    token_hash = hash_refresh_token(body.refresh_token)
    stored = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
    )
    if stored is None:
        raise _invalid_refresh_token()

    now = datetime.now(UTC)
    if stored.revoked_at is not None:
        # A revoked token is being replayed: revoke the whole family.
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == stored.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.commit()
        logger.warning("Refresh token replay detected for user %s", stored.user_id)
        raise _invalid_refresh_token()

    if stored.expires_at <= now:
        raise _invalid_refresh_token()

    user = await db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise _invalid_refresh_token()

    settings = get_settings()
    new_token = generate_refresh_token()
    new_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(new_token),
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(new_record)
    await db.flush()

    stored.revoked_at = now
    stored.replaced_by_id = new_record.id
    await db.commit()

    access_token, expires_in = create_access_token(
        settings,
        subject=str(user.id),
        role=user.role.value,
    )
    return TokenPair(
        access_token=access_token,
        refresh_token=new_token,
        expires_in=expires_in,
    )


@router.post("/logout", status_code=204)
async def logout(body: RefreshRequest, db: DbSession) -> None:
    token_hash = hash_refresh_token(body.refresh_token)
    stored = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
    )
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        await db.commit()


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> User:
    return user
