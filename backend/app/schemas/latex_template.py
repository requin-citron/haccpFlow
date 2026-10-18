from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LatexTemplateRead(BaseModel):
    """Metadata of an uploaded template. The source is served separately."""

    id: uuid.UUID
    name: str
    original_filename: str
    size_bytes: int
    sha256: str
    uploaded_by_email: str | None
    created_at: datetime
    updated_at: datetime


class LatexTemplateRename(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
