from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import DbSession, require_role
from app.core.errors import ApiError
from app.models.user import UserRole
from app.schemas.export import ExportDataset
from app.services.export import FILENAME_PREFIXES, build_export

router = APIRouter(prefix="/exports", tags=["exports"])

_ANY_ROLE = Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))


def _filename(dataset: ExportDataset, from_date: date | None, to_date: date | None) -> str:
    prefix = FILENAME_PREFIXES[dataset]
    if from_date is None and to_date is None:
        return f"{prefix}-complet-{datetime.now(UTC).date().isoformat()}.csv"
    start = from_date.isoformat() if from_date is not None else "debut"
    end = to_date.isoformat() if to_date is not None else "fin"
    return f"{prefix}-{start}-{end}.csv"


@router.get("/{dataset}", dependencies=[_ANY_ROLE])
async def export_dataset(
    dataset: ExportDataset,
    db: DbSession,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
) -> Response:
    if from_date is not None and to_date is not None and from_date > to_date:
        raise ApiError(422, "export_range_invalid", "'from' must not be after 'to'")

    content = await build_export(db, dataset, from_date=from_date, to_date=to_date)
    filename = _filename(dataset, from_date, to_date)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
