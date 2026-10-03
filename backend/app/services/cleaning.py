from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import assert_never

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models.cleaning_plan import (
    CleaningFrequency,
    CleaningPlan,
    CleaningRecord,
    CleaningStatus,
)

DAILY_INTERVAL = timedelta(days=1)
WEEKLY_INTERVAL = timedelta(days=7)


def next_due_date(
    frequency: CleaningFrequency,
    last_cleaning_date: date | None,
    created_at_date: date,
) -> date | None:
    """Sliding interval counted from the last cleaning.

    A plan that has never been cleaned is due since the day it was created:
    nothing has been done yet under it.
    """

    match frequency:
        case CleaningFrequency.AFTER_EACH_USE:
            return None
        case CleaningFrequency.DAILY:
            interval = DAILY_INTERVAL
        case CleaningFrequency.WEEKLY:
            interval = WEEKLY_INTERVAL
        case _ as unreachable:
            assert_never(unreachable)

    if last_cleaning_date is None:
        return created_at_date
    return last_cleaning_date + interval


def schedule_status(next_due: date, on: date) -> tuple[CleaningStatus, int]:
    """Late means strictly past due; due today is not late yet."""

    if next_due < on:
        return CleaningStatus.OVERDUE, (on - next_due).days
    if next_due == on:
        return CleaningStatus.DUE_TODAY, 0
    return CleaningStatus.UPCOMING, 0


async def get_active_cleaning_plan(
    db: AsyncSession,
    plan_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> CleaningPlan:
    query = select(CleaningPlan).where(
        CleaningPlan.id == plan_id,
        CleaningPlan.deleted_at.is_(None),
    )
    if for_update:
        query = query.with_for_update()
    plan = await db.scalar(query)
    if plan is None:
        raise ApiError(404, "cleaning_plan_not_found", "Cleaning plan not found")
    return plan


async def last_cleaning_dates(
    db: AsyncSession,
    plan_ids: list[uuid.UUID],
) -> dict[uuid.UUID, date]:
    """Latest declared cleaning date per plan, ignoring deleted declarations."""

    if not plan_ids:
        return {}
    rows = await db.execute(
        select(CleaningRecord.plan_id, func.max(CleaningRecord.cleaning_date))
        .where(
            CleaningRecord.plan_id.in_(plan_ids),
            CleaningRecord.deleted_at.is_(None),
        )
        .group_by(CleaningRecord.plan_id)
    )
    latest: dict[uuid.UUID, date] = {}
    for plan_id, last_date in rows:
        latest[plan_id] = last_date
    return latest
