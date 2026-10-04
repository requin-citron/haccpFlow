from __future__ import annotations

import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.equipment import MAX_STORABLE_CELSIUS, MIN_ABSOLUTE_CELSIUS


class TransportReadingsFields(BaseModel):
    """The five cold-chain fields, shared by creation and later edits."""

    departure_time: time | None = None
    departure_temperature_celsius: float | None = Field(
        default=None,
        ge=MIN_ABSOLUTE_CELSIUS,
        le=MAX_STORABLE_CELSIUS,
    )
    arrival_time: time | None = None
    arrival_temperature_celsius: float | None = Field(
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


class TransportReadingsWrite(TransportReadingsFields):
    """Partial body: an absent field keeps its value, an explicit null clears it."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _require_a_field(self) -> TransportReadingsWrite:
        if not self.model_fields_set:
            raise ValueError("provide at least one reading field")
        return self


class TransportHeaderFields(BaseModel):
    transport_date: date
    place: str = Field(min_length=1, max_length=160)
    product_name: str = Field(min_length=1, max_length=160)
    lot_number: str | None = Field(default=None, max_length=80)
    #: Either a vehicle from the registry, or a free label for a one-off carrier.
    vehicle_id: uuid.UUID | None = None
    vehicle_label: str | None = Field(default=None, max_length=120)

    @field_validator("place", "product_name")
    @classmethod
    def _clean_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned

    @field_validator("lot_number", "vehicle_label")
    @classmethod
    def _clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def _require_exactly_one_vehicle(self) -> TransportHeaderFields:
        if (self.vehicle_id is None) == (self.vehicle_label is None):
            raise ValueError("provide either vehicle_id or vehicle_label, not both")
        return self


class TransportCreate(TransportHeaderFields, TransportReadingsFields):
    """Payload accepted by POST: the header plus, optionally, the departure."""

    model_config = ConfigDict(extra="forbid")


class TransportHeaderWrite(TransportHeaderFields):
    """Payload accepted by PUT: the header only, readings are edited apart."""

    model_config = ConfigDict(extra="forbid")


class TransportVehicleRead(BaseModel):
    #: Null when the transport used a free label (a one-off carrier).
    id: uuid.UUID | None
    name: str
    plate: str | None


class TransportRead(BaseModel):
    id: uuid.UUID
    transport_date: date
    place: str
    product_name: str
    lot_number: str | None
    vehicle: TransportVehicleRead
    departure_time: time | None
    departure_temperature_celsius: float | None
    arrival_time: time | None
    arrival_temperature_celsius: float | None
    observation: str | None
    #: True once both checkpoints carry a time and a temperature.
    is_complete: bool
    created_at: datetime
    updated_at: datetime
