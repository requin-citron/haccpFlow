from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cleaning_plan import CleaningPlan, CleaningRecord, CleaningRecordEdit
from app.models.equipment import Equipment
from app.models.pasteurisation import (
    PasteurisationBatch,
    PasteurisationPhaseEdit,
    PasteurisationPhaseRecord,
)
from app.models.temperature_reading import (
    ReadingSlot,
    TemperatureReading,
    TemperatureReadingEdit,
)
from app.models.transport import Transport, TransportEdit
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.history import (
    HistoryAction,
    HistoryChangeRead,
    HistoryEntity,
    HistoryEntryRead,
)

DEFAULT_LIMIT = 50
MAX_LIMIT = 200

_SLOT_LABELS = {ReadingSlot.MORNING: "matin", ReadingSlot.EVENING: "soir"}

_PHASE_LABELS = {
    "preheating": "préchauffage",
    "holding": "palier (pasteurisation)",
    "cooling": "refroidissement",
}


def _as_text(value: Any) -> str | None:
    """Render an audit value as a short human string."""

    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _change(
    field: str,
    label: str,
    previous: Any,
    new: Any,
) -> HistoryChangeRead | None:
    if previous == new:
        return None
    return HistoryChangeRead(
        field=field,
        label=label,
        previous=_as_text(previous),
        new=_as_text(new),
    )


def _compact(changes: list[HistoryChangeRead | None]) -> list[HistoryChangeRead]:
    return [change for change in changes if change is not None]


async def _reading_entries(
    db: AsyncSession,
    start: datetime | None,
    end: datetime | None,
    limit: int,
) -> list[HistoryEntryRead]:
    query = (
        select(
            TemperatureReadingEdit,
            TemperatureReading.slot,
            TemperatureReading.reading_date,
            Equipment.id,
            Equipment.name,
            User.email,
        )
        .join(TemperatureReading, TemperatureReading.id == TemperatureReadingEdit.reading_id)
        .join(Equipment, Equipment.id == TemperatureReading.equipment_id)
        .outerjoin(User, User.id == TemperatureReadingEdit.changed_by)
        .order_by(TemperatureReadingEdit.changed_at.desc())
        .limit(limit)
    )
    if start is not None:
        query = query.where(TemperatureReadingEdit.changed_at >= start)
    if end is not None:
        query = query.where(TemperatureReadingEdit.changed_at <= end)

    entries: list[HistoryEntryRead] = []
    for edit, slot, reading_date, equipment_id, equipment_name, email in await db.execute(query):
        entries.append(
            HistoryEntryRead(
                id=edit.id,
                occurred_at=edit.changed_at,
                entity=HistoryEntity.TEMPERATURE_READING,
                action=HistoryAction(str(edit.action)),
                actor_email=email,
                target_id=equipment_id,
                subject=equipment_name,
                detail=f"Relevé du {reading_date.isoformat()} · {_SLOT_LABELS[slot]}",
                changes=_compact(
                    [
                        _change(
                            "temperature_celsius",
                            "Température",
                            edit.previous_celsius,
                            edit.new_celsius,
                        )
                    ]
                ),
            )
        )
    return entries


async def _cleaning_entries(
    db: AsyncSession,
    start: datetime | None,
    end: datetime | None,
    limit: int,
) -> list[HistoryEntryRead]:
    query = (
        select(
            CleaningRecordEdit,
            CleaningPlan.id,
            CleaningPlan.name,
            User.email,
        )
        .join(CleaningRecord, CleaningRecord.id == CleaningRecordEdit.record_id)
        .join(CleaningPlan, CleaningPlan.id == CleaningRecord.plan_id)
        .outerjoin(User, User.id == CleaningRecordEdit.changed_by)
        .order_by(CleaningRecordEdit.changed_at.desc())
        .limit(limit)
    )
    if start is not None:
        query = query.where(CleaningRecordEdit.changed_at >= start)
    if end is not None:
        query = query.where(CleaningRecordEdit.changed_at <= end)

    entries: list[HistoryEntryRead] = []
    for edit, plan_id, plan_name, email in await db.execute(query):
        reference = edit.new_cleaning_date or edit.previous_cleaning_date
        entries.append(
            HistoryEntryRead(
                id=edit.id,
                occurred_at=edit.changed_at,
                entity=HistoryEntity.CLEANING_RECORD,
                action=HistoryAction(str(edit.action)),
                actor_email=email,
                target_id=plan_id,
                subject=plan_name,
                detail=(
                    f"Nettoyage du {reference.isoformat()}"
                    if reference is not None
                    else "Nettoyage"
                ),
                changes=_compact(
                    [
                        _change(
                            "cleaning_date",
                            "Date du nettoyage",
                            edit.previous_cleaning_date,
                            edit.new_cleaning_date,
                        ),
                        _change(
                            "comment",
                            "Commentaire",
                            edit.previous_comment,
                            edit.new_comment,
                        ),
                    ]
                ),
            )
        )
    return entries


