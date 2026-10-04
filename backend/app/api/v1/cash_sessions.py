from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.deps import DbSession, require_role
from app.core.errors import ApiError
from app.models.cash_register import CashRegister
from app.models.cash_session import CashExpense, CashExpenseKind, CashSession
from app.models.user import User, UserRole
from app.schemas.cash_register import CashRegisterCounts
from app.schemas.cash_session import (
    CashExpenseRead,
    CashExpenseWrite,
    CashSessionClose,
    CashSessionFilter,
    CashSessionOpen,
    CashSessionRead,
    CashSessionWrite,
)
from app.services.cash_session import (
    close_cash_session,
    closing_counts_of,
    closing_total_cents,
    ensure_session_is_open,
    expense_total_cents,
    expenses_total_cents,
    get_cash_session,
    get_session_expense,
    load_session_expenses,
    open_cash_session,
    opening_counts_of,
    opening_total_cents,
)
from app.services.dates import ensure_not_in_the_future

router = APIRouter(prefix="/cash-sessions", tags=["cash-sessions"])

_ANY_ROLE = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))
_ADMIN_ONLY = Depends(require_role(UserRole.ADMIN))
WritingUser = Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))]


def _session_query() -> Select[Any]:
    """One session with its register's name and both author's email."""

    opened_user = aliased(User)
    closed_user = aliased(User)
    return (
        select(CashSession, CashRegister.name, opened_user.email, closed_user.email)
        .join(CashRegister, CashRegister.id == CashSession.cash_register_id)
        .outerjoin(opened_user, opened_user.id == CashSession.opened_by)
        .outerjoin(closed_user, closed_user.id == CashSession.closed_by)
    )


def _expense_read(expense: CashExpense) -> CashExpenseRead:
    return CashExpenseRead(
        id=expense.id,
        kind=expense.kind,
        name=expense.name,
        quantity=expense.quantity,
        unit_price_cents=expense.unit_price_cents,
        vat_rate=expense.vat_rate,
        total_cents=expense_total_cents(expense),
        created_at=expense.created_at,
        updated_at=expense.updated_at,
    )


