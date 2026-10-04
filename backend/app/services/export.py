from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cleaning_plan import CleaningFrequency, CleaningPlan, CleaningRecord
from app.models.equipment import Equipment, EquipmentType
from app.models.pasteurisation import PasteurisationBatch, PasteurisationPhase
from app.models.temperature_reading import (
    ReadingSlot,
    ReadingSource,
    TemperatureReading,
)
from app.models.transport import Transport
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.export import ExportDataset
from app.services.pasteurisation import (
    PHASE_ORDER,
    compute_duration_minutes,
    load_phase_records,
    phase_is_complete,
)
from app.services.transport import transport_is_complete

#: Excel in French expects a semicolon delimiter, and the BOM keeps accents intact.
DELIMITER = ";"
UTF8_BOM = "\ufeff"

_EQUIPMENT_TYPE_LABELS = {
    EquipmentType.FRIDGE: "Réfrigérateur",
    EquipmentType.FREEZER: "Congélateur",
}
_SLOT_LABELS = {ReadingSlot.MORNING: "Matin", ReadingSlot.EVENING: "Soir"}
_SOURCE_LABELS = {ReadingSource.MANUAL: "Manuel", ReadingSource.SENSOR: "Capteur"}
_FREQUENCY_LABELS = {
    CleaningFrequency.AFTER_EACH_USE: "Après chaque usage",
    CleaningFrequency.DAILY: "Quotidien",
    CleaningFrequency.WEEKLY: "Hebdomadaire",
}
_PHASE_LABELS = {
    PasteurisationPhase.PREHEATING: "Préchauffage",
    PasteurisationPhase.HOLDING: "Palier (pasteurisation)",
    PasteurisationPhase.COOLING: "Refroidissement",
}

Extract = tuple[list[str], list[list[str]]]


