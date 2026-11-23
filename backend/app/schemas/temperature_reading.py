from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.temperature_reading import ReadingEditAction, ReadingSlot, ReadingSource
from app.schemas.equipment import MAX_STORABLE_CELSIUS, MIN_ABSOLUTE_CELSIUS


class TemperatureReadingWrite(BaseModel):
    """Payload accepted by PUT .../readings/{date}.

    A slot that is absent or null keeps its current value, which is how a day
    gets completed in two passes (morning first, then evening).
    """

    model_config = ConfigDict(extra="forbid")

    morning_celsius: float | None = Field(
        default=None,
        ge=MIN_ABSOLUTE_CELSIUS,
        le=MAX_STORABLE_CELSIUS,
    )
    evening_celsius: float | None = Field(
        default=None,
        ge=MIN_ABSOLUTE_CELSIUS,
        le=MAX_STORABLE_CELSIUS,
    )
    morning_justification: str | None = Field(default=None, max_length=2000)
    evening_justification: str | None = Field(default=None, max_length=2000)

    @field_validator("morning_justification", "evening_justification")
    @classmethod
    def normalize_justification(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class TemperatureReadingSlotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    temperature_celsius: float
    is_compliant: bool
    source: ReadingSource
    recorded_at: datetime
    updated_at: datetime


class TemperatureReadingCorrectionRead(BaseModel):
    previous_celsius: float
    new_celsius: float
    is_compliant: bool
    justification: str
    changed_by_email: str | None
    changed_at: datetime


class TemperatureReadingDayRead(BaseModel):
    reading_date: date
    #: Effective values, kept for compatibility with existing clients.
    morning: TemperatureReadingSlotRead | None
    evening: TemperatureReadingSlotRead | None
    morning_original: TemperatureReadingSlotRead | None
    evening_original: TemperatureReadingSlotRead | None
    morning_modified: TemperatureReadingCorrectionRead | None
    evening_modified: TemperatureReadingCorrectionRead | None


class TemperatureReadingEditRead(BaseModel):
    slot: ReadingSlot
    action: ReadingEditAction
    previous_celsius: float | None
    new_celsius: float
    justification: str | None
    changed_by_email: str | None
    changed_at: datetime
