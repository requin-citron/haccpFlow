from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.cash_register import DENOMINATION_FIELDS
from app.models.cash_session import CashExpenseKind
from app.schemas.cash_register import CashRegisterCounts

#: Typo guards on a single expense line.
MAX_QUANTITY = 100_000
MAX_UNIT_PRICE_CENTS = 100_000_000


class CashSessionFilter(enum.StrEnum):
    """Which sessions a listing should return."""

    ALL = "all"
    OPEN = "open"
    CLOSED = "closed"


class CashSessionOpen(BaseModel):
    """Payload accepted by POST /api/v1/cash-sessions."""

    model_config = ConfigDict(extra="forbid")

    cash_register_id: uuid.UUID
    #: Defaults to today: the day the till is being tracked for.
    session_date: date | None = None
    #: When omitted, the register's current count is copied as the float.
    opening_counts: CashRegisterCounts | None = None


class CashSessionWrite(BaseModel):
    """Payload accepted by PUT /api/v1/cash-sessions/{id} while it is open."""

    model_config = ConfigDict(extra="forbid")

    session_date: date
    opening_counts: CashRegisterCounts


class CashSessionClose(BaseModel):
    """Payload accepted by POST /api/v1/cash-sessions/{id}/close."""

    model_config = ConfigDict(extra="forbid")

    closing_counts: CashRegisterCounts

    @model_validator(mode="after")
    def _require_every_denomination(self) -> CashSessionClose:
        # The register is being recounted: every denomination must be given,
        # so a forgotten one can never silently empty the drawer.
        missing = [
            field
            for field in DENOMINATION_FIELDS
            if field not in self.closing_counts.model_fields_set
        ]
        if missing:
            raise ValueError(
                "closing_counts must provide all twelve denominations: " + ", ".join(missing)
            )
        return self


class CashExpenseWrite(BaseModel):
    """Payload accepted by POST and PUT on a session's expenses."""

    model_config = ConfigDict(extra="forbid")

    kind: CashExpenseKind
    name: str = Field(min_length=1, max_length=160)
    quantity: int = Field(default=1, ge=1, le=MAX_QUANTITY)
    #: Unit price as actually paid, VAT included.
    unit_price_cents: int = Field(ge=0, le=MAX_UNIT_PRICE_CENTS)
    #: VAT rate as a percentage, kept for the record only.
    vat_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, decimal_places=2)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned


class CashExpenseRead(BaseModel):
    id: uuid.UUID
    kind: CashExpenseKind
    name: str
    quantity: int
    unit_price_cents: int
    vat_rate: Decimal
    #: quantity x unit price, computed on read: never stored.
    total_cents: int
    created_at: datetime
    updated_at: datetime


class CashSessionRead(BaseModel):
    id: uuid.UUID
    cash_register_id: uuid.UUID
    cash_register_name: str
    session_date: date
    opening_counts: CashRegisterCounts
    #: Null while the session is open.
    closing_counts: CashRegisterCounts | None
    opening_total_cents: int
    closing_total_cents: int | None
    expenses_total_cents: int
    expenses_professional_total_cents: int
    expenses_personal_total_cents: int
    expenses: list[CashExpenseRead]
    is_open: bool
    opened_by_email: str | None
    closed_by_email: str | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
