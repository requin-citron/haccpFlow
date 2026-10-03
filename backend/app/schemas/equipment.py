from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.equipment import EquipmentType

MIN_ABSOLUTE_CELSIUS = -273.15
MAX_STORABLE_CELSIUS = 999.99


class EquipmentCreate(BaseModel):
    """Payload accepted by POST /api/v1/equipment."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    type: EquipmentType
    min_temperature_celsius: float | None = Field(
        default=None,
        ge=MIN_ABSOLUTE_CELSIUS,
        le=MAX_STORABLE_CELSIUS,
    )
    max_temperature_celsius: float | None = Field(
        default=None,
        ge=MIN_ABSOLUTE_CELSIUS,
        le=MAX_STORABLE_CELSIUS,
    )
    location: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned

    @field_validator("location", "notes")
    @classmethod
    def _clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def _check_thresholds(self) -> EquipmentCreate:
        minimum = self.min_temperature_celsius
        maximum = self.max_temperature_celsius
        if (minimum is None) != (maximum is None):
            raise ValueError("min and max temperatures must be provided together")
        if minimum is not None and maximum is not None and minimum >= maximum:
            raise ValueError("min temperature must be lower than max temperature")
        return self


class EquipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: EquipmentType
    min_temperature_celsius: float
    max_temperature_celsius: float
    location: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
