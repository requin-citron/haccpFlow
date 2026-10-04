"""vehicles and transport tracking

Revision ID: 0006_vehicles_transports
Revises: 0005_pasteurisation
Create Date: 2026-10-04

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_vehicles_transports"
down_revision: str | None = "0005_pasteurisation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("plate", sa.String(length=32), nullable=True),
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
        "uq_vehicles_name_active",
        "vehicles",
        [sa.text("lower(name)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND name IS NOT NULL"),
    )
    op.create_index(
        "uq_vehicles_plate_active",
        "vehicles",
        [sa.text("lower(plate)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND plate IS NOT NULL"),
    )

    op.create_table(
        "transports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transport_date", sa.Date(), nullable=False),
        sa.Column("place", sa.String(length=160), nullable=False),
        sa.Column("product_name", sa.String(length=160), nullable=False),
        sa.Column("lot_number", sa.String(length=80), nullable=True),
        sa.Column("vehicle_id", sa.Uuid(), nullable=True),
        sa.Column("vehicle_label", sa.String(length=120), nullable=True),
        sa.Column("departure_time", sa.Time(), nullable=True),
        sa.Column("departure_temperature_celsius", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("arrival_time", sa.Time(), nullable=True),
        sa.Column("arrival_temperature_celsius", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("observation", sa.String(length=2000), nullable=True),
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
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_transports_lot_number"),
        "transports",
        ["lot_number"],
        unique=False,
    )
    op.create_index(
        op.f("ix_transports_vehicle_id"),
        "transports",
        ["vehicle_id"],
        unique=False,
    )

    op.create_table(
        "transport_edits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transport_id", sa.Uuid(), nullable=False),
        sa.Column(
            "action",
            sa.Enum("created", "updated", name="transport_edit_action"),
            nullable=False,
        ),
        sa.Column("previous_departure_time", sa.Time(), nullable=True),
        sa.Column("new_departure_time", sa.Time(), nullable=True),
        sa.Column(
            "previous_departure_temperature_celsius",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
        sa.Column(
            "new_departure_temperature_celsius", sa.Numeric(precision=5, scale=2), nullable=True
        ),
        sa.Column("previous_arrival_time", sa.Time(), nullable=True),
        sa.Column("new_arrival_time", sa.Time(), nullable=True),
        sa.Column(
            "previous_arrival_temperature_celsius", sa.Numeric(precision=5, scale=2), nullable=True
        ),
        sa.Column(
            "new_arrival_temperature_celsius", sa.Numeric(precision=5, scale=2), nullable=True
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
        sa.ForeignKeyConstraint(["transport_id"], ["transports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_transport_edits_transport_id"),
        "transport_edits",
        ["transport_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_transport_edits_transport_id"), table_name="transport_edits")
    op.drop_table("transport_edits")
    op.drop_index(op.f("ix_transports_vehicle_id"), table_name="transports")
    op.drop_index(op.f("ix_transports_lot_number"), table_name="transports")
    op.drop_table("transports")
    op.drop_index("uq_vehicles_plate_active", table_name="vehicles")
    op.drop_index("uq_vehicles_name_active", table_name="vehicles")
    op.drop_table("vehicles")
    op.execute("DROP TYPE IF EXISTS transport_edit_action")
