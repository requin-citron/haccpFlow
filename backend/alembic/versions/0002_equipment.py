"""equipment table

Revision ID: 0002_equipment
Revises: 0001_initial
Create Date: 2026-10-03

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_equipment"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "equipment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("type", sa.Enum("fridge", "freezer", name="equipment_type"), nullable=False),
        sa.Column("min_temperature_celsius", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("max_temperature_celsius", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("location", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
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
    # Unique among active equipment only: a soft-deleted unit frees its name.
    op.create_index(
        "uq_equipment_name_active",
        "equipment",
        [sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_equipment_name_active", table_name="equipment")
    op.drop_table("equipment")
    op.execute("DROP TYPE IF EXISTS equipment_type")