async def _pasteurisation_entries(
    db: AsyncSession,
    start: datetime | None,
    end: datetime | None,
    limit: int,
) -> list[HistoryEntryRead]:
    query = (
        select(
            PasteurisationPhaseEdit,
            PasteurisationPhaseRecord.phase,
            PasteurisationBatch.id,
            PasteurisationBatch.product_name,
            PasteurisationBatch.lot_number,
            User.email,
        )
        .join(
            PasteurisationPhaseRecord,
            PasteurisationPhaseRecord.id == PasteurisationPhaseEdit.phase_id,
        )
        .join(
            PasteurisationBatch,
            PasteurisationBatch.id == PasteurisationPhaseRecord.batch_id,
        )
        .outerjoin(User, User.id == PasteurisationPhaseEdit.changed_by)
        .order_by(PasteurisationPhaseEdit.changed_at.desc())
        .limit(limit)
    )
    if start is not None:
        query = query.where(PasteurisationPhaseEdit.changed_at >= start)
    if end is not None:
        query = query.where(PasteurisationPhaseEdit.changed_at <= end)

    entries: list[HistoryEntryRead] = []
    for edit, phase, batch_id, product_name, lot_number, email in await db.execute(query):
        entries.append(
            HistoryEntryRead(
                id=edit.id,
                occurred_at=edit.changed_at,
                entity=HistoryEntity.PASTEURISATION_PHASE,
                action=HistoryAction(str(edit.action)),
                actor_email=email,
                target_id=batch_id,
                subject=f"{product_name} · lot {lot_number}",
                detail=f"Phase {_PHASE_LABELS[str(phase)]}",
                changes=_compact(
                    [
                        _change(
                            "started_at",
                            "Heure de début",
                            edit.previous_started_at,
                            edit.new_started_at,
                        ),
                        _change(
                            "ended_at",
                            "Heure de fin",
                            edit.previous_ended_at,
                            edit.new_ended_at,
                        ),
                        _change(
                            "target_temperature_celsius",
                            "Température cible",
                            edit.previous_target_temperature_celsius,
                            edit.new_target_temperature_celsius,
                        ),
                        _change(
                            "observation",
                            "Observation",
                            edit.previous_observation,
                            edit.new_observation,
                        ),
                    ]
                ),
            )
        )
    return entries


async def _transport_entries(
    db: AsyncSession,
    start: datetime | None,
    end: datetime | None,
    limit: int,
) -> list[HistoryEntryRead]:
    query = (
        select(
            TransportEdit,
            Transport.id,
            Transport.product_name,
            Transport.place,
            Transport.transport_date,
            Transport.vehicle_label,
            Vehicle.name,
            Vehicle.plate,
            User.email,
        )
        .join(Transport, Transport.id == TransportEdit.transport_id)
        .outerjoin(Vehicle, Vehicle.id == Transport.vehicle_id)
        .outerjoin(User, User.id == TransportEdit.changed_by)
        .order_by(TransportEdit.changed_at.desc())
        .limit(limit)
    )
    if start is not None:
        query = query.where(TransportEdit.changed_at >= start)
    if end is not None:
        query = query.where(TransportEdit.changed_at <= end)

    entries: list[HistoryEntryRead] = []
    for (
        edit,
        transport_id,
        product_name,
        place,
        transport_date,
        vehicle_label,
        vehicle_name,
        vehicle_plate,
        email,
    ) in await db.execute(query):
        vehicle = vehicle_name or vehicle_plate or vehicle_label or "véhicule inconnu"
        entries.append(
            HistoryEntryRead(
                id=edit.id,
                occurred_at=edit.changed_at,
                entity=HistoryEntity.TRANSPORT,
                action=HistoryAction(str(edit.action)),
                actor_email=email,
                target_id=transport_id,
                subject=f"{product_name} · {place}",
                detail=f"Transport du {transport_date.isoformat()} · {vehicle}",
                changes=_compact(
                    [
                        _change(
                            "departure_time",
                            "Heure de départ",
                            edit.previous_departure_time,
                            edit.new_departure_time,
                        ),
                        _change(
                            "departure_temperature_celsius",
                            "Température de départ",
                            edit.previous_departure_temperature_celsius,
                            edit.new_departure_temperature_celsius,
                        ),
                        _change(
                            "arrival_time",
                            "Heure d'arrivée",
                            edit.previous_arrival_time,
                            edit.new_arrival_time,
                        ),
                        _change(
                            "arrival_temperature_celsius",
                            "Température d'arrivée",
                            edit.previous_arrival_temperature_celsius,
                            edit.new_arrival_temperature_celsius,
                        ),
                        _change(
                            "observation",
                            "Observation",
                            edit.previous_observation,
                            edit.new_observation,
                        ),
                    ]
                ),
            )
        )
    return entries


_COLLECTORS = {
    HistoryEntity.TEMPERATURE_READING: _reading_entries,
    HistoryEntity.CLEANING_RECORD: _cleaning_entries,
    HistoryEntity.PASTEURISATION_PHASE: _pasteurisation_entries,
    HistoryEntity.TRANSPORT: _transport_entries,
}


def resolve_window(
    from_date: date | None,
    to_date: date | None,
) -> tuple[datetime | None, datetime | None]:
    """Turn inclusive calendar days into a UTC datetime window."""

    start = datetime.combine(from_date, time.min, tzinfo=UTC) if from_date is not None else None
    end = (
        datetime.combine(to_date, time.min, tzinfo=UTC) + timedelta(days=1)
        if to_date is not None
        else None
    )
    return start, end


async def collect_history(
    db: AsyncSession,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
    entity: HistoryEntity | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[HistoryEntryRead]:
    """Merged audit feed, most recent first.

    Each source is capped at `limit`, which is enough: the merged top-N can
    never need more rows than the top-N of any single source.
    """

    capped = max(1, min(limit, MAX_LIMIT))
    start, end = resolve_window(from_date, to_date)
    selected = [entity] if entity is not None else list(_COLLECTORS)

    entries: list[HistoryEntryRead] = []
    for source in selected:
        entries.extend(await _COLLECTORS[source](db, start, end, capped))

    entries.sort(key=lambda entry: entry.occurred_at, reverse=True)
    return entries[:capped]
