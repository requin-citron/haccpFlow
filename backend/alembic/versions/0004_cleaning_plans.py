"""cleaning plans, declared cleanings and their audit trail

Revision ID: 0004_cleaning_plans
Revises: 0003_temperature_readings
Create Date: 2026-10-04

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_cleaning_plans"
down_revision: str | None = "0003_temperature_readings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cleaning_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "frequency",
            sa.Enum("after_each_use", "daily", "weekly", name="cleaning_frequency"),
            nullable=False,
        ),
        sa.Column("products", sa.String(length=1000), nullable=True),
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
        "uq_cleaning_plans_name_active",
        "cleaning_plans",
        [sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "cleaning_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("cleaning_date", sa.Date(), nullable=False),
        sa.Column("comment", sa.String(length=2000), nullable=True),
        sa.Column("performed_by", sa.Uuid(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(["plan_id"], ["cleaning_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["performed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cleaning_records_plan_id"),
        "cleaning_records",
        ["plan_id"],
        unique=False,
    )

    op.create_table(
        "cleaning_record_edits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("record_id", sa.Uuid(), nullable=False),
        sa.Column(
            "action",
            sa.Enum("created", "updated", "deleted", name="cleaning_record_edit_action"),
            nullable=False,
        ),
        sa.Column("previous_cleaning_date", sa.Date(), nullable=True),
        sa.Column("new_cleaning_date", sa.Date(), nullable=True),
        sa.Column("previous_comment", sa.String(length=2000), nullable=True),
        sa.Column("new_comment", sa.String(length=2000), nullable=True),
        sa.Column("changed_by", sa.Uuid(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["record_id"], ["cleaning_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cleaning_record_edits_record_id"),
        "cleaning_record_edits",
        ["record_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_cleaning_record_edits_record_id"),
        table_name="cleaning_record_edits",
    )
    op.drop_table("cleaning_record_edits")
    op.drop_index(op.f("ix_cleaning_records_plan_id"), table_name="cleaning_records")
    op.drop_table("cleaning_records")
    op.drop_index("uq_cleaning_plans_name_active", table_name="cleaning_plans")
    op.drop_table("cleaning_plans")
    op.execute("DROP TYPE IF EXISTS cleaning_record_edit_action")
    op.execute("DROP TYPE IF EXISTS cleaning_frequency")
