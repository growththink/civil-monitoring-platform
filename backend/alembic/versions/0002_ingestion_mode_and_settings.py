"""Add ingestion_mode to sensors + system_settings table

Revision ID: 0002_ingestion_mode_and_settings
Revises: 0001_init
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_ingestion_mode_and_settings"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ───── ingestion_mode enum ─────
    ingestion_mode = postgresql.ENUM(
        "modbus", "mqtt", "manual",
        name="ingestion_mode", create_type=False,
    )
    ingestion_mode.create(op.get_bind(), checkfirst=True)

    # ───── sensors.ingestion_mode column ─────
    op.add_column(
        "sensors",
        sa.Column(
            "ingestion_mode",
            ingestion_mode,
            nullable=False,
            server_default="mqtt",
        ),
    )
    op.create_index("ix_sensors_ingestion_mode", "sensors", ["ingestion_mode"])

    # Existing rows already get 'mqtt' via server_default; this is just to be explicit.
    op.execute(
        "UPDATE sensors SET ingestion_mode = 'mqtt' WHERE ingestion_mode IS NULL;"
    )

    # ───── system_settings table ─────
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(120), primary_key=True),
        sa.Column("value", sa.String(2000), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ───── initial setting: measurement_interval_minutes = '60' ─────
    op.execute(
        "INSERT INTO system_settings (key, value) VALUES ('measurement_interval_minutes', '60') "
        "ON CONFLICT (key) DO NOTHING;"
    )


def downgrade() -> None:
    op.drop_table("system_settings")

    op.drop_index("ix_sensors_ingestion_mode", table_name="sensors")
    op.drop_column("sensors", "ingestion_mode")

    op.execute("DROP TYPE IF EXISTS ingestion_mode;")
