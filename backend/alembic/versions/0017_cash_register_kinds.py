"""cash register kinds and non-cash collected amounts

Revision ID: 0017_cash_register_kinds
Revises: 0016_temperature_corrections
Create Date: 2026-11-25

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_cash_register_kinds"
down_revision: str | None = "0016_temperature_corrections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CASH_REGISTER_KIND = sa.Enum("cash", "cheque", "card", name="cash_register_kind")


def upgrade() -> None:
    CASH_REGISTER_KIND.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "cash_registers",
        sa.Column(
            "kind",
            CASH_REGISTER_KIND,
            nullable=False,
            server_default=sa.text("'cash'"),
        ),
    )
    op.add_column(
        "cash_sessions",
        sa.Column("collected_amount_cents", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_cash_sessions_collected_amount_nonnegative",
        "cash_sessions",
        "collected_amount_cents IS NULL OR collected_amount_cents >= 0",
    )


def downgrade() -> None:
    # Dropping the kind would turn every cheque/card register into an empty
    # cash register and silently discard its business meaning.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM cash_registers WHERE kind::text <> 'cash'
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade while non-cash cash registers exist';
            END IF;
        END $$;
        """
    )
    op.drop_constraint(
        "ck_cash_sessions_collected_amount_nonnegative",
        "cash_sessions",
        type_="check",
    )
    op.drop_column("cash_sessions", "collected_amount_cents")
    op.drop_column("cash_registers", "kind")
    CASH_REGISTER_KIND.drop(op.get_bind(), checkfirst=True)
