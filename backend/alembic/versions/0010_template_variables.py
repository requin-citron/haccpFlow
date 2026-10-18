"""template variables and generated documents

Revision ID: 0010_template_variables
Revises: 0009_latex_templates
Create Date: 2026-10-18

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_template_variables"
down_revision: str | None = "0009_latex_templates"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    variable_kind = sa.Enum("static", "local", name="template_variable_kind")
    value_type = sa.Enum("text", "number", "date", name="template_variable_value_type")

    op.create_table(
        "template_variables",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("kind", variable_kind, nullable=False),
        sa.Column("value_type", value_type, nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "kind <> 'static' OR value IS NOT NULL",
            name="ck_template_variables_static_value",
        ),
        sa.ForeignKeyConstraint(["template_id"], ["latex_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id", "name", name="uq_template_variables_template_name"),
    )
    op.create_index(
        op.f("ix_template_variables_template_id"),
        "template_variables",
        ["template_id"],
        unique=False,
    )

    op.create_table(
        "generated_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("template_name", sa.String(length=120), nullable=False),
        sa.Column("generated_by_id", sa.Uuid(), nullable=True),
        sa.Column("values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=80), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
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
        sa.ForeignKeyConstraint(["generated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["latex_templates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        op.f("ix_generated_documents_template_id"),
        "generated_documents",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generated_documents_generated_by_id"),
        "generated_documents",
        ["generated_by_id"],
        unique=False,
    )
    op.create_index(
        "ix_generated_documents_created_at",
        "generated_documents",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_generated_documents_created_at", table_name="generated_documents")
    op.drop_index(
        op.f("ix_generated_documents_generated_by_id"),
        table_name="generated_documents",
    )
    op.drop_index(op.f("ix_generated_documents_template_id"), table_name="generated_documents")
    op.drop_table("generated_documents")

    op.drop_index(op.f("ix_template_variables_template_id"), table_name="template_variables")
    op.drop_table("template_variables")

    sa.Enum(name="template_variable_value_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="template_variable_kind").drop(op.get_bind(), checkfirst=True)
