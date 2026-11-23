from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.api.deps import DbSession, require_role
from app.core.errors import ApiError
from app.models.temperature_reading import (
    ReadingEditAction,
    ReadingSlot,
    ReadingSource,
    TemperatureReading,
)
from app.models.user import User, UserRole
from app.schemas.temperature_reading import (
    TemperatureReadingCorrectionRead,
    TemperatureReadingDayRead,
    TemperatureReadingEditRead,
    TemperatureReadingSlotRead,
    TemperatureReadingWrite,
)
from app.services.equipment import get_active_equipment
from app.services.temperature import (
    effective_compliance,
    effective_source,
    effective_temperature,
    evaluate_compliance,
    requested_slots,
    resolve_range,
    validate_reading_date,
)

router = APIRouter(prefix="/equipment/{equipment_id}/readings", tags=["readings"])

_ANY_ROLE = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))
ReadingWriter = Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))]


@dataclass(frozen=True)
class LoadedReading:
    reading: TemperatureReading
    corrected_by_email: str | None


def _slot_read(
    loaded: LoadedReading | None,
    *,
    effective: bool,
) -> TemperatureReadingSlotRead | None:
    if loaded is None:
        return None
    reading = loaded.reading
    if effective and reading.corrected_temperature_celsius is not None:
        if reading.corrected_is_compliant is None or reading.corrected_at is None:
            raise RuntimeError("Incomplete corrected temperature reading")
        return TemperatureReadingSlotRead(
            temperature_celsius=float(reading.corrected_temperature_celsius),
            is_compliant=effective_compliance(reading),
            source=effective_source(reading),
            recorded_at=reading.recorded_at,
            updated_at=reading.corrected_at,
        )
    return TemperatureReadingSlotRead(
        temperature_celsius=float(reading.temperature_celsius),
        is_compliant=reading.is_compliant,
        source=reading.source,
        recorded_at=reading.recorded_at,
        updated_at=reading.updated_at,
    )


def _correction_read(
    loaded: LoadedReading | None,
) -> TemperatureReadingCorrectionRead | None:
    if loaded is None:
        return None
    reading = loaded.reading
    if reading.corrected_temperature_celsius is None:
        return None
    if reading.corrected_is_compliant is None or reading.corrected_at is None:
        raise RuntimeError("Incomplete corrected temperature reading")
    if reading.correction_justification is None:
        raise RuntimeError("Correction justification is missing")
    return TemperatureReadingCorrectionRead(
        previous_celsius=float(reading.temperature_celsius),
        new_celsius=float(reading.corrected_temperature_celsius),
        is_compliant=reading.corrected_is_compliant,
        justification=reading.correction_justification,
        changed_by_email=loaded.corrected_by_email,
        changed_at=reading.corrected_at,
    )


def _day_read(
    reading_date: date,
    readings: dict[ReadingSlot, LoadedReading],
) -> TemperatureReadingDayRead:
    morning = readings.get(ReadingSlot.MORNING)
    evening = readings.get(ReadingSlot.EVENING)
    return TemperatureReadingDayRead(
        reading_date=reading_date,
        morning=_slot_read(morning, effective=True),
        evening=_slot_read(evening, effective=True),
        morning_original=_slot_read(morning, effective=False),
        evening_original=_slot_read(evening, effective=False),
        morning_modified=_correction_read(morning),
        evening_modified=_correction_read(evening),
    )


async def _load_readings(
    db: DbSession,
    equipment_id: uuid.UUID,
    start: date,
    end: date,
) -> dict[date, dict[ReadingSlot, LoadedReading]]:
    rows = await db.execute(
        select(TemperatureReading, User.email)
        .outerjoin(User, User.id == TemperatureReading.corrected_by)
        .where(
            TemperatureReading.equipment_id == equipment_id,
            TemperatureReading.reading_date >= start,
            TemperatureReading.reading_date <= end,
        )
    )
    grouped: dict[date, dict[ReadingSlot, LoadedReading]] = {}
    for reading, corrected_by_email in rows:
        grouped.setdefault(reading.reading_date, {})[reading.slot] = LoadedReading(
            reading=reading,
            corrected_by_email=corrected_by_email,
        )
    return grouped


