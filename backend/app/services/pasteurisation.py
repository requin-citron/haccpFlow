from __future__ import annotations

import uuid
from datetime import time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models.pasteurisation import (
    PasteurisationBatch,
    PasteurisationPhase,
    PasteurisationPhaseRecord,
)

#: Canonical order of the phases, and the single place to extend for a new one.
PHASE_ORDER: tuple[PasteurisationPhase, ...] = tuple(PasteurisationPhase)


def compute_duration_minutes(started_at: time | None, ended_at: time | None) -> int | None:
    """Duration of a phase, derived from its two times.

    Returns None when one of the times is missing or when the range does not
    move forward (a phase cannot cross midnight).
    """

    if started_at is None or ended_at is None:
        return None
    start_seconds = started_at.hour * 3600 + started_at.minute * 60 + started_at.second
    end_seconds = ended_at.hour * 3600 + ended_at.minute * 60 + ended_at.second
    elapsed = end_seconds - start_seconds
    return elapsed // 60 if elapsed > 0 else None


def phase_is_filled(
    *,
    started_at: time | None,
    ended_at: time | None,
    target_temperature_celsius: Decimal | None,
    observation: str | None,
) -> bool:
    return any(
        value is not None
        for value in (started_at, ended_at, target_temperature_celsius, observation)
    )


def phase_is_complete(
    *,
    started_at: time | None,
    ended_at: time | None,
    target_temperature_celsius: Decimal | None,
) -> bool:
    return (
        started_at is not None and ended_at is not None and target_temperature_celsius is not None
    )


async def get_active_pasteurisation(
    db: AsyncSession,
    batch_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> PasteurisationBatch:
    query = select(PasteurisationBatch).where(
        PasteurisationBatch.id == batch_id,
        PasteurisationBatch.deleted_at.is_(None),
    )
    if for_update:
        query = query.with_for_update()
    batch = await db.scalar(query)
    if batch is None:
        raise ApiError(404, "pasteurisation_not_found", "Pasteurisation batch not found")
    return batch


async def load_phase_records(
    db: AsyncSession,
    batch_ids: list[uuid.UUID],
) -> dict[uuid.UUID, dict[PasteurisationPhase, PasteurisationPhaseRecord]]:
    """Phases of the given batches, grouped by batch then by phase."""

    if not batch_ids:
        return {}
    rows = await db.scalars(
        select(PasteurisationPhaseRecord).where(PasteurisationPhaseRecord.batch_id.in_(batch_ids))
    )
    grouped: dict[uuid.UUID, dict[PasteurisationPhase, PasteurisationPhaseRecord]] = {}
    for row in rows:
        grouped.setdefault(row.batch_id, {})[row.phase] = row
    return grouped
