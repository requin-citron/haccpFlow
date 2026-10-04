from __future__ import annotations

import csv
import io
import re
import unicodedata
import uuid
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.errors import ApiError
from app.models.cash_register import DENOMINATIONS, CashRegister
from app.models.cash_session import CashExpense, CashExpenseKind, CashSession
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
from app.services.cash_session import (
    closing_counts_of,
    closing_total_cents,
    counts_from,
    expenses_total_cents,
    opening_total_cents,
)
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
_CENT_LABELS = {
    1: "1 centime",
    2: "2 centimes",
    5: "5 centimes",
    10: "10 centimes",
    20: "20 centimes",
    50: "50 centimes",
    100: "1 euro",
    200: "2 euros",
    500: "5 euros",
    1000: "10 euros",
    2000: "20 euros",
    5000: "50 euros",
}
_DENOMINATION_LABELS = {field: _CENT_LABELS[cents] for field, cents in DENOMINATIONS}
_EXPENSE_KIND_LABELS = {
    CashExpenseKind.PROFESSIONAL: "Frais pro",
    CashExpenseKind.PERSONAL: "Frais perso",
}

Extract = tuple[list[str], list[list[str]]]


class CashSessionExport(NamedTuple):
    """One session's extract: the file name and the CSV itself."""

    filename: str
    content: str


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


def _decimal(value: Decimal | None) -> str:
    """Decimal comma, so Excel reads the cell as a number."""

    return f"{value:.2f}".replace(".", ",") if value is not None else ""


def _euros(cents: int) -> str:
    """Cents to an amount Excel reads as a number, e.g. 8228 -> "82,28"."""

    return f"{cents / 100:.2f}".replace(".", ",")


def _slugify(value: str) -> str:
    """A file-name-safe version of a register name, accents folded."""

    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


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
                _decimal(reading.temperature_celsius),
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
                    _decimal(record.target_temperature_celsius),
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
                _decimal(transport.departure_temperature_celsius),
                _time(transport.arrival_time),
                _decimal(transport.arrival_temperature_celsius),
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


def _count_rows(counts: dict[str, int]) -> list[list[str]]:
    rows = [["Coupure", "Nombre", "Montant (€)"]]
    for field, cents in DENOMINATIONS:
        count = int(counts.get(field, 0))
        rows.append([_DENOMINATION_LABELS[field], str(count), _euros(count * cents)])
    return rows


async def _expenses_by_session(
    db: AsyncSession,
    session_ids: Sequence[uuid.UUID],
) -> dict[uuid.UUID, list[CashExpense]]:
    """Every expense of the given sessions, grouped, in a single query."""

    grouped: dict[uuid.UUID, list[CashExpense]] = {}
    if not session_ids:
        return grouped
    for expense in await db.scalars(
        select(CashExpense)
        .where(CashExpense.session_id.in_(session_ids))
        .order_by(CashExpense.created_at, CashExpense.id)
    ):
        grouped.setdefault(expense.session_id, []).append(expense)
    return grouped


async def _cash_registers(db: AsyncSession, start: date | None, end: date | None) -> Extract:
    """The successive states of the registers: one row per tracking session."""

    headers = ["Caisse", "Date", "Fond — total (€)"]
    headers.extend(f"Fond — {_DENOMINATION_LABELS[field]}" for field, _ in DENOMINATIONS)
    headers.extend(
        ["Frais pro (€)", "Frais perso (€)", "Total des frais (€)", "Clôture — total (€)"]
    )
    headers.extend(f"Clôture — {_DENOMINATION_LABELS[field]}" for field, _ in DENOMINATIONS)
    headers.extend(["Ouvert par", "Ouvert le", "Clôturé par", "Clôturé le", "Supprimé le"])

    opened_user = aliased(User)
    closed_user = aliased(User)
    query = (
        select(CashSession, CashRegister.name, opened_user.email, closed_user.email)
        .join(CashRegister, CashRegister.id == CashSession.cash_register_id)
        .outerjoin(opened_user, opened_user.id == CashSession.opened_by)
        .outerjoin(closed_user, closed_user.id == CashSession.closed_by)
        .order_by(
            func.lower(CashRegister.name),
            CashSession.session_date,
            CashSession.created_at,
        )
    )
    if start is not None:
        query = query.where(CashSession.session_date >= start)
    if end is not None:
        query = query.where(CashSession.session_date <= end)

    rows_data = list(await db.execute(query))
    expenses = await _expenses_by_session(db, [session.id for session, _, _, _ in rows_data])

    rows: list[list[str]] = []
    for session, register_name, opened_email, closed_email in rows_data:
        session_expenses = expenses.get(session.id, [])
        opening = counts_from(session)
        closing = closing_counts_of(session)
        row = [register_name, _date(session.session_date), _euros(opening_total_cents(session))]
        row.extend(str(opening[field]) for field, _ in DENOMINATIONS)
        row.extend(
            [
                _euros(expenses_total_cents(session_expenses, kind=CashExpenseKind.PROFESSIONAL)),
                _euros(expenses_total_cents(session_expenses, kind=CashExpenseKind.PERSONAL)),
                _euros(expenses_total_cents(session_expenses)),
                "" if closing is None else _euros(closing_total_cents(session) or 0),
            ]
        )
        row.extend("" if closing is None else str(closing[field]) for field, _ in DENOMINATIONS)
        row.extend(
            [
                _text(opened_email),
                _datetime(session.created_at),
                _text(closed_email),
                _datetime(session.closed_at),
                _datetime(session.deleted_at),
            ]
        )
        rows.append(row)
    return headers, rows


