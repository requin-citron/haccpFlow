from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.api.deps import DbSession, require_role
from app.core.errors import ApiError
from app.models.temperature_reading import (
    ReadingEditAction,
    ReadingSlot,
    ReadingSource,
    TemperatureReading,
    TemperatureReadingEdit,
)
from app.models.user import User, UserRole
from app.schemas.temperature_reading import (
    TemperatureReadingDayRead,
    TemperatureReadingEditRead,
    TemperatureReadingSlotRead,
    TemperatureReadingWrite,
)
from app.services.equipment import get_active_equipment
from app.services.temperature import (
    evaluate_compliance,
    requested_slots,
    resolve_range,
    validate_reading_date,
)

router = APIRouter(prefix="/equipment/{equipment_id}/readings", tags=["readings"])

_ANY_ROLE = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))
ReadingWriter = Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))]


def _slot_read(reading: TemperatureReading | None) -> TemperatureReadingSlotRead | None:
    if reading is None:
        return None
    return TemperatureReadingSlotRead.model_validate(reading)


def _day_read(
    reading_date: date,
    readings: dict[ReadingSlot, TemperatureReading],
) -> TemperatureReadingDayRead:
    return TemperatureReadingDayRead(
        reading_date=reading_date,
        morning=_slot_read(readings.get(ReadingSlot.MORNING)),
        evening=_slot_read(readings.get(ReadingSlot.EVENING)),
    )


async def _load_readings(
    db: DbSession,
    equipment_id: uuid.UUID,
    start: date,
    end: date,
) -> dict[date, dict[ReadingSlot, TemperatureReading]]:
    rows = await db.scalars(
        select(TemperatureReading).where(
            TemperatureReading.equipment_id == equipment_id,
            TemperatureReading.reading_date >= start,
            TemperatureReading.reading_date <= end,
        )
    )
    grouped: dict[date, dict[ReadingSlot, TemperatureReading]] = {}
    for row in rows:
        grouped.setdefault(row.reading_date, {})[row.slot] = row
    return grouped


@router.put("/{reading_date}", response_model=TemperatureReadingDayRead)
async def upsert_reading_day(
    equipment_id: uuid.UUID,
    reading_date: date,
    payload: TemperatureReadingWrite,
    db: DbSession,
    user: ReadingWriter,
) -> TemperatureReadingDayRead:
    # Locking the equipment serialises concurrent writes for the same unit.
    equipment = await get_active_equipment(db, equipment_id, for_update=True)
    validate_reading_date(reading_date)

    slots = requested_slots(payload)
    if not slots:
        raise ApiError(
            422,
            "reading_value_required",
            "Provide at least one of morning_celsius or evening_celsius",
        )

    existing = (await _load_readings(db, equipment_id, reading_date, reading_date)).get(
        reading_date, {}
    )
    recorded_at = datetime.now(UTC)

    for slot, value in slots.items():
        compliant = evaluate_compliance(
            value,
            equipment.min_temperature_celsius,
            equipment.max_temperature_celsius,
        )
        current = existing.get(slot)
        if current is None:
            reading = TemperatureReading(
                equipment_id=equipment.id,
                reading_date=reading_date,
                slot=slot,
                temperature_celsius=value,
                is_compliant=compliant,
                source=ReadingSource.MANUAL,
                recorded_at=recorded_at,
            )
            db.add(reading)
            await db.flush()
            db.add(
                TemperatureReadingEdit(
                    reading_id=reading.id,
                    action=ReadingEditAction.CREATED,
                    previous_celsius=None,
                    new_celsius=value,
                    changed_by=user.id,
                )
            )
            existing[slot] = reading
        elif current.temperature_celsius != value:
            db.add(
                TemperatureReadingEdit(
                    reading_id=current.id,
                    action=ReadingEditAction.UPDATED,
                    previous_celsius=current.temperature_celsius,
                    new_celsius=value,
                    changed_by=user.id,
                )
            )
            current.temperature_celsius = value
            current.is_compliant = compliant
            # A human correction takes the reading away from the sensor.
            current.source = ReadingSource.MANUAL

    await db.commit()
    # Re-read after commit: freshly inserted rows only load their server-side
    # defaults (updated_at) through a SELECT.
    refreshed = await _load_readings(db, equipment_id, reading_date, reading_date)
    return _day_read(reading_date, refreshed.get(reading_date, {}))


@router.get("", response_model=list[TemperatureReadingDayRead], dependencies=[_ANY_ROLE])
async def list_reading_days(
    equipment_id: uuid.UUID,
    db: DbSession,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
) -> list[TemperatureReadingDayRead]:
    await get_active_equipment(db, equipment_id)
    start, end = resolve_range(from_date, to_date)

    grouped = await _load_readings(db, equipment_id, start, end)
    days: list[TemperatureReadingDayRead] = []
    current = start
    while current <= end:
        days.append(_day_read(current, grouped.get(current, {})))
        current += timedelta(days=1)
    return days


@router.get(
    "/{reading_date}/history",
    response_model=list[TemperatureReadingEditRead],
    dependencies=[_ANY_ROLE],
)
async def reading_history(
    equipment_id: uuid.UUID,
    reading_date: date,
    db: DbSession,
) -> list[TemperatureReadingEditRead]:
    await get_active_equipment(db, equipment_id)

    rows = await db.execute(
        select(TemperatureReadingEdit, TemperatureReading.slot, User.email)
        .join(TemperatureReading, TemperatureReading.id == TemperatureReadingEdit.reading_id)
        .outerjoin(User, User.id == TemperatureReadingEdit.changed_by)
        .where(
            TemperatureReading.equipment_id == equipment_id,
            TemperatureReading.reading_date == reading_date,
        )
        .order_by(TemperatureReadingEdit.changed_at.desc(), TemperatureReading.slot)
    )
    return [
        TemperatureReadingEditRead(
            slot=slot,
            action=edit.action,
            previous_celsius=edit.previous_celsius,
            new_celsius=edit.new_celsius,
            changed_by_email=email,
            changed_at=edit.changed_at,
        )
        for edit, slot, email in rows
    ]


@router.get("/{reading_date}", response_model=TemperatureReadingDayRead, dependencies=[_ANY_ROLE])
async def get_reading_day(
    equipment_id: uuid.UUID,
    reading_date: date,
    db: DbSession,
) -> TemperatureReadingDayRead:
    await get_active_equipment(db, equipment_id)
    grouped = await _load_readings(db, equipment_id, reading_date, reading_date)
    return _day_read(reading_date, grouped.get(reading_date, {}))