def _session_read(
    session: CashSession,
    *,
    cash_register_name: str,
    opened_by_email: str | None,
    closed_by_email: str | None,
    expenses: list[CashExpense],
) -> CashSessionRead:
    closing = closing_counts_of(session)
    return CashSessionRead(
        id=session.id,
        cash_register_id=session.cash_register_id,
        cash_register_name=cash_register_name,
        session_date=session.session_date,
        opening_counts=CashRegisterCounts(**opening_counts_of(session)),
        closing_counts=CashRegisterCounts(**closing) if closing is not None else None,
        opening_total_cents=opening_total_cents(session),
        closing_total_cents=closing_total_cents(session),
        expenses_total_cents=expenses_total_cents(expenses),
        expenses_professional_total_cents=expenses_total_cents(
            expenses, kind=CashExpenseKind.PROFESSIONAL
        ),
        expenses_personal_total_cents=expenses_total_cents(expenses, kind=CashExpenseKind.PERSONAL),
        expenses=[_expense_read(expense) for expense in expenses],
        is_open=session.closed_at is None,
        opened_by_email=opened_by_email,
        closed_by_email=closed_by_email,
        closed_at=session.closed_at,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


async def _session_row(
    db: AsyncSession, session_id: uuid.UUID
) -> tuple[CashSession, str, str | None, str | None]:
    row = (
        await db.execute(
            _session_query().where(
                CashSession.id == session_id,
                CashSession.deleted_at.is_(None),
            )
        )
    ).one_or_none()
    if row is None:
        raise ApiError(404, "cash_session_not_found", "Cash session not found")
    session, cash_register_name, opened_by_email, closed_by_email = row
    return session, cash_register_name, opened_by_email, closed_by_email


async def _load_session_read(db: AsyncSession, session_id: uuid.UUID) -> CashSessionRead:
    session, cash_register_name, opened_by_email, closed_by_email = await _session_row(
        db, session_id
    )
    return _session_read(
        session,
        cash_register_name=cash_register_name,
        opened_by_email=opened_by_email,
        closed_by_email=closed_by_email,
        expenses=await load_session_expenses(db, session.id),
    )


@router.get("", response_model=list[CashSessionRead], dependencies=[_ANY_ROLE])
async def list_sessions(
    db: DbSession,
    cash_register_id: uuid.UUID | None = None,
    status: CashSessionFilter = CashSessionFilter.ALL,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
) -> list[CashSessionRead]:
    query = _session_query().where(CashSession.deleted_at.is_(None))
    if cash_register_id is not None:
        query = query.where(CashSession.cash_register_id == cash_register_id)
    if status is CashSessionFilter.OPEN:
        query = query.where(CashSession.closed_at.is_(None))
    elif status is CashSessionFilter.CLOSED:
        query = query.where(CashSession.closed_at.is_not(None))
    if from_date is not None:
        query = query.where(CashSession.session_date >= from_date)
    if to_date is not None:
        query = query.where(CashSession.session_date <= to_date)
    query = query.order_by(CashSession.session_date.desc(), CashSession.created_at.desc())

    rows = list(await db.execute(query))
    if not rows:
        return []

    session_ids = [session.id for session, _, _, _ in rows]
    grouped: dict[uuid.UUID, list[CashExpense]] = {}
    for expense in await db.scalars(
        select(CashExpense)
        .where(CashExpense.session_id.in_(session_ids))
        .order_by(CashExpense.created_at, CashExpense.id)
    ):
        grouped.setdefault(expense.session_id, []).append(expense)

    return [
        _session_read(
            session,
            cash_register_name=cash_register_name,
            opened_by_email=opened_by_email,
            closed_by_email=closed_by_email,
            expenses=grouped.get(session.id, []),
        )
        for session, cash_register_name, opened_by_email, closed_by_email in rows
    ]


@router.post("", response_model=CashSessionRead, status_code=201)
async def open_session(
    payload: CashSessionOpen,
    db: DbSession,
    user: WritingUser,
) -> CashSessionRead:
    session_date = payload.session_date or datetime.now(UTC).date()
    ensure_not_in_the_future(session_date, code="cash_session_date_in_future")

    session = await open_cash_session(
        db,
        cash_register_id=payload.cash_register_id,
        session_date=session_date,
        opening_counts=(
            payload.opening_counts.model_dump() if payload.opening_counts is not None else None
        ),
        opened_by=user.id,
    )
    return await _load_session_read(db, session.id)


@router.get("/{session_id}", response_model=CashSessionRead, dependencies=[_ANY_ROLE])
async def get_session(session_id: uuid.UUID, db: DbSession) -> CashSessionRead:
    return await _load_session_read(db, session_id)


@router.put("/{session_id}", response_model=CashSessionRead, dependencies=[_ANY_ROLE])
async def update_session(
    session_id: uuid.UUID,
    payload: CashSessionWrite,
    db: DbSession,
) -> CashSessionRead:
    session = await get_cash_session(db, session_id, for_update=True)
    ensure_session_is_open(session)
    ensure_not_in_the_future(payload.session_date, code="cash_session_date_in_future")

    session.session_date = payload.session_date
    for field, value in payload.opening_counts.model_dump().items():
        setattr(session, field, int(value))

    await db.commit()
    await db.refresh(session)
    return await _load_session_read(db, session.id)


@router.post(
    "/{session_id}/expenses",
    response_model=CashSessionRead,
    status_code=201,
    dependencies=[_ANY_ROLE],
)
async def add_expense(
    session_id: uuid.UUID,
    payload: CashExpenseWrite,
    db: DbSession,
) -> CashSessionRead:
    session = await get_cash_session(db, session_id)
    ensure_session_is_open(session)

    db.add(
        CashExpense(
            session_id=session.id,
            kind=payload.kind,
            name=payload.name,
            quantity=payload.quantity,
            unit_price_cents=payload.unit_price_cents,
            vat_rate=payload.vat_rate,
        )
    )
    await db.commit()
    return await _load_session_read(db, session.id)


@router.put(
    "/{session_id}/expenses/{expense_id}",
    response_model=CashSessionRead,
    dependencies=[_ANY_ROLE],
)
async def update_expense(
    session_id: uuid.UUID,
    expense_id: uuid.UUID,
    payload: CashExpenseWrite,
    db: DbSession,
) -> CashSessionRead:
    session = await get_cash_session(db, session_id)
    ensure_session_is_open(session)
    expense = await get_session_expense(db, session_id, expense_id)

    expense.kind = payload.kind
    expense.name = payload.name
    expense.quantity = payload.quantity
    expense.unit_price_cents = payload.unit_price_cents
    expense.vat_rate = payload.vat_rate

    await db.commit()
    return await _load_session_read(db, session.id)


@router.delete(
    "/{session_id}/expenses/{expense_id}",
    status_code=204,
    dependencies=[_ANY_ROLE],
)
async def remove_expense(
    session_id: uuid.UUID,
    expense_id: uuid.UUID,
    db: DbSession,
) -> None:
    session = await get_cash_session(db, session_id)
    ensure_session_is_open(session)
    expense = await get_session_expense(db, session_id, expense_id)

    # No audit trail was asked for on expenses, and the session is still open:
    # a line added by mistake simply disappears.
    await db.delete(expense)
    await db.commit()


@router.post("/{session_id}/close", response_model=CashSessionRead)
async def close_session(
    session_id: uuid.UUID,
    payload: CashSessionClose,
    db: DbSession,
    user: WritingUser,
) -> CashSessionRead:
    session = await get_cash_session(db, session_id, for_update=True)
    await close_cash_session(
        db,
        session=session,
        closing_counts=payload.closing_counts.model_dump(),
        closed_by=user.id,
    )
    return await _load_session_read(db, session.id)


@router.delete("/{session_id}", status_code=204, dependencies=[_ADMIN_ONLY])
async def delete_session(session_id: uuid.UUID, db: DbSession) -> None:
    session = await get_cash_session(db, session_id, for_update=True)
    session.deleted_at = datetime.now(UTC)
    await db.commit()
