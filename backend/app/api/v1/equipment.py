from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession, require_role
from app.config import get_settings
from app.core.errors import ApiError
from app.models.equipment import Equipment
from app.models.user import UserRole
from app.schemas.equipment import EquipmentRead, EquipmentWrite
from app.services.equipment import resolve_thresholds

router = APIRouter(prefix="/equipment", tags=["equipment"])

_ANY_ROLE = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))
_ADMIN_ONLY = Depends(require_role(UserRole.ADMIN))


def _name_conflict_error(name: str) -> ApiError:
    return ApiError(
        409,
        "equipment_name_conflict",
        f"An active equipment named '{name}' already exists",
    )


@router.get("", response_model=list[EquipmentRead], dependencies=[_ANY_ROLE])
async def list_equipment(db: DbSession) -> list[Equipment]:
    result = await db.scalars(
        select(Equipment).where(Equipment.deleted_at.is_(None)).order_by(func.lower(Equipment.name))
    )
    return list(result)


@router.post("", response_model=EquipmentRead, status_code=201, dependencies=[_ANY_ROLE])
async def create_equipment(payload: EquipmentWrite, db: DbSession) -> Equipment:
    if await _name_is_taken(db, payload.name):
        raise _name_conflict_error(payload.name)

    minimum, maximum = resolve_thresholds(payload, get_settings())
    equipment = Equipment(
        name=payload.name,
        type=payload.type,
        min_temperature_celsius=minimum,
        max_temperature_celsius=maximum,
        location=payload.location,
        notes=payload.notes,
    )
    db.add(equipment)
    try:
        await db.commit()
    except IntegrityError as exc:
        # Backstop for two concurrent creations of the same name.
        await db.rollback()
        raise _name_conflict_error(payload.name) from exc

    await db.refresh(equipment)
    return equipment


@router.put("/{equipment_id}", response_model=EquipmentRead, dependencies=[_ANY_ROLE])
async def update_equipment(
    equipment_id: uuid.UUID,
    payload: EquipmentWrite,
    db: DbSession,
) -> Equipment:
    equipment = await _get_active_equipment(db, equipment_id)

    if await _name_is_taken(db, payload.name, exclude_id=equipment_id):
        raise _name_conflict_error(payload.name)

    minimum, maximum = resolve_thresholds(payload, get_settings())
    equipment.name = payload.name
    equipment.type = payload.type
    equipment.min_temperature_celsius = minimum
    equipment.max_temperature_celsius = maximum
    equipment.location = payload.location
    equipment.notes = payload.notes

    try:
        await db.commit()
    except IntegrityError as exc:
        # Backstop for two concurrent updates with diverging names.
        await db.rollback()
        raise _name_conflict_error(payload.name) from exc

    await db.refresh(equipment)
    return equipment


@router.delete("/{equipment_id}", status_code=204, dependencies=[_ADMIN_ONLY])
async def delete_equipment(equipment_id: uuid.UUID, db: DbSession) -> None:
    equipment = await _get_active_equipment(db, equipment_id)
    equipment.deleted_at = datetime.now(UTC)
    await db.commit()


async def _get_active_equipment(db: DbSession, equipment_id: uuid.UUID) -> Equipment:
    equipment = await db.scalar(
        select(Equipment)
        .where(Equipment.id == equipment_id, Equipment.deleted_at.is_(None))
        .with_for_update()
    )
    if equipment is None:
        raise ApiError(404, "equipment_not_found", "Equipment not found")
    return equipment


async def _name_is_taken(
    db: DbSession,
    name: str,
    *,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    query = select(Equipment.id).where(
        Equipment.deleted_at.is_(None),
        func.lower(Equipment.name) == name.lower(),
    )
    if exclude_id is not None:
        query = query.where(Equipment.id != exclude_id)
    return await db.scalar(query) is not None
