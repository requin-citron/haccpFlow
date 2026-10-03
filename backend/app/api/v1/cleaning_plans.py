from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession, require_role
from app.core.errors import ApiError
from app.models.cleaning_plan import (
    CleaningPlan,
    CleaningRecord,
    CleaningRecordEdit,
    CleaningRecordEditAction,
)
from app.models.user import User, UserRole
from app.schemas.cleaning_plan import (
    CleaningPlanRead,
    CleaningPlanWrite,
    CleaningRecordEditRead,
    CleaningRecordRead,
    CleaningRecordUpdate,
    CleaningRecordWrite,
)
from app.services.cleaning import (
    get_active_cleaning_plan,
    last_cleaning_dates,
    next_due_date,
)
from app.services.dates import ensure_not_in_the_future

router = APIRouter(prefix="/cleaning-plans", tags=["cleaning-plans"])

_ANY_ROLE = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))
_ADMIN_ONLY = Depends(require_role(UserRole.ADMIN))
WritingUser = Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))]


def _name_conflict_error(name: str) -> ApiError:
    return ApiError(
        409,
        "cleaning_plan_name_conflict",
        f"An active cleaning plan named '{name}' already exists",
    )


def _plan_read(
    plan: CleaningPlan,
    last_cleaning: date | None,
    on: date,
) -> CleaningPlanRead:
    return CleaningPlanRead(
        id=plan.id,
        name=plan.name,
        frequency=plan.frequency,
        products=plan.products,
        last_cleaning_date=last_cleaning,
        next_due_date=next_due_date(plan.frequency, last_cleaning, plan.created_at.date()),
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def _record_read(record: CleaningRecord, email: str | None) -> CleaningRecordRead:
    return CleaningRecordRead(
        id=record.id,
        plan_id=record.plan_id,
        cleaning_date=record.cleaning_date,
        comment=record.comment,
        performed_by_email=email,
        recorded_at=record.recorded_at,
        updated_at=record.updated_at,
    )


async def _load_record(db: DbSession, record_id: uuid.UUID) -> CleaningRecordRead:
    row = (
        await db.execute(
            select(CleaningRecord, User.email)
            .outerjoin(User, User.id == CleaningRecord.performed_by)
            .where(CleaningRecord.id == record_id)
        )
    ).one()
    record, email = row
    return _record_read(record, email)


async def _get_record(
    db: DbSession,
    plan_id: uuid.UUID,
    record_id: uuid.UUID,
    *,
    include_deleted: bool = False,
    for_update: bool = False,
) -> CleaningRecord:
    query = select(CleaningRecord).where(
        CleaningRecord.id == record_id,
        CleaningRecord.plan_id == plan_id,
    )
    if not include_deleted:
        query = query.where(CleaningRecord.deleted_at.is_(None))
    if for_update:
        query = query.with_for_update()
    record = await db.scalar(query)
    if record is None:
        raise ApiError(404, "cleaning_record_not_found", "Cleaning record not found")
    return record


async def _name_is_taken(
    db: DbSession,
    name: str,
    *,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    query = select(CleaningPlan.id).where(
        CleaningPlan.deleted_at.is_(None),
        func.lower(CleaningPlan.name) == name.lower(),
    )
    if exclude_id is not None:
        query = query.where(CleaningPlan.id != exclude_id)
    return await db.scalar(query) is not None


@router.get("", response_model=list[CleaningPlanRead], dependencies=[_ANY_ROLE])
async def list_cleaning_plans(db: DbSession) -> list[CleaningPlanRead]:
    plans = list(
        await db.scalars(
            select(CleaningPlan)
            .where(CleaningPlan.deleted_at.is_(None))
            .order_by(func.lower(CleaningPlan.name))
        )
    )
    cleanings = await last_cleaning_dates(db, [plan.id for plan in plans])
    on = datetime.now(UTC).date()
    return [_plan_read(plan, cleanings.get(plan.id), on) for plan in plans]


@router.post("", response_model=CleaningPlanRead, status_code=201, dependencies=[_ANY_ROLE])
async def create_cleaning_plan(payload: CleaningPlanWrite, db: DbSession) -> CleaningPlanRead:
    if await _name_is_taken(db, payload.name):
        raise _name_conflict_error(payload.name)

    plan = CleaningPlan(
        name=payload.name,
        frequency=payload.frequency,
        products=payload.products,
    )
    db.add(plan)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _name_conflict_error(payload.name) from exc

    await db.refresh(plan)
    return _plan_read(plan, None, datetime.now(UTC).date())


@router.put("/{plan_id}", response_model=CleaningPlanRead, dependencies=[_ANY_ROLE])
async def update_cleaning_plan(
    plan_id: uuid.UUID,
    payload: CleaningPlanWrite,
    db: DbSession,
) -> CleaningPlanRead:
    plan = await get_active_cleaning_plan(db, plan_id, for_update=True)

    if await _name_is_taken(db, payload.name, exclude_id=plan_id):
        raise _name_conflict_error(payload.name)

    plan.name = payload.name
    plan.frequency = payload.frequency
    plan.products = payload.products

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _name_conflict_error(payload.name) from exc

    await db.refresh(plan)
    cleanings = await last_cleaning_dates(db, [plan.id])
    return _plan_read(plan, cleanings.get(plan.id), datetime.now(UTC).date())


@router.delete("/{plan_id}", status_code=204, dependencies=[_ADMIN_ONLY])
async def delete_cleaning_plan(plan_id: uuid.UUID, db: DbSession) -> None:
    plan = await get_active_cleaning_plan(db, plan_id, for_update=True)
    plan.deleted_at = datetime.now(UTC)
    await db.commit()


@router.get(
    "/{plan_id}/records",
    response_model=list[CleaningRecordRead],
    dependencies=[_ANY_ROLE],
)
async def list_cleaning_records(
    plan_id: uuid.UUID,
    db: DbSession,
) -> list[CleaningRecordRead]:
    await get_active_cleaning_plan(db, plan_id)
    rows = await db.execute(
        select(CleaningRecord, User.email)
        .outerjoin(User, User.id == CleaningRecord.performed_by)
        .where(
            CleaningRecord.plan_id == plan_id,
            CleaningRecord.deleted_at.is_(None),
        )
        .order_by(CleaningRecord.cleaning_date.desc(), CleaningRecord.recorded_at.desc())
    )
    return [_record_read(record, email) for record, email in rows]


@router.post(
    "/{plan_id}/records",
    response_model=CleaningRecordRead,
    status_code=201,
)
async def create_cleaning_record(
    plan_id: uuid.UUID,
    payload: CleaningRecordWrite,
    db: DbSession,
    user: WritingUser,
) -> CleaningRecordRead:
    plan = await get_active_cleaning_plan(db, plan_id, for_update=True)
    ensure_not_in_the_future(payload.cleaning_date, code="cleaning_date_out_of_range")

    record = CleaningRecord(
        plan_id=plan.id,
        cleaning_date=payload.cleaning_date,
        comment=payload.comment,
        performed_by=user.id,
        recorded_at=datetime.now(UTC),
    )
    db.add(record)
    await db.flush()
    db.add(
        CleaningRecordEdit(
            record_id=record.id,
            action=CleaningRecordEditAction.CREATED,
            previous_cleaning_date=None,
            new_cleaning_date=payload.cleaning_date,
            previous_comment=None,
            new_comment=payload.comment,
            changed_by=user.id,
        )
    )
    await db.commit()
    return await _load_record(db, record.id)


@router.put(
    "/{plan_id}/records/{record_id}",
    response_model=CleaningRecordRead,
)
async def update_cleaning_record(
    plan_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: CleaningRecordUpdate,
    db: DbSession,
    user: WritingUser,
) -> CleaningRecordRead:
    await get_active_cleaning_plan(db, plan_id)
    record = await _get_record(db, plan_id, record_id, for_update=True)

    new_date = record.cleaning_date
    if payload.cleaning_date is not None:
        ensure_not_in_the_future(payload.cleaning_date, code="cleaning_date_out_of_range")
        new_date = payload.cleaning_date
    # An explicit null clears the comment; an absent field keeps it.
    new_comment = payload.comment if "comment" in payload.model_fields_set else record.comment

    if new_date == record.cleaning_date and new_comment == record.comment:
        return await _load_record(db, record.id)

    db.add(
        CleaningRecordEdit(
            record_id=record.id,
            action=CleaningRecordEditAction.UPDATED,
            previous_cleaning_date=record.cleaning_date,
            new_cleaning_date=new_date,
            previous_comment=record.comment,
            new_comment=new_comment,
            changed_by=user.id,
        )
    )
    record.cleaning_date = new_date
    record.comment = new_comment
    await db.commit()
    return await _load_record(db, record.id)


@router.delete("/{plan_id}/records/{record_id}", status_code=204)
async def delete_cleaning_record(
    plan_id: uuid.UUID,
    record_id: uuid.UUID,
    db: DbSession,
    user: WritingUser,
) -> None:
    await get_active_cleaning_plan(db, plan_id)
    record = await _get_record(db, plan_id, record_id, for_update=True)

    record.deleted_at = datetime.now(UTC)
    db.add(
        CleaningRecordEdit(
            record_id=record.id,
            action=CleaningRecordEditAction.DELETED,
            previous_cleaning_date=record.cleaning_date,
            new_cleaning_date=None,
            previous_comment=record.comment,
            new_comment=None,
            changed_by=user.id,
        )
    )
    await db.commit()


@router.get(
    "/{plan_id}/records/{record_id}/history",
    response_model=list[CleaningRecordEditRead],
    dependencies=[_ANY_ROLE],
)
async def cleaning_record_history(
    plan_id: uuid.UUID,
    record_id: uuid.UUID,
    db: DbSession,
) -> list[CleaningRecordEditRead]:
    await get_active_cleaning_plan(db, plan_id)
    # A deleted declaration keeps its history reachable.
    await _get_record(db, plan_id, record_id, include_deleted=True)

    rows = await db.execute(
        select(CleaningRecordEdit, User.email)
        .outerjoin(User, User.id == CleaningRecordEdit.changed_by)
        .where(CleaningRecordEdit.record_id == record_id)
        .order_by(CleaningRecordEdit.changed_at.desc())
    )
    return [
        CleaningRecordEditRead(
            action=edit.action,
            previous_cleaning_date=edit.previous_cleaning_date,
            new_cleaning_date=edit.new_cleaning_date,
            previous_comment=edit.previous_comment,
            new_comment=edit.new_comment,
            changed_by_email=email,
            changed_at=edit.changed_at,
        )
        for edit, email in rows
    ]
