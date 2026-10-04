from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.api.deps import DbSession, require_role
from app.core.errors import ApiError
from app.models.pasteurisation import (
    PasteurisationBatch,
    PasteurisationPhase,
    PasteurisationPhaseEdit,
    PasteurisationPhaseEditAction,
    PasteurisationPhaseRecord,
)
from app.models.user import User, UserRole
from app.schemas.pasteurisation import (
    PasteurisationBatchWrite,
    PasteurisationPhaseEditRead,
    PasteurisationPhaseRead,
    PasteurisationPhaseWrite,
    PasteurisationRead,
)
from app.services.dates import ensure_not_in_the_future
from app.services.pasteurisation import (
    PHASE_ORDER,
    compute_duration_minutes,
    get_active_pasteurisation,
    load_phase_records,
    phase_is_complete,
    phase_is_filled,
)
from app.services.temperature import as_celsius

router = APIRouter(prefix="/pasteurisations", tags=["pasteurisations"])

_ANY_ROLE = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))
_ADMIN_ONLY = Depends(require_role(UserRole.ADMIN))
WritingUser = Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))]

PHASE_FIELDS = ("started_at", "ended_at", "target_temperature_celsius", "observation")


def _phase_read(
    phase: PasteurisationPhase,
    record: PasteurisationPhaseRecord | None,
) -> PasteurisationPhaseRead:
    if record is None:
        return PasteurisationPhaseRead(
            phase=phase,
            started_at=None,
            ended_at=None,
            duration_minutes=None,
            target_temperature_celsius=None,
            observation=None,
        )
    return PasteurisationPhaseRead(
        phase=phase,
        started_at=record.started_at,
        ended_at=record.ended_at,
        duration_minutes=compute_duration_minutes(record.started_at, record.ended_at),
        target_temperature_celsius=record.target_temperature_celsius,
        observation=record.observation,
    )


def _record_is_filled(record: PasteurisationPhaseRecord | None) -> bool:
    if record is None:
        return False
    return phase_is_filled(
        started_at=record.started_at,
        ended_at=record.ended_at,
        target_temperature_celsius=record.target_temperature_celsius,
        observation=record.observation,
    )


def _record_is_complete(record: PasteurisationPhaseRecord | None) -> bool:
    if record is None:
        return False
    return phase_is_complete(
        started_at=record.started_at,
        ended_at=record.ended_at,
        target_temperature_celsius=record.target_temperature_celsius,
    )


def _batch_read(
    batch: PasteurisationBatch,
    records: dict[PasteurisationPhase, PasteurisationPhaseRecord],
) -> PasteurisationRead:
    # Every known phase is returned, filled or not: the caller sees at a glance
    # what is still missing, and a new phase appears here automatically.
    return PasteurisationRead(
        id=batch.id,
        batch_date=batch.batch_date,
        product_name=batch.product_name,
        lot_number=batch.lot_number,
        quantity=batch.quantity,
        phases=[_phase_read(phase, records.get(phase)) for phase in PHASE_ORDER],
        filled_phases=sum(1 for phase in PHASE_ORDER if _record_is_filled(records.get(phase))),
        is_complete=all(_record_is_complete(records.get(phase)) for phase in PHASE_ORDER),
        created_at=batch.created_at,
        updated_at=batch.updated_at,
    )


async def _load_batch_read(db: DbSession, batch: PasteurisationBatch) -> PasteurisationRead:
    grouped = await load_phase_records(db, [batch.id])
    return _batch_read(batch, grouped.get(batch.id, {}))


@router.get("", response_model=list[PasteurisationRead], dependencies=[_ANY_ROLE])
async def list_pasteurisations(
    db: DbSession,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    lot: Annotated[str | None, Query(max_length=80)] = None,
) -> list[PasteurisationRead]:
    query = select(PasteurisationBatch).where(PasteurisationBatch.deleted_at.is_(None))
    if from_date is not None:
        query = query.where(PasteurisationBatch.batch_date >= from_date)
    if to_date is not None:
        query = query.where(PasteurisationBatch.batch_date <= to_date)
    if lot and lot.strip():
        query = query.where(
            func.lower(PasteurisationBatch.lot_number).contains(
                lot.strip().lower(), autoescape=True
            )
        )
    query = query.order_by(
        PasteurisationBatch.batch_date.desc(),
        PasteurisationBatch.created_at.desc(),
    )

    batches = list(await db.scalars(query))
    grouped = await load_phase_records(db, [batch.id for batch in batches])
    return [_batch_read(batch, grouped.get(batch.id, {})) for batch in batches]


