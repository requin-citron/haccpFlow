"""temperature readings and their audit trail

Revision ID: 0003_temperature_readings
Revises: 0002_equipment
Create Date: 2026-10-04

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_temperature_readings"
down_revision: str | None = "0002_equipment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "temperature_readings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("equipment_id", sa.Uuid(), nullable=False),
        sa.Column("reading_date", sa.Date(), nullable=False),
        sa.Column("slot", sa.Enum("morning", "evening", name="reading_slot"), nullable=False),
        sa.Column("temperature_celsius", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("is_compliant", sa.Boolean(), nullable=False),
        sa.Column("source", sa.Enum("manual", "sensor", name="reading_source"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "equipment_id",
            "reading_date",
            "slot",
            name="uq_temperature_readings_slot",
        ),
    )
    op.create_index(
        op.f("ix_temperature_readings_equipment_id"),
        "temperature_readings",
        ["equipment_id"],
        unique=False,
    )

    op.create_table(
        "temperature_reading_edits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reading_id", sa.Uuid(), nullable=False),
        sa.Column(
            "action",
            sa.Enum("created", "updated", name="reading_edit_action"),
            nullable=False,
        ),
        sa.Column("previous_celsius", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("new_celsius", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("changed_by", sa.Uuid(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["reading_id"], ["temperature_readings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_temperature_reading_edits_reading_id"),
        "temperature_reading_edits",
        ["reading_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_temperature_reading_edits_reading_id"),
        table_name="temperature_reading_edits",
    )
    op.drop_table("temperature_reading_edits")
    op.drop_index(
        op.f("ix_temperature_readings_equipment_id"),
        table_name="temperature_readings",
    )
    op.drop_table("temperature_readings")
    op.execute("DROP TYPE IF EXISTS reading_edit_action")
    op.execute("DROP TYPE IF EXISTS reading_source")
    op.execute("DROP TYPE IF EXISTS reading_slot")
