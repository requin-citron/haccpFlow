from __future__ import annotations

import enum
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DashboardWidgetKey(enum.StrEnum):
    """Widgets supported by the configurable dashboard."""

    REVENUE = "revenue"
    MISSING_READINGS = "missing_readings"


class DashboardWidgetConfig(BaseModel):
    """One widget placement on the twelve-column dashboard grid."""

    model_config = ConfigDict(extra="forbid")

    key: DashboardWidgetKey
    column_start: int = Field(ge=1, le=12)
    row_start: int = Field(default=1, ge=1, le=1_000)
    width_columns: int = Field(ge=3, le=12)
    row_span: int = Field(default=6, ge=5, le=12)

    @model_validator(mode="after")
    def _validate_grid_bounds(self) -> DashboardWidgetConfig:
        if self.column_start + self.width_columns - 1 > 12:
            raise ValueError("widget must fit inside the twelve-column grid")
        return self


class DashboardLayoutRead(BaseModel):
    """A persisted dashboard layout returned to the client."""

    model_config = ConfigDict(extra="forbid")

    widgets: list[DashboardWidgetConfig] = Field(max_length=20)

    @model_validator(mode="after")
    def _validate_unique_widgets(self) -> DashboardLayoutRead:
        keys = [widget.key for widget in self.widgets]
        if len(keys) != len(set(keys)):
            raise ValueError("widget keys must be unique")
        return self


class DashboardLayoutWrite(DashboardLayoutRead):
    """Full replacement of one user's dashboard layout."""

    @model_validator(mode="after")
    def _validate_no_overlap(self) -> DashboardLayoutWrite:
        for index, widget in enumerate(self.widgets):
            for other in self.widgets[index + 1 :]:
                overlaps = (
                    widget.column_start < other.column_start + other.width_columns
                    and widget.column_start + widget.width_columns > other.column_start
                    and widget.row_start < other.row_start + other.row_span
                    and widget.row_start + widget.row_span > other.row_start
                )
                if overlaps:
                    raise ValueError("dashboard widgets must not overlap")
        return self


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


class DashboardMissingReadingsRead(BaseModel):
    """Reading completion totals for one inclusive UTC date range."""

    model_config = ConfigDict(populate_by_name=True)

    from_date: date = Field(alias="from", serialization_alias="from")
    to_date: date = Field(alias="to", serialization_alias="to")
    missing_slots: int
    filled_slots: int
    total_slots: int
    equipment_count: int