def _justification(payload: TemperatureReadingWrite, slot: ReadingSlot) -> str | None:
    if slot is ReadingSlot.MORNING:
        return payload.morning_justification
    return payload.evening_justification


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

    prepared: list[tuple[ReadingSlot, Decimal, bool, LoadedReading | None, str | None]] = []
    for slot, value in slots.items():
        compliant = evaluate_compliance(
            value,
            equipment.min_temperature_celsius,
            equipment.max_temperature_celsius,
        )
        current = existing.get(slot)
        if current is None:
            prepared.append((slot, value, compliant, None, None))
            continue
        if effective_temperature(current.reading) == value:
            continue
        justification = _justification(payload, slot)
        if justification is None:
            raise ApiError(
                422,
                "reading_justification_required",
                "A justification is required to correct an existing reading",
                context={"slot": slot.value},
            )
        prepared.append((slot, value, compliant, current, justification))

    for slot, value, compliant, current, justification in prepared:
        if current is None:
            reading = TemperatureReading(
                equipment_id=equipment.id,
                reading_date=reading_date,
                slot=slot,
                temperature_celsius=value,
                is_compliant=compliant,
                source=ReadingSource.MANUAL,
                recorded_at=recorded_at,
                created_by=user.id,
            )
            db.add(reading)
            await db.flush()
            existing[slot] = LoadedReading(
                reading=reading,
                corrected_by_email=None,
            )
        else:
            current.reading.corrected_temperature_celsius = value
            current.reading.corrected_is_compliant = compliant
            current.reading.correction_justification = justification
            current.reading.corrected_by = user.id
            current.reading.corrected_at = recorded_at

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

    created_user = aliased(User)
    corrected_user = aliased(User)
    rows = await db.execute(
        select(
            TemperatureReading,
            created_user.email,
            corrected_user.email,
        )
        .outerjoin(created_user, created_user.id == TemperatureReading.created_by)
        .outerjoin(corrected_user, corrected_user.id == TemperatureReading.corrected_by)
        .where(
            TemperatureReading.equipment_id == equipment_id,
            TemperatureReading.reading_date == reading_date,
        )
    )
    entries: list[tuple[datetime, int, TemperatureReadingEditRead]] = []
    slot_order = {ReadingSlot.MORNING: 0, ReadingSlot.EVENING: 1}
    for reading, created_email, corrected_email in rows:
        entries.append(
            (
                reading.recorded_at,
                slot_order[reading.slot],
                TemperatureReadingEditRead(
                    slot=reading.slot,
                    action=ReadingEditAction.CREATED,
                    previous_celsius=None,
                    new_celsius=float(reading.temperature_celsius),
                    justification=None,
                    changed_by_email=created_email,
                    changed_at=reading.recorded_at,
                ),
            )
        )
        if reading.corrected_temperature_celsius is not None:
            if reading.corrected_at is None or reading.correction_justification is None:
                raise RuntimeError("Incomplete corrected temperature reading")
            entries.append(
                (
                    reading.corrected_at,
                    slot_order[reading.slot],
                    TemperatureReadingEditRead(
                        slot=reading.slot,
                        action=ReadingEditAction.UPDATED,
                        previous_celsius=float(reading.temperature_celsius),
                        new_celsius=float(reading.corrected_temperature_celsius),
                        justification=reading.correction_justification,
                        changed_by_email=corrected_email,
                        changed_at=reading.corrected_at,
                    ),
                )
            )
    entries.sort(key=lambda entry: (entry[0], entry[1]), reverse=True)
    return [entry for _, _, entry in entries]


@router.get("/{reading_date}", response_model=TemperatureReadingDayRead, dependencies=[_ANY_ROLE])
async def get_reading_day(
    equipment_id: uuid.UUID,
    reading_date: date,
    db: DbSession,
) -> TemperatureReadingDayRead:
    await get_active_equipment(db, equipment_id)
    grouped = await _load_readings(db, equipment_id, reading_date, reading_date)
    return _day_read(reading_date, grouped.get(reading_date, {}))
