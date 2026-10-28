from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.core.security import generate_temporary_password, hash_password
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole, normalize_email
from app.schemas.user import UserUpdate


async def get_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> User:
    query = select(User).where(User.id == user_id)
    if for_update:
        query = query.with_for_update()
    user = await db.scalar(query)
    if user is None:
        raise ApiError(404, "user_not_found", "User not found")
    return user


async def _email_is_taken(db: AsyncSession, email: str) -> bool:
    found = await db.scalar(select(User.id).where(func.lower(User.email) == normalize_email(email)))
    return found is not None


async def _count_other_active_admins(
    db: AsyncSession,
    *,
    excluded_user_id: uuid.UUID,
) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
            User.id != excluded_user_id,
        )
    )
    return int(count or 0)


async def _revoke_refresh_tokens(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    role: UserRole,
) -> tuple[User, str]:
    normalized = normalize_email(email)
    if await _email_is_taken(db, normalized):
        raise ApiError(409, "user_email_taken", "A user with this email already exists")

    temporary_password = generate_temporary_password()
    user = User(
        email=normalized,
        hashed_password=hash_password(temporary_password),
        role=role,
        is_active=True,
        auth_version=0,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ApiError(
            409,
            "user_email_taken",
            "A user with this email already exists",
        ) from exc

    await db.refresh(user)
    return user, temporary_password


async def update_user(
    db: AsyncSession,
    *,
    actor: User,
    target_id: uuid.UUID,
    payload: UserUpdate,
) -> User:
    target = await get_user(db, target_id, for_update=True)
    if "role" in payload.model_fields_set:
        assert payload.role is not None
        new_role: UserRole = payload.role
    else:
        new_role = target.role
    if "is_active" in payload.model_fields_set:
        assert payload.is_active is not None
        new_active: bool = payload.is_active
    else:
        new_active = bool(target.is_active)

    if target.id == actor.id and (new_role != target.role or new_active != target.is_active):
        raise ApiError(
            409,
            "user_self_lockout",
            "An administrator cannot change their own role or deactivate their own account",
        )

    removes_active_admin = (
        target.role is UserRole.ADMIN
        and target.is_active
        and (new_role is not UserRole.ADMIN or not new_active)
    )
    if (
        removes_active_admin
        and await _count_other_active_admins(db, excluded_user_id=target.id) == 0
    ):
        raise ApiError(
            409,
            "user_last_admin",
            "The last active administrator cannot be demoted or deactivated",
        )

    if new_role == target.role and new_active == target.is_active:
        return target

    target.role = new_role
    target.is_active = new_active
    target.auth_version += 1
    if not new_active:
        await _revoke_refresh_tokens(db, target.id)

    try:
        await db.commit()
    except BaseException:
        await db.rollback()
        raise

    await db.refresh(target)
    return target


async def reset_user_password(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> str:
    user = await get_user(db, user_id, for_update=True)
    temporary_password = generate_temporary_password()
    user.hashed_password = hash_password(temporary_password)
    user.auth_version += 1
    await _revoke_refresh_tokens(db, user.id)
    try:
        await db.commit()
    except BaseException:
        await db.rollback()
        raise

    await db.refresh(user)
    return temporary_password
