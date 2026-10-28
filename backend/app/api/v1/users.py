from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select

from app.api.deps import DbSession, require_role
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate,
    UserCreated,
    UserPasswordReset,
    UserRead,
    UserUpdate,
)
from app.services.users import create_user, delete_user, reset_user_password, update_user

router = APIRouter(prefix="/users", tags=["users"])

AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]


def _read(user: User) -> UserRead:
    return UserRead.model_validate(user)


def _created(user: User, temporary_password: str) -> UserCreated:
    return UserCreated(
        **_read(user).model_dump(),
        temporary_password=temporary_password,
    )


@router.get("", response_model=list[UserRead])
async def list_users(db: DbSession, _: AdminUser) -> list[UserRead]:
    result = await db.scalars(select(User).order_by(User.email))
    return [_read(user) for user in result]


@router.post(
    "",
    response_model=UserCreated,
    status_code=201,
)
async def create_user_account(
    payload: UserCreate,
    db: DbSession,
    _: AdminUser,
    response: Response,
) -> UserCreated:
    user, temporary_password = await create_user(
        db,
        email=str(payload.email),
        role=payload.role,
    )
    response.headers["Cache-Control"] = "no-store"
    return _created(user, temporary_password)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
)
async def update_user_account(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: DbSession,
    actor: AdminUser,
) -> UserRead:
    user = await update_user(
        db,
        actor=actor,
        target_id=user_id,
        payload=payload,
    )
    return _read(user)


@router.delete("/{user_id}", status_code=204)
async def delete_user_account(
    user_id: uuid.UUID,
    db: DbSession,
    actor: AdminUser,
) -> None:
    await delete_user(db, actor=actor, target_id=user_id)


@router.post(
    "/{user_id}/reset-password",
    response_model=UserPasswordReset,
)
async def reset_password(
    user_id: uuid.UUID,
    db: DbSession,
    _: AdminUser,
    response: Response,
) -> UserPasswordReset:
    temporary_password = await reset_user_password(db, user_id=user_id)
    response.headers["Cache-Control"] = "no-store"
    return UserPasswordReset(temporary_password=temporary_password)
