from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, func, select

from app.api.deps import DbSession, require_role
from app.models.transport import Transport, TransportEdit, TransportEditAction
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle
from app.schemas.transport import (
    TransportCreate,
    TransportHeaderWrite,
    TransportRead,
    TransportReadingsWrite,
    TransportVehicleRead,
)
from app.services.dates import ensure_not_in_the_future
from app.services.temperature import as_celsius
from app.services.transport import (
    TRANSPORT_READING_FIELDS,
    get_active_transport,
    transport_is_complete,
)
from app.services.vehicle import get_active_vehicle, load_vehicle

router = APIRouter(prefix="/transports", tags=["transports"])

_ANY_ROLE = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))
_ADMIN_ONLY = Depends(require_role(UserRole.ADMIN))
WritingUser = Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))]


def _transport_query() -> Select[Any]:
    return select(Transport, Vehicle).outerjoin(Vehicle, Vehicle.id == Transport.vehicle_id)


def _transport_read(transport: Transport, vehicle: Vehicle | None) -> TransportRead:
    if vehicle is not None:
        vehicle_read = TransportVehicleRead(
            id=vehicle.id,
            name=vehicle.name or vehicle.plate or "",
            plate=vehicle.plate,
        )
    else:
        vehicle_read = TransportVehicleRead(
            id=None,
            name=transport.vehicle_label or "",
            plate=None,
        )

    return TransportRead(
        id=transport.id,
        transport_date=transport.transport_date,
        place=transport.place,
        product_name=transport.product_name,
        lot_number=transport.lot_number,
        vehicle=vehicle_read,
        departure_time=transport.departure_time,
        departure_temperature_celsius=transport.departure_temperature_celsius,
        arrival_time=transport.arrival_time,
        arrival_temperature_celsius=transport.arrival_temperature_celsius,
        observation=transport.observation,
        is_complete=transport_is_complete(
            departure_time=transport.departure_time,
            departure_temperature_celsius=transport.departure_temperature_celsius,
            arrival_time=transport.arrival_time,
            arrival_temperature_celsius=transport.arrival_temperature_celsius,
        ),
        created_at=transport.created_at,
        updated_at=transport.updated_at,
    )


async def _resolve_vehicle(db: DbSession, vehicle_id: uuid.UUID | None) -> Vehicle | None:
    if vehicle_id is None:
        return None
    return await get_active_vehicle(db, vehicle_id)


def _has_readings(transport: Transport) -> bool:
    return any(getattr(transport, field) is not None for field in TRANSPORT_READING_FIELDS)


def _readings_of(transport: Transport) -> dict[str, Any]:
    return {field: getattr(transport, field) for field in TRANSPORT_READING_FIELDS}


@router.get("", response_model=list[TransportRead], dependencies=[_ANY_ROLE])
async def list_transports(
    db: DbSession,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    lot: Annotated[str | None, Query(max_length=80)] = None,
) -> list[TransportRead]:
    query = _transport_query().where(Transport.deleted_at.is_(None))
    if from_date is not None:
        query = query.where(Transport.transport_date >= from_date)
    if to_date is not None:
        query = query.where(Transport.transport_date <= to_date)
    if lot and lot.strip():
        query = query.where(
            func.lower(Transport.lot_number).contains(lot.strip().lower(), autoescape=True)
        )
    query = query.order_by(
        Transport.transport_date.desc(),
        Transport.created_at.desc(),
    )

    return [_transport_read(transport, vehicle) for transport, vehicle in await db.execute(query)]