def _session_extract(
    session: CashSession,
    *,
    register_name: str,
    opened_by_email: str | None,
    closed_by_email: str | None,
    expenses: Sequence[CashExpense],
) -> Extract:
    """One session as a block-per-block document, readable for a control."""

    headers = ["Suivi de caisse", register_name]
    rows: list[list[str]] = [
        ["Date", _date(session.session_date)],
        ["Ouvert par", _text(opened_by_email)],
        ["Ouvert le", _datetime(session.created_at)],
        ["Clôturé par", _text(closed_by_email)],
        ["Clôturé le", _datetime(session.closed_at)],
    ]
    if session.deleted_at is not None:
        rows.append(["Supprimé le", _datetime(session.deleted_at)])

    rows.append([])
    rows.append(["Comptage d'ouverture"])
    rows.extend(_count_rows(counts_from(session)))
    rows.append(["Total", "", _euros(opening_total_cents(session))])

    rows.append([])
    rows.append(["Frais"])
    rows.append(["Type", "Nom", "Quantité", "Prix unitaire (€)", "TVA (%)", "Total (€)"])
    for expense in expenses:
        rows.append(
            [
                _EXPENSE_KIND_LABELS[expense.kind],
                expense.name,
                str(expense.quantity),
                _euros(expense.unit_price_cents),
                _decimal(expense.vat_rate),
                _euros(expense.quantity * expense.unit_price_cents),
            ]
        )
    rows.append([])
    rows.append(["Totaux"])
    rows.append(
        [
            "Frais pro (€)",
            _euros(expenses_total_cents(expenses, kind=CashExpenseKind.PROFESSIONAL)),
        ]
    )
    rows.append(
        [
            "Frais perso (€)",
            _euros(expenses_total_cents(expenses, kind=CashExpenseKind.PERSONAL)),
        ]
    )
    rows.append(["Total des frais (€)", _euros(expenses_total_cents(expenses))])

    rows.append([])
    rows.append(["Comptage de clôture"])
    closing = closing_counts_of(session)
    if closing is None:
        rows.append(["Suivi en cours — comptage de clôture non saisi"])
    else:
        rows.extend(_count_rows(closing))
        rows.append(["Total", "", _euros(closing_total_cents(session) or 0)])
    return headers, rows


async def build_cash_session_export(db: AsyncSession, session_id: uuid.UUID) -> CashSessionExport:
    """The extract of one session, with the file name to hand out."""

    opened_user = aliased(User)
    closed_user = aliased(User)
    row = (
        await db.execute(
            select(CashSession, CashRegister.name, opened_user.email, closed_user.email)
            .join(CashRegister, CashRegister.id == CashSession.cash_register_id)
            .outerjoin(opened_user, opened_user.id == CashSession.opened_by)
            .outerjoin(closed_user, closed_user.id == CashSession.closed_by)
            .where(
                CashSession.id == session_id,
                CashSession.deleted_at.is_(None),
            )
        )
    ).one_or_none()
    if row is None:
        raise ApiError(404, "cash_session_not_found", "Cash session not found")
    session, register_name, opened_by_email, closed_by_email = row

    headers, rows = _session_extract(
        session,
        register_name=register_name,
        opened_by_email=opened_by_email,
        closed_by_email=closed_by_email,
        expenses=list(
            await db.scalars(
                select(CashExpense)
                .where(CashExpense.session_id == session.id)
                .order_by(CashExpense.created_at, CashExpense.id)
            )
        ),
    )
    slug = _slugify(register_name) or "caisse"
    filename = f"caisse-{slug}-{session.session_date.isoformat()}.csv"
    return CashSessionExport(filename=filename, content=render_csv(headers, rows))


_EXTRACTS = {
    ExportDataset.READINGS: _readings,
    ExportDataset.CLEANINGS: _cleanings,
    ExportDataset.PASTEURISATIONS: _pasteurisations,
    ExportDataset.TRANSPORTS: _transports,
    ExportDataset.CASH_REGISTERS: _cash_registers,
}

#: File-name prefixes, one per data set.
FILENAME_PREFIXES = {
    ExportDataset.READINGS: "releves",
    ExportDataset.CLEANINGS: "nettoyages",
    ExportDataset.PASTEURISATIONS: "pasteurisation",
    ExportDataset.TRANSPORTS: "transports",
    ExportDataset.CASH_REGISTERS: "caisses",
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
