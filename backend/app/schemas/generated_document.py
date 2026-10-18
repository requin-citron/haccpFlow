from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.template_variable import ProductRow


class GenerateTemplateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #: Local variable values, keyed by their Jinja name. All values are sent
    #: as strings and converted according to the variable type.
    values: dict[str, str | list[ProductRow]] = Field(default_factory=dict)


class GeneratedDocumentRead(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID | None
    template_name: str
    generated_by_email: str | None
    values: dict[str, object]
    filename: str
    size_bytes: int
    sha256: str
    created_at: datetime
