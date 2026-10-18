"""add static image variables and their assets

Revision ID: 0012_template_image_variables
Revises: 0011_product_rows_variable
Create Date: 2026-10-18

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_template_image_variables"
down_revision: str | None = "0011_product_rows_variable"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE template_variable_value_type ADD VALUE IF NOT EXISTS 'image'")
    op.drop_constraint(
        "ck_template_variables_static_value",
        "template_variables",
        type_="check",
    )
    op.create_check_constraint(
        "ck_template_variables_static_value",
        "template_variables",
        "kind <> 'static' OR value IS NOT NULL OR value_type::text = 'image'",
    )
    op.create_table(
        "template_variable_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("variable_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=80), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("uploaded_by_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["variable_id"],
            ["template_variables.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
        sa.UniqueConstraint("variable_id"),
    )


def downgrade() -> None:
    op.drop_table("template_variable_assets")
