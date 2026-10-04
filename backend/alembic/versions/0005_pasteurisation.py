"""pasteurisation batches, their phases and the phase audit trail

Revision ID: 0005_pasteurisation
Revises: 0004_cleaning_plans
Create Date: 2026-10-04

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_pasteurisation"
down_revision: str | None = "0004_cleaning_plans"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pasteurisation_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_date", sa.Date(), nullable=False),
        sa.Column("product_name", sa.String(length=160), nullable=False),
        sa.Column("lot_number", sa.String(length=80), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pasteurisation_batches_lot_number"),
        "pasteurisation_batches",
        ["lot_number"],
        unique=False,
    )

    op.create_table(
        "pasteurisation_phases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column(
            "phase",
            sa.Enum("preheating", "holding", "cooling", name="pasteurisation_phase"),
            nullable=False,
        ),
        sa.Column("started_at", sa.Time(), nullable=True),
        sa.Column("ended_at", sa.Time(), nullable=True),
        sa.Column("target_temperature_celsius", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("observation", sa.String(length=2000), nullable=True),
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
        sa.ForeignKeyConstraint(["batch_id"], ["pasteurisation_batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id", "phase", name="uq_pasteurisation_phases_slot"),
    )
    op.create_index(
        op.f("ix_pasteurisation_phases_batch_id"),
        "pasteurisation_phases",
        ["batch_id"],
        unique=False,
    )

    op.create_table(
        "pasteurisation_phase_edits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("phase_id", sa.Uuid(), nullable=False),
        sa.Column(
            "action",
            sa.Enum("created", "updated", name="pasteurisation_phase_edit_action"),
            nullable=False,
        ),
        sa.Column("previous_started_at", sa.Time(), nullable=True),
        sa.Column("new_started_at", sa.Time(), nullable=True),
        sa.Column("previous_ended_at", sa.Time(), nullable=True),
        sa.Column("new_ended_at", sa.Time(), nullable=True),
        sa.Column(
            "previous_target_temperature_celsius", sa.Numeric(precision=5, scale=2), nullable=True
        ),
        sa.Column(
            "new_target_temperature_celsius", sa.Numeric(precision=5, scale=2), nullable=True
        ),
        sa.Column("previous_observation", sa.String(length=2000), nullable=True),
        sa.Column("new_observation", sa.String(length=2000), nullable=True),
        sa.Column("changed_by", sa.Uuid(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["phase_id"], ["pasteurisation_phases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pasteurisation_phase_edits_phase_id"),
        "pasteurisation_phase_edits",
        ["phase_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_pasteurisation_phase_edits_phase_id"),
        table_name="pasteurisation_phase_edits",
    )
    op.drop_table("pasteurisation_phase_edits")
    op.drop_index(
        op.f("ix_pasteurisation_phases_batch_id"),
        table_name="pasteurisation_phases",
    )
    op.drop_table("pasteurisation_phases")
    op.drop_index(
        op.f("ix_pasteurisation_batches_lot_number"),
        table_name="pasteurisation_batches",
    )
    op.drop_table("pasteurisation_batches")
    op.execute("DROP TYPE IF EXISTS pasteurisation_phase_edit_action")
    op.execute("DROP TYPE IF EXISTS pasteurisation_phase")
