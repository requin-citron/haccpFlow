from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

#: A typo guard: no register holds a million of a single denomination.
MAX_DENOMINATION_COUNT = 1_000_000


class CashRegisterCounts(BaseModel):
    """The twelve counters, all optional and zero by default."""

    coins_1_cent: int = Field(default=0, ge=0, le=MAX_DENOMINATION_COUNT)
    coins_2_cent: int = Field(default=0, ge=0, le=MAX_DENOMINATION_COUNT)
    coins_5_cent: int = Field(default=0, ge=0, le=MAX_DENOMINATION_COUNT)
    coins_10_cent: int = Field(default=0, ge=0, le=MAX_DENOMINATION_COUNT)
    coins_20_cent: int = Field(default=0, ge=0, le=MAX_DENOMINATION_COUNT)
    coins_50_cent: int = Field(default=0, ge=0, le=MAX_DENOMINATION_COUNT)
    coins_1_euro: int = Field(default=0, ge=0, le=MAX_DENOMINATION_COUNT)
    coins_2_euro: int = Field(default=0, ge=0, le=MAX_DENOMINATION_COUNT)
    notes_5_euro: int = Field(default=0, ge=0, le=MAX_DENOMINATION_COUNT)
    notes_10_euro: int = Field(default=0, ge=0, le=MAX_DENOMINATION_COUNT)
    notes_20_euro: int = Field(default=0, ge=0, le=MAX_DENOMINATION_COUNT)
    notes_50_euro: int = Field(default=0, ge=0, le=MAX_DENOMINATION_COUNT)


class CashRegisterWrite(CashRegisterCounts):
    """Payload accepted by POST and PUT /api/v1/cash-registers."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned


class CashRegisterRead(CashRegisterCounts):
    id: uuid.UUID
    name: str
    #: Sum of the counters, in cents: exact, the client formats it.
    total_cents: int
    created_at: datetime
    updated_at: datetime
