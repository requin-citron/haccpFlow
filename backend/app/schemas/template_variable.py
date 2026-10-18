from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.template_variable import TemplateVariableKind, TemplateVariableValueType


class ProductRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    designation: str = Field(min_length=1, max_length=200)
    pots: int = Field(ge=0, le=1_000_000)
    #: Decimal string, validated and normalized by the service.
    prix: str = Field(min_length=1, max_length=64)


class TemplateVariableWrite(BaseModel):
    """Payload accepted by the variable create and update endpoints.

    Business validation (identifier, kind rules, typed value) lives in the
    template variables service so the error codes stay stable.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    kind: TemplateVariableKind
    value_type: TemplateVariableValueType
    value: str | list[ProductRow] | None = None


class TemplateVariableRead(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    name: str
    label: str
    description: str | None
    kind: TemplateVariableKind
    value_type: TemplateVariableValueType
    value: str | list[ProductRow] | None
    used_in_template: bool
    created_at: datetime
    updated_at: datetime
