from __future__ import annotations

import enum


class ExportDataset(enum.StrEnum):
    """The data sets available as CSV extracts."""

    READINGS = "readings"
    CLEANINGS = "cleanings"
    PASTEURISATIONS = "pasteurisations"
    TRANSPORTS = "transports"
