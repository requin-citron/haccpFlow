from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class VehicleWrite(BaseModel):
    """Payload accepted by POST and PUT /api/v1/vehicles."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=120)
    plate: str | None = Field(default=None, max_length=32)

    @field_validator("name", "plate")
    @classmethod
    def _clean_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def _require_identification(self) -> VehicleWrite:
        if self.name is None and self.plate is None:
            raise ValueError("provide at least a name or a plate number")
        return self


class VehicleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str | None
    plate: str | None
    created_at: datetime
    updated_at: datetime
