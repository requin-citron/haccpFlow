from __future__ import annotations

import enum
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DashboardWidgetKey(enum.StrEnum):
    """Widgets supported by the configurable dashboard."""

    REVENUE = "revenue"


class DashboardWidgetConfig(BaseModel):
    """One widget placement on the twelve-column dashboard grid."""

    model_config = ConfigDict(extra="forbid")

    key: DashboardWidgetKey
    column_start: int = Field(ge=1, le=12)
    width_columns: int = Field(ge=3, le=12)
    row_span: int = Field(default=6, ge=5, le=12)

    @model_validator(mode="after")
    def _validate_grid_bounds(self) -> DashboardWidgetConfig:
        if self.column_start + self.width_columns - 1 > 12:
            raise ValueError("widget must fit inside the twelve-column grid")
        return self


class DashboardLayoutWrite(BaseModel):
    """Full replacement of one user's dashboard layout."""

    model_config = ConfigDict(extra="forbid")

    widgets: list[DashboardWidgetConfig] = Field(max_length=20)

    @model_validator(mode="after")
    def _validate_unique_widgets(self) -> DashboardLayoutWrite:
        keys = [widget.key for widget in self.widgets]
        if len(keys) != len(set(keys)):
            raise ValueError("widget keys must be unique")
        return self


class DashboardLayoutRead(DashboardLayoutWrite):
    pass


class DashboardRevenueRead(BaseModel):
    """Revenue totals for one inclusive UTC date range."""

    model_config = ConfigDict(populate_by_name=True)

    from_date: date = Field(alias="from", serialization_alias="from")
    to_date: date = Field(alias="to", serialization_alias="to")
    total_cents: int
    cash_cents: int
    cheque_cents: int
    card_cents: int
    #: Cash expenses added back to reconstruct revenue from cash movements.
    cash_expenses_cents: int
    closed_session_count: int