@router.post("", response_model=TransportRead, status_code=201)
async def create_transport(
    payload: TransportCreate,
    db: DbSession,
    user: WritingUser,
) -> TransportRead:
    ensure_not_in_the_future(payload.transport_date, code="transport_date_out_of_range")
    vehicle = await _resolve_vehicle(db, payload.vehicle_id)

    transport = Transport(
        transport_date=payload.transport_date,
        place=payload.place,
        product_name=payload.product_name,
        lot_number=payload.lot_number,
        vehicle_id=vehicle.id if vehicle is not None else None,
        vehicle_label=payload.vehicle_label,
        departure_time=payload.departure_time,
        departure_temperature_celsius=(
            as_celsius(payload.departure_temperature_celsius)
            if payload.departure_temperature_celsius is not None
            else None
        ),
        arrival_time=payload.arrival_time,
        arrival_temperature_celsius=(
            as_celsius(payload.arrival_temperature_celsius)
            if payload.arrival_temperature_celsius is not None
            else None
        ),
        observation=payload.observation,
    )
    db.add(transport)
    await db.flush()

    if _has_readings(transport):
        readings = _readings_of(transport)
        db.add(
            TransportEdit(
                transport_id=transport.id,
                action=TransportEditAction.CREATED,
                previous_departure_time=None,
                new_departure_time=readings["departure_time"],
                previous_departure_temperature_celsius=None,
                new_departure_temperature_celsius=readings["departure_temperature_celsius"],
                previous_arrival_time=None,
                new_arrival_time=readings["arrival_time"],
                previous_arrival_temperature_celsius=None,
                new_arrival_temperature_celsius=readings["arrival_temperature_celsius"],
                previous_observation=None,
                new_observation=readings["observation"],
                changed_by=user.id,
            )
        )

    await db.commit()
    await db.refresh(transport)
    return _transport_read(transport, vehicle)


@router.get("/{transport_id}", response_model=TransportRead, dependencies=[_ANY_ROLE])
async def get_transport(transport_id: uuid.UUID, db: DbSession) -> TransportRead:
    transport = await get_active_transport(db, transport_id)
    vehicle = await load_vehicle(db, transport.vehicle_id)
    return _transport_read(transport, vehicle)


@router.put("/{transport_id}", response_model=TransportRead, dependencies=[_ANY_ROLE])
async def update_transport(
    transport_id: uuid.UUID,
    payload: TransportHeaderWrite,
    db: DbSession,
) -> TransportRead:
    transport = await get_active_transport(db, transport_id, for_update=True)
    ensure_not_in_the_future(payload.transport_date, code="transport_date_out_of_range")
    vehicle = await _resolve_vehicle(db, payload.vehicle_id)

    transport.transport_date = payload.transport_date
    transport.place = payload.place
    transport.product_name = payload.product_name
    transport.lot_number = payload.lot_number
    transport.vehicle_id = vehicle.id if vehicle is not None else None
    transport.vehicle_label = payload.vehicle_label
    await db.commit()
    await db.refresh(transport)
    return _transport_read(transport, vehicle)


@router.put("/{transport_id}/readings", response_model=TransportRead)
async def update_transport_readings(
    transport_id: uuid.UUID,
    payload: TransportReadingsWrite,
    db: DbSession,
    user: WritingUser,
) -> TransportRead:
    transport = await get_active_transport(db, transport_id, for_update=True)
    vehicle = await load_vehicle(db, transport.vehicle_id)

    previous = _readings_of(transport)
    had_readings = any(value is not None for value in previous.values())

    for field in TRANSPORT_READING_FIELDS:
        if field not in payload.model_fields_set:
            continue
        value = getattr(payload, field)
        if field.endswith("_temperature_celsius") and value is not None:
            value = as_celsius(value)
        setattr(transport, field, value)

    current = _readings_of(transport)
    if not any(previous[field] != current[field] for field in TRANSPORT_READING_FIELDS):
        return _transport_read(transport, vehicle)

    db.add(
        TransportEdit(
            transport_id=transport.id,
            action=(TransportEditAction.UPDATED if had_readings else TransportEditAction.CREATED),
            previous_departure_time=previous["departure_time"],
            new_departure_time=current["departure_time"],
            previous_departure_temperature_celsius=previous["departure_temperature_celsius"],
            new_departure_temperature_celsius=current["departure_temperature_celsius"],
            previous_arrival_time=previous["arrival_time"],
            new_arrival_time=current["arrival_time"],
            previous_arrival_temperature_celsius=previous["arrival_temperature_celsius"],
            new_arrival_temperature_celsius=current["arrival_temperature_celsius"],
            previous_observation=previous["observation"],
            new_observation=current["observation"],
            changed_by=user.id,
        )
    )
    await db.commit()
    await db.refresh(transport)
    return _transport_read(transport, vehicle)


@router.delete("/{transport_id}", status_code=204, dependencies=[_ADMIN_ONLY])
async def delete_transport(transport_id: uuid.UUID, db: DbSession) -> None:
    transport = await get_active_transport(db, transport_id, for_update=True)
    transport.deleted_at = datetime.now(UTC)
    await db.commit()
