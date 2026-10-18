"""add the products variable type

Revision ID: 0011_product_rows_variable
Revises: 0010_template_variables
Create Date: 2026-10-18

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0011_product_rows_variable"
down_revision: str | None = "0010_template_variables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL cannot remove an enum value, so downgrade is intentionally a
    # no-op. The new value is additive and safe for existing rows.
    op.execute("ALTER TYPE template_variable_value_type ADD VALUE IF NOT EXISTS 'products'")


def downgrade() -> None:
    pass
