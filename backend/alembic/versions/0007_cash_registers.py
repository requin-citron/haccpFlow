"""cash registers and their opening count

Revision ID: 0007_cash_registers
Revises: 0006_vehicles_transports
Create Date: 2026-10-04

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_cash_registers"
down_revision: str | None = "0006_vehicles_transports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: column name, value in cents
DENOMINATIONS: tuple[tuple[str, int], ...] = (
    ("coins_1_cent", 1),
    ("coins_2_cent", 2),
    ("coins_5_cent", 5),
    ("coins_10_cent", 10),
    ("coins_20_cent", 20),
    ("coins_50_cent", 50),
    ("coins_1_euro", 100),
    ("coins_2_euro", 200),
    ("notes_5_euro", 500),
    ("notes_10_euro", 1000),
    ("notes_20_euro", 2000),
    ("notes_50_euro", 5000),
)


def upgrade() -> None:
    op.create_table(
        "cash_registers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        *[
            sa.Column(name, sa.Integer(), nullable=False, server_default=sa.text("0"))
            for name, _ in DENOMINATIONS
        ],
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
        "uq_cash_registers_name_active",
        "cash_registers",
        [sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_cash_registers_name_active", table_name="cash_registers")
    op.drop_table("cash_registers")