def render_csv(headers: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
    """Render a French-Excel friendly CSV, with its UTF-8 BOM."""

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=DELIMITER, lineterminator="\r\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return UTF8_BOM + buffer.getvalue()


def _text(value: str | None) -> str:
    return value or ""


def _date(value: date | None) -> str:
    return value.strftime("%d/%m/%Y") if value is not None else ""


def _time(value: time | None) -> str:
    return value.strftime("%H:%M") if value is not None else ""


def _datetime(value: datetime | None) -> str:
    return value.astimezone(UTC).strftime("%d/%m/%Y %H:%M") if value is not None else ""


def _temperature(value: Decimal | None) -> str:
    """Decimal comma, so Excel reads the cell as a number."""

    return f"{value:.2f}".replace(".", ",") if value is not None else ""


def _boolean(value: bool) -> str:
    return "Oui" if value else "Non"


async def _readings(db: AsyncSession, start: date | None, end: date | None) -> Extract:
    headers = [
        "Matériel",
        "Type",
        "Date",
        "Créneau",
        "Température (°C)",
        "Conforme",
        "Source",
        "Relevé le",
    ]
    query = (
        select(TemperatureReading, Equipment)
        .join(Equipment, Equipment.id == TemperatureReading.equipment_id)
        .order_by(TemperatureReading.reading_date, Equipment.name)
    )
    if start is not None:
        query = query.where(TemperatureReading.reading_date >= start)
    if end is not None:
        query = query.where(TemperatureReading.reading_date <= end)

    rows: list[list[str]] = []
    for reading, equipment in await db.execute(query):
        rows.append(
            [
                equipment.name,
                _EQUIPMENT_TYPE_LABELS[equipment.type],
                _date(reading.reading_date),
                _SLOT_LABELS[reading.slot],
                _temperature(reading.temperature_celsius),
                _boolean(reading.is_compliant),
                _SOURCE_LABELS[reading.source],
                _datetime(reading.recorded_at),
            ]
        )
    return headers, rows


async def _cleanings(db: AsyncSession, start: date | None, end: date | None) -> Extract:
    headers = [
        "Plan",
        "Fréquence",
        "Produits",
        "Date du nettoyage",
        "Commentaire",
        "Déclaré par",
        "Déclaré le",
    ]
    # A deleted declaration was withdrawn as a mistake: the audit trail keeps it.
    query = (
        select(CleaningRecord, CleaningPlan, User.email)
        .join(CleaningPlan, CleaningPlan.id == CleaningRecord.plan_id)
        .outerjoin(User, User.id == CleaningRecord.performed_by)
        .where(CleaningRecord.deleted_at.is_(None))
        .order_by(CleaningRecord.cleaning_date, CleaningPlan.name)
    )
    if start is not None:
        query = query.where(CleaningRecord.cleaning_date >= start)
    if end is not None:
        query = query.where(CleaningRecord.cleaning_date <= end)

    rows: list[list[str]] = []
    for record, plan, email in await db.execute(query):
        rows.append(
            [
                plan.name,
                _FREQUENCY_LABELS[plan.frequency],
                _text(plan.products),
                _date(record.cleaning_date),
                _text(record.comment),
                _text(email),
                _datetime(record.recorded_at),
            ]
        )
    return headers, rows


async def _pasteurisations(db: AsyncSession, start: date | None, end: date | None) -> Extract:
    headers = ["Date", "Produit", "N° de lot", "Quantité"]
    for phase in PHASE_ORDER:
        label = _PHASE_LABELS[phase]
        headers.extend(
            [
                f"{label} — début",
                f"{label} — fin",
                f"{label} — température cible (°C)",
                f"{label} — durée (min)",
                f"{label} — observation",
            ]
        )
    headers.append("Phases")

    query = select(PasteurisationBatch).order_by(
        PasteurisationBatch.batch_date, PasteurisationBatch.lot_number
    )
    if start is not None:
        query = query.where(PasteurisationBatch.batch_date >= start)
    if end is not None:
        query = query.where(PasteurisationBatch.batch_date <= end)
    batches = list(await db.scalars(query))
    phases = await load_phase_records(db, [batch.id for batch in batches])

    rows: list[list[str]] = []
    for batch in batches:
        records = phases.get(batch.id, {})
        row = [
            _date(batch.batch_date),
            batch.product_name,
            batch.lot_number,
            str(batch.quantity),
        ]
        complete = True
        for phase in PHASE_ORDER:
            record = records.get(phase)
            if record is None:
                row.extend(["", "", "", "", ""])
                complete = False
                continue
            duration = compute_duration_minutes(record.started_at, record.ended_at)
            if not phase_is_complete(
                started_at=record.started_at,
                ended_at=record.ended_at,
                target_temperature_celsius=record.target_temperature_celsius,
            ):
                complete = False
            row.extend(
                [
                    _time(record.started_at),
                    _time(record.ended_at),
                    _temperature(record.target_temperature_celsius),
                    "" if duration is None else str(duration),
                    _text(record.observation),
                ]
            )
        row.append("Complet" if complete else "Incomplet")
        rows.append(row)
    return headers, rows


async def _transports(db: AsyncSession, start: date | None, end: date | None) -> Extract:
    headers = [
        "Date",
        "Produit",
        "N° de lot",
        "Lieu",
        "Véhicule",
        "Plaque",
        "Véhicule référencé",
        "Départ — heure",
        "Départ — température (°C)",
        "Arrivée — heure",
        "Arrivée — température (°C)",
        "Observation",
        "Chaîne du froid",
    ]
    query = (
        select(Transport, Vehicle)
        .outerjoin(Vehicle, Vehicle.id == Transport.vehicle_id)
        .order_by(Transport.transport_date, Transport.created_at)
    )
    if start is not None:
        query = query.where(Transport.transport_date >= start)
    if end is not None:
        query = query.where(Transport.transport_date <= end)

    rows: list[list[str]] = []
    for transport, vehicle in await db.execute(query):
        rows.append(
            [
                _date(transport.transport_date),
                transport.product_name,
                _text(transport.lot_number),
                transport.place,
                vehicle.name if vehicle is not None else _text(transport.vehicle_label),
                _text(vehicle.plate) if vehicle is not None else "",
                _boolean(vehicle is not None),
                _time(transport.departure_time),
                _temperature(transport.departure_temperature_celsius),
                _time(transport.arrival_time),
                _temperature(transport.arrival_temperature_celsius),
                _text(transport.observation),
                (
                    "Complet"
                    if transport_is_complete(
                        departure_time=transport.departure_time,
                        departure_temperature_celsius=transport.departure_temperature_celsius,
                        arrival_time=transport.arrival_time,
                        arrival_temperature_celsius=transport.arrival_temperature_celsius,
                    )
                    else "En cours"
                ),
            ]
        )
    return headers, rows


_EXTRACTS = {
    ExportDataset.READINGS: _readings,
    ExportDataset.CLEANINGS: _cleanings,
    ExportDataset.PASTEURISATIONS: _pasteurisations,
    ExportDataset.TRANSPORTS: _transports,
}

#: File-name prefixes, one per data set.
FILENAME_PREFIXES = {
    ExportDataset.READINGS: "releves",
    ExportDataset.CLEANINGS: "nettoyages",
    ExportDataset.PASTEURISATIONS: "pasteurisation",
    ExportDataset.TRANSPORTS: "transports",
}


async def build_export(
    db: AsyncSession,
    dataset: ExportDataset,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> str:
    headers, rows = await _EXTRACTS[dataset](db, from_date, to_date)
    return render_csv(headers, rows)
