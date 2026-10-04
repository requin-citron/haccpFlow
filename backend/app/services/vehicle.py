from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models.vehicle import Vehicle


async def get_active_vehicle(
    db: AsyncSession,
    vehicle_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> Vehicle:
    query = select(Vehicle).where(
        Vehicle.id == vehicle_id,
        Vehicle.deleted_at.is_(None),
    )
    if for_update:
        query = query.with_for_update()
    vehicle = await db.scalar(query)
    if vehicle is None:
        raise ApiError(404, "vehicle_not_found", "Vehicle not found")
    return vehicle


async def find_vehicle_conflict(
    db: AsyncSession,
    *,
    name: str | None,
    plate: str | None,
    exclude_id: uuid.UUID | None = None,
) -> str | None:
    """Return "name" or "plate" when an active vehicle already uses it."""

    async def taken(column: object, value: str) -> bool:
        query = select(Vehicle.id).where(
            Vehicle.deleted_at.is_(None),
            func.lower(column) == value.lower(),
        )
        if exclude_id is not None:
            query = query.where(Vehicle.id != exclude_id)
        return await db.scalar(query) is not None

    if name is not None and await taken(Vehicle.name, name):
        return "name"
    if plate is not None and await taken(Vehicle.plate, plate):
        return "plate"
    return None


async def load_vehicle(db: AsyncSession, vehicle_id: uuid.UUID | None) -> Vehicle | None:
    """Load a vehicle for display, including a deactivated one.

    A transport must stay readable and editable after its vehicle is
    deactivated: the reference is historical.
    """

    if vehicle_id is None:
        return None
    return await db.get(Vehicle, vehicle_id)


async def load_vehicles(
    db: AsyncSession,
    vehicle_ids: list[uuid.UUID],
) -> dict[uuid.UUID, Vehicle]:
    if not vehicle_ids:
        return {}
    rows = await db.scalars(select(Vehicle).where(Vehicle.id.in_(vehicle_ids)))
    return {vehicle.id: vehicle for vehicle in rows}
