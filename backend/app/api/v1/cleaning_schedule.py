from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.api.deps import DbSession, require_role
from app.models.cleaning_plan import CleaningFrequency, CleaningPlan, CleaningStatus
from app.models.user import UserRole
from app.schemas.cleaning_plan import CleaningScheduleEntry
from app.services.cleaning import last_cleaning_dates, next_due_date, schedule_status

router = APIRouter(prefix="/cleaning-schedule", tags=["cleaning-schedule"])

_ANY_ROLE = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))


async def _scheduled_entries(db: DbSession, on: date) -> list[CleaningScheduleEntry]:
    plans = list(
        await db.scalars(
            select(CleaningPlan).where(
                CleaningPlan.deleted_at.is_(None),
                CleaningPlan.frequency != CleaningFrequency.AFTER_EACH_USE,
            )
        )
    )
    cleanings = await last_cleaning_dates(db, [plan.id for plan in plans])

    entries: list[CleaningScheduleEntry] = []
    for plan in plans:
        due = next_due_date(plan.frequency, cleanings.get(plan.id), plan.created_at.date())
        if due is None:
            continue
        status, days_late = schedule_status(due, on)
        entries.append(
            CleaningScheduleEntry(
                plan_id=plan.id,
                name=plan.name,
                frequency=plan.frequency,
                products=plan.products,
                last_cleaning_date=cleanings.get(plan.id),
                next_due_date=due,
                status=status,
                days_late=days_late,
            )
        )

    entries.sort(key=lambda entry: (entry.next_due_date, entry.name.casefold()))
    return entries


@router.get("", response_model=list[CleaningScheduleEntry], dependencies=[_ANY_ROLE])
async def cleaning_schedule(
    db: DbSession,
    on: Annotated[date | None, Query()] = None,
) -> list[CleaningScheduleEntry]:
    return await _scheduled_entries(db, on or datetime.now(UTC).date())


@router.get("/overdue", response_model=list[CleaningScheduleEntry], dependencies=[_ANY_ROLE])
async def cleaning_schedule_overdue(
    db: DbSession,
    on: Annotated[date | None, Query()] = None,
) -> list[CleaningScheduleEntry]:
    entries = await _scheduled_entries(db, on or datetime.now(UTC).date())
    return [entry for entry in entries if entry.status is CleaningStatus.OVERDUE]
