from __future__ import annotations

import uuid
from collections.abc import Mapping

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models.cash_register import (
    DENOMINATION_FIELDS,
    DENOMINATIONS,
    CashRegister,
)


def compute_total_cents(counts: Mapping[str, int]) -> int:
    """Total of a count, in cents, from the denomination values."""

    return sum(counts.get(field, 0) * value for field, value in DENOMINATIONS)


def cash_register_total_cents(cash_register: CashRegister) -> int:
    return compute_total_cents(
        {field: getattr(cash_register, field) for field in DENOMINATION_FIELDS}
    )


async def get_active_cash_register(
    db: AsyncSession,
    cash_register_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> CashRegister:
    query = select(CashRegister).where(
        CashRegister.id == cash_register_id,
        CashRegister.deleted_at.is_(None),
    )
    if for_update:
        query = query.with_for_update()
    cash_register = await db.scalar(query)
    if cash_register is None:
        raise ApiError(404, "cash_register_not_found", "Cash register not found")
    return cash_register


async def name_is_taken(
    db: AsyncSession,
    name: str,
    *,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    query = select(CashRegister.id).where(
        CashRegister.deleted_at.is_(None),
        func.lower(CashRegister.name) == name.lower(),
    )
    if exclude_id is not None:
        query = query.where(CashRegister.id != exclude_id)
    return await db.scalar(query) is not None
