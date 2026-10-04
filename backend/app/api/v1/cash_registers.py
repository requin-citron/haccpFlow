from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession, require_role
from app.core.errors import ApiError
from app.models.cash_register import DENOMINATION_FIELDS, CashRegister
from app.models.user import UserRole
from app.schemas.cash_register import CashRegisterRead, CashRegisterWrite
from app.services.cash_register import (
    cash_register_total_cents,
    get_active_cash_register,
    name_is_taken,
)

router = APIRouter(prefix="/cash-registers", tags=["cash-registers"])

_ANY_ROLE = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))
_ADMIN_ONLY = Depends(require_role(UserRole.ADMIN))


def _conflict_error(name: str) -> ApiError:
    return ApiError(
        409,
        "cash_register_name_conflict",
        f"An active cash register named '{name}' already exists",
    )


def _counts(source: CashRegister | CashRegisterWrite) -> dict[str, int]:
    return {field: getattr(source, field) for field in DENOMINATION_FIELDS}


def _read(cash_register: CashRegister) -> CashRegisterRead:
    return CashRegisterRead(
        id=cash_register.id,
        name=cash_register.name,
        total_cents=cash_register_total_cents(cash_register),
        created_at=cash_register.created_at,
        updated_at=cash_register.updated_at,
        **_counts(cash_register),
    )


@router.get("", response_model=list[CashRegisterRead], dependencies=[_ANY_ROLE])
async def list_cash_registers(db: DbSession) -> list[CashRegisterRead]:
    cash_registers = await db.scalars(
        select(CashRegister)
        .where(CashRegister.deleted_at.is_(None))
        .order_by(func.lower(CashRegister.name))
    )
    return [_read(cash_register) for cash_register in cash_registers]


@router.post("", response_model=CashRegisterRead, status_code=201, dependencies=[_ANY_ROLE])
async def create_cash_register(
    payload: CashRegisterWrite,
    db: DbSession,
) -> CashRegisterRead:
    if await name_is_taken(db, payload.name):
        raise _conflict_error(payload.name)

    cash_register = CashRegister(name=payload.name, **_counts(payload))
    db.add(cash_register)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict_error(payload.name) from exc

    await db.refresh(cash_register)
    return _read(cash_register)


@router.put("/{cash_register_id}", response_model=CashRegisterRead, dependencies=[_ANY_ROLE])
async def update_cash_register(
    cash_register_id: uuid.UUID,
    payload: CashRegisterWrite,
    db: DbSession,
) -> CashRegisterRead:
    cash_register = await get_active_cash_register(db, cash_register_id, for_update=True)

    if await name_is_taken(db, payload.name, exclude_id=cash_register_id):
        raise _conflict_error(payload.name)

    cash_register.name = payload.name
    for field, value in _counts(payload).items():
        setattr(cash_register, field, value)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict_error(payload.name) from exc

    await db.refresh(cash_register)
    return _read(cash_register)


@router.delete("/{cash_register_id}", status_code=204, dependencies=[_ADMIN_ONLY])
async def delete_cash_register(cash_register_id: uuid.UUID, db: DbSession) -> None:
    cash_register = await get_active_cash_register(db, cash_register_id, for_update=True)
    cash_register.deleted_at = datetime.now(UTC)
    await db.commit()
