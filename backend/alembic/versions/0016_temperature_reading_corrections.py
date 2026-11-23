"""store the final temperature reading correction on each slot

Revision ID: 0016_temperature_corrections
Revises: 0015_transport_checkpoints
Create Date: 2026-11-23

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_temperature_corrections"
down_revision: str | None = "0015_transport_checkpoints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_JUSTIFICATION = "Correction antérieure non justifiée"


def upgrade() -> None:
    op.add_column("temperature_readings", sa.Column("created_by", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_temperature_readings_created_by_users",
        "temperature_readings",
        "users",
        ["created_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "temperature_readings",
        sa.Column(
            "corrected_temperature_celsius",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
    )
    op.add_column(
        "temperature_readings",
        sa.Column("corrected_is_compliant", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "temperature_readings",
        sa.Column("correction_justification", sa.Text(), nullable=True),
    )
    op.add_column("temperature_readings", sa.Column("corrected_by", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_temperature_readings_corrected_by_users",
        "temperature_readings",
        "users",
        ["corrected_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "temperature_readings",
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Creation rows previously carried the author. Move that information to the
    # reading itself before the old edit table becomes a read-only archive.
    op.execute(
        """
        UPDATE temperature_readings AS reading
        SET created_by = (
            SELECT edit.changed_by
            FROM temperature_reading_edits AS edit
            WHERE edit.reading_id = reading.id
              AND edit.action = 'created'
            ORDER BY edit.changed_at, edit.id
            LIMIT 1
        )
        """
    )

    # Collapse every historical correction into the state required by the new
    # contract: immutable original value plus one final correction.
    op.execute(
        f"""
        WITH originals AS (
            SELECT reading_id, new_celsius
            FROM (
                SELECT
                    reading_id,
                    new_celsius,
                    row_number() OVER (
                        PARTITION BY reading_id
                        ORDER BY changed_at, id
                    ) AS position
                FROM temperature_reading_edits
                WHERE action = 'created'
            ) AS ranked
            WHERE position = 1
        ),
        latest_updates AS (
            SELECT DISTINCT ON (reading_id)
                reading_id,
                changed_by,
                changed_at
            FROM temperature_reading_edits
            WHERE action = 'updated'
            ORDER BY reading_id, changed_at DESC, id DESC
        ),
        collapsed AS (
            SELECT
                reading.id,
                reading.temperature_celsius AS effective_celsius,
                reading.is_compliant AS effective_is_compliant,
                COALESCE(original.new_celsius, reading.temperature_celsius)
                    AS original_celsius,
                COALESCE(original.new_celsius, reading.temperature_celsius)
                    BETWEEN equipment.min_temperature_celsius
                    AND equipment.max_temperature_celsius
                    AS original_is_compliant,
                update_row.changed_by,
                update_row.changed_at
            FROM temperature_readings AS reading
            JOIN latest_updates AS update_row
                ON update_row.reading_id = reading.id
            LEFT JOIN originals AS original
                ON original.reading_id = reading.id
            JOIN equipment
                ON equipment.id = reading.equipment_id
        )
        UPDATE temperature_readings AS reading
        SET
            corrected_temperature_celsius = collapsed.effective_celsius,
            corrected_is_compliant = collapsed.effective_is_compliant,
            correction_justification = '{LEGACY_JUSTIFICATION}',
            corrected_by = collapsed.changed_by,
            corrected_at = collapsed.changed_at,
            temperature_celsius = collapsed.original_celsius,
            is_compliant = collapsed.original_is_compliant
        FROM collapsed
        WHERE reading.id = collapsed.id
        """
    )

    op.create_check_constraint(
        "ck_temperature_readings_correction_complete",
        "temperature_readings",
        """
        (
            corrected_at IS NULL
            AND corrected_temperature_celsius IS NULL
            AND corrected_is_compliant IS NULL
            AND correction_justification IS NULL
            AND corrected_by IS NULL
        )
        OR
        (
            corrected_at IS NOT NULL
            AND corrected_temperature_celsius IS NOT NULL
            AND corrected_is_compliant IS NOT NULL
            AND correction_justification IS NOT NULL
            AND btrim(correction_justification) <> ''
        )
        """,
    )


def downgrade() -> None:
    # Recreate creation rows only for slots that have no legacy audit at all.
    op.execute(
        """
        INSERT INTO temperature_reading_edits (
            id,
            reading_id,
            action,
            previous_celsius,
            new_celsius,
            changed_by,
            changed_at
        )
        SELECT
            gen_random_uuid(),
            reading.id,
            'created',
            NULL,
            reading.temperature_celsius,
            reading.created_by,
            reading.recorded_at
        FROM temperature_readings AS reading
        WHERE NOT EXISTS (
            SELECT 1
            FROM temperature_reading_edits AS edit
            WHERE edit.reading_id = reading.id
        )
        """
    )
    op.execute(
        """
        INSERT INTO temperature_reading_edits (
            id,
            reading_id,
            action,
            previous_celsius,
            new_celsius,
            changed_by,
            changed_at
        )
        SELECT
            gen_random_uuid(),
            reading.id,
            'updated',
            reading.temperature_celsius,
            reading.corrected_temperature_celsius,
            reading.corrected_by,
            reading.corrected_at
        FROM temperature_readings AS reading
        WHERE reading.corrected_at IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM temperature_reading_edits AS edit
              WHERE edit.reading_id = reading.id
                AND edit.action = 'updated'
          )
        """
    )

    # The previous code expects the effective value in temperature_celsius.
    op.execute(
        """
        UPDATE temperature_readings
        SET
            temperature_celsius = COALESCE(
                corrected_temperature_celsius,
                temperature_celsius
            ),
            is_compliant = COALESCE(corrected_is_compliant, is_compliant),
            source = CASE
                WHEN corrected_at IS NOT NULL THEN 'manual'
                ELSE source
            END
        """
    )

    op.drop_constraint(
        "ck_temperature_readings_correction_complete",
        "temperature_readings",
        type_="check",
    )
    op.drop_constraint(
        "fk_temperature_readings_corrected_by_users",
        "temperature_readings",
        type_="foreignkey",
    )
    op.drop_column("temperature_readings", "corrected_at")
    op.drop_column("temperature_readings", "corrected_by")
    op.drop_column("temperature_readings", "correction_justification")
    op.drop_column("temperature_readings", "corrected_is_compliant")
    op.drop_column("temperature_readings", "corrected_temperature_celsius")
    op.drop_constraint(
        "fk_temperature_readings_created_by_users",
        "temperature_readings",
        type_="foreignkey",
    )
    op.drop_column("temperature_readings", "created_by")
