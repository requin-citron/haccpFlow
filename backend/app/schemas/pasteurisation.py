from __future__ import annotations

import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.pasteurisation import PasteurisationPhase, PasteurisationPhaseEditAction
from app.schemas.equipment import MAX_STORABLE_CELSIUS, MIN_ABSOLUTE_CELSIUS


class PasteurisationBatchWrite(BaseModel):
    """Payload accepted by POST and PUT /api/v1/pasteurisations."""

    model_config = ConfigDict(extra="forbid")

    batch_date: date
    product_name: str = Field(min_length=1, max_length=160)
    lot_number: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=100_000)

    @field_validator("product_name", "lot_number")
    @classmethod
    def _clean_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned


class PasteurisationPhaseWrite(BaseModel):
    """Partial body: an absent field keeps its value, an explicit null clears it."""

    model_config = ConfigDict(extra="forbid")

    started_at: time | None = None
    ended_at: time | None = None
    target_temperature_celsius: float | None = Field(
        default=None,
        ge=MIN_ABSOLUTE_CELSIUS,
        le=MAX_STORABLE_CELSIUS,
    )
    observation: str | None = Field(default=None, max_length=2000)

    @field_validator("observation")
    @classmethod
    def _clean_observation(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def _require_a_field(self) -> PasteurisationPhaseWrite:
        if not self.model_fields_set:
            raise ValueError(
                "provide at least one of started_at, ended_at, "
                "target_temperature_celsius, observation"
            )
        return self


class PasteurisationPhaseRead(BaseModel):
    phase: PasteurisationPhase
    started_at: time | None
    ended_at: time | None
    duration_minutes: int | None
    target_temperature_celsius: float | None
    observation: str | None


class PasteurisationRead(BaseModel):
    id: uuid.UUID
    batch_date: date
    product_name: str
    lot_number: str
    quantity: int
    phases: list[PasteurisationPhaseRead]
    filled_phases: int
    is_complete: bool
    created_at: datetime
    updated_at: datetime


class PasteurisationPhaseEditRead(BaseModel):
    action: PasteurisationPhaseEditAction
    previous_started_at: time | None
    new_started_at: time | None
    previous_ended_at: time | None
    new_ended_at: time | None
    previous_target_temperature_celsius: float | None
    new_target_temperature_celsius: float | None
    previous_observation: str | None
    new_observation: str | None
    changed_by_email: str | None
    changed_at: datetime
