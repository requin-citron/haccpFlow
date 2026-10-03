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
from app.schemas.equipment import EquipmentCreate, EquipmentRead
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
async def create_equipment(payload: EquipmentCreate, db: DbSession) -> Equipment:
    normalized_name = payload.name.lower()
    existing = await db.scalar(
        select(Equipment.id).where(
            Equipment.deleted_at.is_(None),
            func.lower(Equipment.name) == normalized_name,
        )
    )
    if existing is not None:
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


@router.delete("/{equipment_id}", status_code=204, dependencies=[_ADMIN_ONLY])
async def delete_equipment(equipment_id: uuid.UUID, db: DbSession) -> None:
    equipment = await db.scalar(
        select(Equipment)
        .where(Equipment.id == equipment_id, Equipment.deleted_at.is_(None))
        .with_for_update()
    )
    if equipment is None:
        raise ApiError(404, "equipment_not_found", "Equipment not found")

    equipment.deleted_at = datetime.now(UTC)
    await db.commit()
