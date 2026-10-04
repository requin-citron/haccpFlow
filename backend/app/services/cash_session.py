from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models.cash_register import DENOMINATION_FIELDS, CashRegister
from app.models.cash_session import CashExpense, CashExpenseKind, CashSession
from app.services.cash_register import compute_total_cents, get_active_cash_register

ALREADY_OPEN = (
    409,
    "cash_session_already_open",
    "This cash register already has an open session: close it first",
)
ALREADY_CLOSED = (
    409,
    "cash_session_closed",
    "This cash session is closed and can no longer be changed",
)


def opening_counts_of(session: CashSession) -> dict[str, int]:
    """The float the session was opened with, in units per denomination."""

    return counts_from(session)


def closing_counts_of(session: CashSession) -> dict[str, int] | None:
    """The count made at closing time, or None while the session is open."""

    if session.closed_at is None:
        return None
    return counts_from(session, prefix="closed_")


def register_counts_of(cash_register: CashRegister) -> dict[str, int]:
    return counts_from(cash_register)


def counts_from(source: object, *, prefix: str = "") -> dict[str, int]:
    counts: dict[str, int] = {}
    for field in DENOMINATION_FIELDS:
        counts[field] = int(getattr(source, f"{prefix}{field}"))
    return counts


def expense_total_cents(expense: CashExpense) -> int:
    return expense.quantity * expense.unit_price_cents


def expenses_total_cents(
    expenses: Iterable[CashExpense],
    *,
    kind: CashExpenseKind | None = None,
) -> int:
    return sum(
        expense_total_cents(expense) for expense in expenses if kind is None or expense.kind == kind
    )


def opening_total_cents(session: CashSession) -> int:
    return compute_total_cents(opening_counts_of(session))


def closing_total_cents(session: CashSession) -> int | None:
    counts = closing_counts_of(session)
    if counts is None:
        return None
    return compute_total_cents(counts)


def ensure_session_is_open(session: CashSession) -> None:
    if session.closed_at is not None:
        raise ApiError(*ALREADY_CLOSED)


async def get_cash_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> CashSession:
    query = select(CashSession).where(
        CashSession.id == session_id,
        CashSession.deleted_at.is_(None),
    )
    if for_update:
        query = query.with_for_update()
    session = await db.scalar(query)
    if session is None:
        raise ApiError(404, "cash_session_not_found", "Cash session not found")
    return session


async def get_open_cash_session(
    db: AsyncSession,
    cash_register_id: uuid.UUID,
) -> CashSession | None:
    session: CashSession | None = await db.scalar(
        select(CashSession).where(
            CashSession.cash_register_id == cash_register_id,
            CashSession.closed_at.is_(None),
            CashSession.deleted_at.is_(None),
        )
    )
    return session


async def register_has_open_session(db: AsyncSession, cash_register_id: uuid.UUID) -> bool:
    return await get_open_cash_session(db, cash_register_id) is not None


async def load_session_expenses(db: AsyncSession, session_id: uuid.UUID) -> list[CashExpense]:
    return list(
        await db.scalars(
            select(CashExpense)
            .where(CashExpense.session_id == session_id)
            .order_by(CashExpense.created_at, CashExpense.id)
        )
    )


async def get_session_expense(
    db: AsyncSession,
    session_id: uuid.UUID,
    expense_id: uuid.UUID,
) -> CashExpense:
    expense = await db.scalar(
        select(CashExpense).where(
            CashExpense.id == expense_id,
            CashExpense.session_id == session_id,
        )
    )
    if expense is None:
        raise ApiError(404, "cash_expense_not_found", "Cash expense not found")
    return expense


async def open_cash_session(
    db: AsyncSession,
    *,
    cash_register_id: uuid.UUID,
    session_date: date,
    opening_counts: Mapping[str, int] | None,
    opened_by: uuid.UUID | None,
) -> CashSession:
    """Open a session's tracking, copying the register's count by default."""

    # Locking the register serialises two openings started at the same time:
    # the second one sees the first session and gets a clean 409.
    cash_register = await get_active_cash_register(db, cash_register_id, for_update=True)
    if await get_open_cash_session(db, cash_register.id) is not None:
        raise ApiError(*ALREADY_OPEN)

    counts = register_counts_of(cash_register) if opening_counts is None else opening_counts
    session = CashSession(
        cash_register_id=cash_register.id,
        session_date=session_date,
        opened_by=opened_by,
        **{field: int(counts.get(field, 0)) for field in DENOMINATION_FIELDS},
    )
    db.add(session)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ApiError(*ALREADY_OPEN) from exc

    await db.refresh(session)
    return session


async def close_cash_session(
    db: AsyncSession,
    *,
    session: CashSession,
    closing_counts: Mapping[str, int],
    closed_by: uuid.UUID | None,
) -> CashRegister:
    """Close a session: its closing count becomes the register's new state."""

    ensure_session_is_open(session)
    cash_register = await get_active_cash_register(db, session.cash_register_id, for_update=True)

    for field in DENOMINATION_FIELDS:
        value = int(closing_counts.get(field, 0))
        setattr(session, f"closed_{field}", value)
        setattr(cash_register, field, value)

    session.closed_at = datetime.now(UTC)
    session.closed_by = closed_by
    await db.commit()
    await db.refresh(session)
    await db.refresh(cash_register)
    return cash_register
