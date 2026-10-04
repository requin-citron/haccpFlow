"""cash sessions, their expenses and the closing count

Revision ID: 0008_cash_sessions
Revises: 0007_cash_registers
Create Date: 2026-10-04

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_cash_sessions"
down_revision: str | None = "0007_cash_registers"
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
        "cash_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cash_register_id", sa.Uuid(), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        *[
            sa.Column(name, sa.Integer(), nullable=False, server_default=sa.text("0"))
            for name, _ in DENOMINATIONS
        ],
        *[sa.Column(f"closed_{name}", sa.Integer(), nullable=True) for name, _ in DENOMINATIONS],
        sa.Column("opened_by", sa.Uuid(), nullable=True),
        sa.Column("closed_by", sa.Uuid(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["cash_register_id"],
            ["cash_registers.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["opened_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cash_sessions_cash_register_id"),
        "cash_sessions",
        ["cash_register_id"],
        unique=False,
    )
    # One open session per register at most: the partial index ignores the
    # closed and soft-deleted rows, which are just history.
    op.create_index(
        "uq_cash_sessions_open_per_register",
        "cash_sessions",
        ["cash_register_id"],
        unique=True,
        postgresql_where=sa.text("closed_at IS NULL AND deleted_at IS NULL"),
    )

    op.create_table(
        "cash_expenses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("professional", "personal", name="cash_expense_kind"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "vat_rate",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
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
        sa.ForeignKeyConstraint(["session_id"], ["cash_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cash_expenses_session_id"),
        "cash_expenses",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_cash_expenses_session_id"), table_name="cash_expenses")
    op.drop_table("cash_expenses")
    op.execute("DROP TYPE IF EXISTS cash_expense_kind")

    op.drop_index("uq_cash_sessions_open_per_register", table_name="cash_sessions")
    op.drop_index(op.f("ix_cash_sessions_cash_register_id"), table_name="cash_sessions")
    op.drop_table("cash_sessions")