@router.post("", response_model=PasteurisationRead, status_code=201, dependencies=[_ANY_ROLE])
async def create_pasteurisation(
    payload: PasteurisationBatchWrite,
    db: DbSession,
) -> PasteurisationRead:
    ensure_not_in_the_future(payload.batch_date, code="pasteurisation_date_out_of_range")

    batch = PasteurisationBatch(
        batch_date=payload.batch_date,
        product_name=payload.product_name,
        lot_number=payload.lot_number,
        quantity=payload.quantity,
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return _batch_read(batch, {})


@router.get("/{batch_id}", response_model=PasteurisationRead, dependencies=[_ANY_ROLE])
async def get_pasteurisation(batch_id: uuid.UUID, db: DbSession) -> PasteurisationRead:
    batch = await get_active_pasteurisation(db, batch_id)
    return await _load_batch_read(db, batch)


@router.put("/{batch_id}", response_model=PasteurisationRead, dependencies=[_ANY_ROLE])
async def update_pasteurisation(
    batch_id: uuid.UUID,
    payload: PasteurisationBatchWrite,
    db: DbSession,
) -> PasteurisationRead:
    batch = await get_active_pasteurisation(db, batch_id, for_update=True)
    ensure_not_in_the_future(payload.batch_date, code="pasteurisation_date_out_of_range")

    batch.batch_date = payload.batch_date
    batch.product_name = payload.product_name
    batch.lot_number = payload.lot_number
    batch.quantity = payload.quantity
    await db.commit()
    # `updated_at` is generated server side: reload it before reading the row.
    await db.refresh(batch)
    return await _load_batch_read(db, batch)


@router.delete("/{batch_id}", status_code=204, dependencies=[_ADMIN_ONLY])
async def delete_pasteurisation(batch_id: uuid.UUID, db: DbSession) -> None:
    batch = await get_active_pasteurisation(db, batch_id, for_update=True)
    batch.deleted_at = datetime.now(UTC)
    await db.commit()


@router.put("/{batch_id}/phases/{phase}", response_model=PasteurisationRead)
async def upsert_pasteurisation_phase(
    batch_id: uuid.UUID,
    phase: PasteurisationPhase,
    payload: PasteurisationPhaseWrite,
    db: DbSession,
    user: WritingUser,
) -> PasteurisationRead:
    batch = await get_active_pasteurisation(db, batch_id, for_update=True)
    record = await db.scalar(
        select(PasteurisationPhaseRecord)
        .where(
            PasteurisationPhaseRecord.batch_id == batch.id,
            PasteurisationPhaseRecord.phase == phase,
        )
        .with_for_update()
    )
    is_new = record is None
    if record is None:
        record = PasteurisationPhaseRecord(batch_id=batch.id, phase=phase)
        db.add(record)

    previous: dict[str, Any] = {field: getattr(record, field) for field in PHASE_FIELDS}
    for field in PHASE_FIELDS:
        if field in payload.model_fields_set:
            value = getattr(payload, field)
            if field == "target_temperature_celsius" and value is not None:
                value = as_celsius(value)
            setattr(record, field, value)

    if (
        record.started_at is not None
        and record.ended_at is not None
        and record.ended_at <= record.started_at
    ):
        raise ApiError(
            422,
            "pasteurisation_phase_time_invalid",
            "The end time must be later than the start time",
        )

    if is_new and not _record_is_filled(record):
        # An explicit null on an empty phase changes nothing: no row, no audit.
        db.expunge(record)
        return await _load_batch_read(db, batch)

    changed = [field for field in PHASE_FIELDS if previous[field] != getattr(record, field)]
    if not is_new and not changed:
        return await _load_batch_read(db, batch)

    await db.flush()
    db.add(
        PasteurisationPhaseEdit(
            phase_id=record.id,
            action=(
                PasteurisationPhaseEditAction.CREATED
                if is_new
                else PasteurisationPhaseEditAction.UPDATED
            ),
            previous_started_at=previous["started_at"],
            new_started_at=record.started_at,
            previous_ended_at=previous["ended_at"],
            new_ended_at=record.ended_at,
            previous_target_temperature_celsius=previous["target_temperature_celsius"],
            new_target_temperature_celsius=record.target_temperature_celsius,
            previous_observation=previous["observation"],
            new_observation=record.observation,
            changed_by=user.id,
        )
    )
    await db.commit()
    return await _load_batch_read(db, batch)


@router.get(
    "/{batch_id}/phases/{phase}/history",
    response_model=list[PasteurisationPhaseEditRead],
    dependencies=[_ANY_ROLE],
)
async def pasteurisation_phase_history(
    batch_id: uuid.UUID,
    phase: PasteurisationPhase,
    db: DbSession,
) -> list[PasteurisationPhaseEditRead]:
    await get_active_pasteurisation(db, batch_id)
    record = await db.scalar(
        select(PasteurisationPhaseRecord).where(
            PasteurisationPhaseRecord.batch_id == batch_id,
            PasteurisationPhaseRecord.phase == phase,
        )
    )
    if record is None:
        return []

    rows = await db.execute(
        select(PasteurisationPhaseEdit, User.email)
        .outerjoin(User, User.id == PasteurisationPhaseEdit.changed_by)
        .where(PasteurisationPhaseEdit.phase_id == record.id)
        .order_by(PasteurisationPhaseEdit.changed_at.desc())
    )
    return [
        PasteurisationPhaseEditRead(
            action=edit.action,
            previous_started_at=edit.previous_started_at,
            new_started_at=edit.new_started_at,
            previous_ended_at=edit.previous_ended_at,
            new_ended_at=edit.new_ended_at,
            previous_target_temperature_celsius=edit.previous_target_temperature_celsius,
            new_target_temperature_celsius=edit.new_target_temperature_celsius,
            previous_observation=edit.previous_observation,
            new_observation=edit.new_observation,
            changed_by_email=email,
            changed_at=edit.changed_at,
        )
        for edit, email in rows
    ]
