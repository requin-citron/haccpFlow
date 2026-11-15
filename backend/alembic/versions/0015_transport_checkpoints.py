"""rename transport checkpoints to initial and in progress

Revision ID: 0015_transport_checkpoints
Revises: 0014_user_auth_version
Create Date: 2026-11-15

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_transport_checkpoints"
down_revision: str | None = "0014_user_auth_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TRANSPORT_COLUMNS = (
    ("departure_time", "initial_time", sa.Time()),
    (
        "departure_temperature_celsius",
        "initial_temperature_celsius",
        sa.Numeric(precision=5, scale=2),
    ),
    ("arrival_time", "in_progress_time", sa.Time()),
    (
        "arrival_temperature_celsius",
        "in_progress_temperature_celsius",
        sa.Numeric(precision=5, scale=2),
    ),
)

EDIT_COLUMNS = (
    ("previous_departure_time", "previous_initial_time", sa.Time()),
    ("new_departure_time", "new_initial_time", sa.Time()),
    (
        "previous_departure_temperature_celsius",
        "previous_initial_temperature_celsius",
        sa.Numeric(precision=5, scale=2),
    ),
    (
        "new_departure_temperature_celsius",
        "new_initial_temperature_celsius",
        sa.Numeric(precision=5, scale=2),
    ),
    ("previous_arrival_time", "previous_in_progress_time", sa.Time()),
    ("new_arrival_time", "new_in_progress_time", sa.Time()),
    (
        "previous_arrival_temperature_celsius",
        "previous_in_progress_temperature_celsius",
        sa.Numeric(precision=5, scale=2),
    ),
    (
        "new_arrival_temperature_celsius",
        "new_in_progress_temperature_celsius",
        sa.Numeric(precision=5, scale=2),
    ),
)


def _rename_columns(
    table_name: str,
    columns: Sequence[tuple[str, str, sa.TypeEngine[object]]],
    *,
    forward: bool,
) -> None:
    for old_name, new_name, column_type in columns:
        source, target = (old_name, new_name) if forward else (new_name, old_name)
        op.alter_column(
            table_name,
            source,
            new_column_name=target,
            existing_type=column_type,
            existing_nullable=True,
        )


def upgrade() -> None:
    _rename_columns("transports", TRANSPORT_COLUMNS, forward=True)
    _rename_columns("transport_edits", EDIT_COLUMNS, forward=True)


def downgrade() -> None:
    _rename_columns("transport_edits", EDIT_COLUMNS, forward=False)
    _rename_columns("transports", TRANSPORT_COLUMNS, forward=False)
