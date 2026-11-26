from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cash_register import CashRegister, CashRegisterKind
from app.models.cash_session import CashExpense, CashExpenseKind, CashSession
from app.models.dashboard_layout import DashboardLayout
from app.models.equipment import Equipment
from app.models.temperature_reading import TemperatureReading
from app.services.cash_session import (
    closing_total_cents,
    expenses_total_cents,
    opening_total_cents,
)

DEFAULT_DASHBOARD_WIDGETS: tuple[dict[str, object], ...] = (
    {
        "key": "revenue",
        "column_start": 1,
        "row_start": 1,
        "width_columns": 12,
        "row_span": 6,
    },
)


@dataclass(frozen=True)
class DashboardRevenue:
    total_cents: int
    cash_cents: int
    cheque_cents: int
    card_cents: int
    cash_expenses_cents: int
    closed_session_count: int


@dataclass(frozen=True)
class DashboardMissingReadings:
    missing_slots: int
    filled_slots: int
    total_slots: int
    equipment_count: int


async def dashboard_revenue(
    db: AsyncSession,
    *,
    from_date: date,
    to_date: date,
) -> DashboardRevenue:
    """Aggregate revenue from closed sessions in an inclusive date range."""

    rows = list(
        await db.execute(
            select(CashSession, CashRegister.kind)
            .join(CashRegister, CashRegister.id == CashSession.cash_register_id)
            .where(
                CashSession.closed_at.is_not(None),
                CashSession.deleted_at.is_(None),
                CashSession.session_date >= from_date,
                CashSession.session_date <= to_date,
            )
            .order_by(CashSession.session_date, CashSession.created_at)
        )
    )

    expenses_by_session: dict[uuid.UUID, list[CashExpense]] = {}
    if rows:
        session_ids = [session.id for session, _ in rows]
        for expense in await db.scalars(
            select(CashExpense).where(CashExpense.session_id.in_(session_ids))
        ):
            expenses_by_session.setdefault(expense.session_id, []).append(expense)

    cash_cents = 0
    cheque_cents = 0
    card_cents = 0
    cash_expenses_cents = 0

    for session, register_kind in rows:
        expenses = expenses_by_session.get(session.id, [])
        if register_kind is CashRegisterKind.CASH:
            expenses_cents = expenses_total_cents(
                expenses,
                kind=CashExpenseKind.PROFESSIONAL,
            ) + expenses_total_cents(
                expenses,
                kind=CashExpenseKind.PERSONAL,
            )
            cash_expenses_cents += expenses_cents
            cash_cents += (
                (closing_total_cents(session) or 0) - opening_total_cents(session) + expenses_cents
            )
        elif register_kind is CashRegisterKind.CHEQUE:
            cheque_cents += session.collected_amount_cents or 0
        else:
            card_cents += session.collected_amount_cents or 0

    return DashboardRevenue(
        total_cents=cash_cents + cheque_cents + card_cents,
        cash_cents=cash_cents,
        cheque_cents=cheque_cents,
        card_cents=card_cents,
        cash_expenses_cents=cash_expenses_cents,
        closed_session_count=len(rows),
    )


async def dashboard_missing_readings(
    db: AsyncSession,
    *,
    from_date: date,
    to_date: date,
) -> DashboardMissingReadings:
    """Count expected and filled reading slots for active equipment."""

    end_date = min(to_date, datetime.now(UTC).date())
    if end_date < from_date:
        return DashboardMissingReadings(
            missing_slots=0,
            filled_slots=0,
            total_slots=0,
            equipment_count=0,
        )

    equipment = list(
        await db.scalars(
            select(Equipment)
            .where(Equipment.deleted_at.is_(None))
            .order_by(Equipment.created_at, Equipment.id)
        )
    )
    eligible_equipment = [
        item for item in equipment if max(from_date, item.created_at.date()) <= end_date
    ]
    total_slots = sum(
        (end_date - max(from_date, item.created_at.date())).days * 2 + 2
        for item in eligible_equipment
    )

    filled_slots = 0
    if eligible_equipment:
        filled_slots = int(
            await db.scalar(
                select(func.count(TemperatureReading.id)).where(
                    TemperatureReading.equipment_id.in_([item.id for item in eligible_equipment]),
                    TemperatureReading.reading_date >= from_date,
                    TemperatureReading.reading_date <= end_date,
                )
            )
            or 0
        )

    return DashboardMissingReadings(
        missing_slots=max(0, total_slots - filled_slots),
        filled_slots=filled_slots,
        total_slots=total_slots,
        equipment_count=len(eligible_equipment),
    )


async def get_dashboard_widgets(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[dict[str, object]]:
    """Return the saved layout, or the virtual default without writing to DB."""

    layout = await db.scalar(select(DashboardLayout).where(DashboardLayout.user_id == user_id))
    if layout is None:
        return [dict(widget) for widget in DEFAULT_DASHBOARD_WIDGETS]
    return list(layout.widgets)


async def save_dashboard_widgets(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    widgets: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Atomically replace one user's complete widget list."""

    statement = (
        insert(DashboardLayout)
        .values(
            id=uuid.uuid4(),
            user_id=user_id,
            widgets=widgets,
        )
        .on_conflict_do_update(
            index_elements=[DashboardLayout.user_id],
            set_={
                "widgets": widgets,
                "updated_at": func.now(),
            },
        )
        .returning(DashboardLayout.widgets)
    )
    saved = await db.scalar(statement)
    await db.commit()
    return list(saved or [])
