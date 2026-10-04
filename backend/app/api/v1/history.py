from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, require_role
from app.models.user import UserRole
from app.schemas.history import HistoryEntity, HistoryEntryRead
from app.services.history import DEFAULT_LIMIT, collect_history

router = APIRouter(prefix="/history", tags=["history"])

# The audit feed is open to administrators only.
_ADMIN_ONLY = Depends(require_role(UserRole.ADMIN))


@router.get("", response_model=list[HistoryEntryRead], dependencies=[_ADMIN_ONLY])
async def list_history(
    db: DbSession,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    entity: Annotated[HistoryEntity | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = DEFAULT_LIMIT,
) -> list[HistoryEntryRead]:
    return await collect_history(
        db,
        from_date=from_date,
        to_date=to_date,
        entity=entity,
        limit=limit,
    )
