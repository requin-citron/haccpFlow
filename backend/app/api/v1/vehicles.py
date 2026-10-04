from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession, require_role
from app.core.errors import ApiError
from app.models.user import UserRole
from app.models.vehicle import Vehicle
from app.schemas.vehicle import VehicleRead, VehicleWrite
from app.services.vehicle import find_vehicle_conflict, get_active_vehicle

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

_ANY_ROLE = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))
_ADMIN_ONLY = Depends(require_role(UserRole.ADMIN))


def _conflict_error(field: str, payload: VehicleWrite) -> ApiError:
    value = payload.plate if field == "plate" else payload.name
    label = "plate number" if field == "plate" else "name"
    return ApiError(
        409,
        "vehicle_conflict",
        f"An active vehicle already uses this {label}: '{value}'",
    )


@router.get("", response_model=list[VehicleRead], dependencies=[_ANY_ROLE])
async def list_vehicles(db: DbSession) -> list[Vehicle]:
    return list(
        await db.scalars(
            select(Vehicle)
            .where(Vehicle.deleted_at.is_(None))
            .order_by(
                func.lower(Vehicle.name).nulls_last(),
                func.lower(Vehicle.plate).nulls_last(),
            )
        )
    )


@router.post("", response_model=VehicleRead, status_code=201, dependencies=[_ANY_ROLE])
async def create_vehicle(payload: VehicleWrite, db: DbSession) -> Vehicle:
    conflict = await find_vehicle_conflict(db, name=payload.name, plate=payload.plate)
    if conflict is not None:
        raise _conflict_error(conflict, payload)

    vehicle = Vehicle(name=payload.name, plate=payload.plate)
    db.add(vehicle)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict_error("name", payload) from exc

    await db.refresh(vehicle)
    return vehicle


@router.put("/{vehicle_id}", response_model=VehicleRead, dependencies=[_ANY_ROLE])
async def update_vehicle(
    vehicle_id: uuid.UUID,
    payload: VehicleWrite,
    db: DbSession,
) -> Vehicle:
    vehicle = await get_active_vehicle(db, vehicle_id, for_update=True)

    conflict = await find_vehicle_conflict(
        db,
        name=payload.name,
        plate=payload.plate,
        exclude_id=vehicle_id,
    )
    if conflict is not None:
        raise _conflict_error(conflict, payload)

    vehicle.name = payload.name
    vehicle.plate = payload.plate
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict_error("plate", payload) from exc

    await db.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}", status_code=204, dependencies=[_ADMIN_ONLY])
async def delete_vehicle(vehicle_id: uuid.UUID, db: DbSession) -> None:
    vehicle = await get_active_vehicle(db, vehicle_id, for_update=True)
    vehicle.deleted_at = datetime.now(UTC)
    await db.commit()
