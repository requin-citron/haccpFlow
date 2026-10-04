from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pydantic import BaseModel


class HistoryEntity(enum.StrEnum):
    """Sources contributing to the unified history feed."""

    TEMPERATURE_READING = "temperature_reading"
    CLEANING_RECORD = "cleaning_record"
    PASTEURISATION_PHASE = "pasteurisation_phase"


class HistoryAction(enum.StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"


class HistoryChangeRead(BaseModel):
    field: str
    label: str
    previous: str | None
    new: str | None


class HistoryEntryRead(BaseModel):
    id: uuid.UUID
    occurred_at: datetime
    entity: HistoryEntity
    action: HistoryAction
    actor_email: str | None
    #: Id of the parent entity, used by the client to link back.
    target_id: uuid.UUID
    subject: str
    detail: str
    changes: list[HistoryChangeRead]
