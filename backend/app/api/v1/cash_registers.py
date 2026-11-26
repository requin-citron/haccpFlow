from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession, require_role
from app.core.errors import ApiError
from app.models.cash_register import DENOMINATION_FIELDS, CashRegister, CashRegisterKind
from app.models.user import UserRole
from app.schemas.cash_register import CashRegisterRead, CashRegisterWrite
from app.services.cash_register import (
    cash_register_total_cents,
    get_active_cash_register,
    kind_uses_denominations,
    name_is_taken,
)
from app.services.cash_session import register_has_open_session

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
        kind=cash_register.kind,
        total_cents=cash_register_total_cents(cash_register),
        created_at=cash_register.created_at,
        updated_at=cash_register.updated_at,
        **_counts(cash_register),
    )


def _validate_counts_for_kind(payload: CashRegisterWrite) -> None:
    if kind_uses_denominations(payload.kind):
        return
    if any(getattr(payload, field) != 0 for field in DENOMINATION_FIELDS):
        raise ApiError(
            422,
            "cash_register_counts_not_supported",
            "Cheque and card registers cannot contain denomination counts",
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
    _validate_counts_for_kind(payload)
    if await name_is_taken(db, payload.name):
        raise _conflict_error(payload.name)

    cash_register = CashRegister(
        name=payload.name,
        kind=payload.kind,
        **_counts(payload),
    )
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
    if payload.kind is not cash_register.kind:
        raise ApiError(
            409,
            "cash_register_kind_immutable",
            "A cash register kind cannot be changed after creation",
        )
    _validate_counts_for_kind(payload)

    if await name_is_taken(db, payload.name, exclude_id=cash_register_id):
        raise _conflict_error(payload.name)

    cash_register.name = payload.name
    if cash_register.kind is CashRegisterKind.CASH:
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
    if await register_has_open_session(db, cash_register_id):
        raise ApiError(
            409,
            "cash_register_has_open_session",
            "Close the cash register's open session before deactivating it",
        )
    cash_register.deleted_at = datetime.now(UTC)
    await db.commit()
