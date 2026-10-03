from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.cleaning_plan import (
    CleaningFrequency,
    CleaningRecordEditAction,
    CleaningStatus,
)


class CleaningPlanWrite(BaseModel):
    """Payload accepted by POST and PUT /api/v1/cleaning-plans."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    frequency: CleaningFrequency
    products: str | None = Field(default=None, max_length=1000)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned

    @field_validator("products")
    @classmethod
    def _clean_products(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class CleaningPlanRead(BaseModel):
    id: uuid.UUID
    name: str
    frequency: CleaningFrequency
    products: str | None
    last_cleaning_date: date | None
    next_due_date: date | None
    created_at: datetime
    updated_at: datetime


class CleaningRecordWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cleaning_date: date
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("comment")
    @classmethod
    def _clean_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class CleaningRecordUpdate(BaseModel):
    """Partial edit of a declared cleaning: only the provided fields change."""

    model_config = ConfigDict(extra="forbid")

    cleaning_date: date | None = None
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("comment")
    @classmethod
    def _clean_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def _require_something_to_change(self) -> CleaningRecordUpdate:
        if not self.model_fields_set:
            raise ValueError("provide cleaning_date or comment")
        if "cleaning_date" in self.model_fields_set and self.cleaning_date is None:
            raise ValueError("cleaning_date cannot be null")
        return self


class CleaningRecordRead(BaseModel):
    id: uuid.UUID
    plan_id: uuid.UUID
    cleaning_date: date
    comment: str | None
    performed_by_email: str | None
    recorded_at: datetime
    updated_at: datetime


class CleaningRecordEditRead(BaseModel):
    action: CleaningRecordEditAction
    previous_cleaning_date: date | None
    new_cleaning_date: date | None
    previous_comment: str | None
    new_comment: str | None
    changed_by_email: str | None
    changed_at: datetime


class CleaningScheduleEntry(BaseModel):
    plan_id: uuid.UUID
    name: str
    frequency: CleaningFrequency
    products: str | None
    last_cleaning_date: date | None
    next_due_date: date
    status: CleaningStatus
    days_late: int
