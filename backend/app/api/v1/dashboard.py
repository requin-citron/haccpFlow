from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, require_role
from app.core.errors import ApiError
from app.models.user import User, UserRole
from app.schemas.dashboard import (
    DashboardLayoutRead,
    DashboardLayoutWrite,
    DashboardMissingReadingsRead,
    DashboardRevenueRead,
)
from app.services.dashboard import (
    dashboard_missing_readings,
    dashboard_revenue,
    get_dashboard_widgets,
    save_dashboard_widgets,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

DashboardUser = Annotated[
    User,
    Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR)),
]


@router.get("/revenue", response_model=DashboardRevenueRead)
async def revenue(
    db: DbSession,
    _: DashboardUser,
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
) -> DashboardRevenueRead:
    if from_date > to_date:
        raise ApiError(
            422,
            "dashboard_range_invalid",
            "The start date must be before the end date",
        )

    summary = await dashboard_revenue(db, from_date=from_date, to_date=to_date)
    return DashboardRevenueRead(
        from_date=from_date,
        to_date=to_date,
        total_cents=summary.total_cents,
        cash_cents=summary.cash_cents,
        cheque_cents=summary.cheque_cents,
        card_cents=summary.card_cents,
        cash_expenses_cents=summary.cash_expenses_cents,
        closed_session_count=summary.closed_session_count,
    )


@router.get("/missing-readings", response_model=DashboardMissingReadingsRead)
async def missing_readings(
    db: DbSession,
    _: DashboardUser,
    from_date: Annotated[date, Query(alias="from")],
    to_date: Annotated[date, Query(alias="to")],
) -> DashboardMissingReadingsRead:
    if from_date > to_date:
        raise ApiError(
            422,
            "dashboard_range_invalid",
            "The start date must be before the end date",
        )

    summary = await dashboard_missing_readings(
        db,
        from_date=from_date,
        to_date=to_date,
    )
    return DashboardMissingReadingsRead(
        from_date=from_date,
        to_date=to_date,
        missing_slots=summary.missing_slots,
        filled_slots=summary.filled_slots,
        total_slots=summary.total_slots,
        equipment_count=summary.equipment_count,
    )


@router.get("/layout", response_model=DashboardLayoutRead)
async def get_layout(db: DbSession, user: DashboardUser) -> DashboardLayoutRead:
    widgets = await get_dashboard_widgets(db, user_id=user.id)
    return DashboardLayoutRead.model_validate({"widgets": widgets})


@router.put("/layout", response_model=DashboardLayoutRead)
async def save_layout(
    payload: DashboardLayoutWrite,
    db: DbSession,
    user: DashboardUser,
) -> DashboardLayoutRead:
    widgets = await save_dashboard_widgets(
        db,
        user_id=user.id,
        widgets=payload.model_dump(mode="json")["widgets"],
    )
    return DashboardLayoutRead.model_validate({"widgets": widgets})
