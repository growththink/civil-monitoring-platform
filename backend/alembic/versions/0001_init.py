"""init schema with TimescaleDB hypertables

Revision ID: 0001_init
Revises:
Create Date: 2026-05-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ───── Extensions ─────
    op.execute("CREATE EXTENSION IF NOT EXISTS \"timescaledb\";")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";")

    # ───── ENUMs ─────
    user_role = postgresql.ENUM(
        "super_admin", "admin", "operator", "client",
        name="user_role", create_type=False,
    )
    user_role.create(op.get_bind(), checkfirst=True)

    site_status = postgresql.ENUM(
        "normal", "warning", "critical", "disconnected",
        name="site_status", create_type=False,
    )
    site_status.create(op.get_bind(), checkfirst=True)

    device_type = postgresql.ENUM(
        "datalogger", "plc", "rtu", "gateway", "standalone",
        name="device_type", create_type=False,
    )
    device_type.create(op.get_bind(), checkfirst=True)

    device_protocol = postgresql.ENUM(
        "mqtt", "http", "modbus_tcp", "modbus_rtu", "csv",
        name="device_protocol", create_type=False,
    )
    device_protocol.create(op.get_bind(), checkfirst=True)

    sensor_type = postgresql.ENUM(
        "inclinometer", "settlement", "crack", "lvdt", "piezometer",
        "water_level", "load_cell", "strain_gauge", "vibration",
        "sound_level", "total_station", "gnss", "temperature", "other",
        name="sensor_type", create_type=False,
    )
    sensor_type.create(op.get_bind(), checkfirst=True)

    threshold_level = postgresql.ENUM(
        "warning", "critical",
        name="threshold_level", create_type=False,
    )
    threshold_level.create(op.get_bind(), checkfirst=True)

    quality_flag = postgresql.ENUM(
        "good", "suspect", "bad", "missing",
        name="quality_flag", create_type=False,
    )
    quality_flag.create(op.get_bind(), checkfirst=True)

    ingest_source = postgresql.ENUM(
        "mqtt", "http", "modbus", "csv",
        name="ingest_source", create_type=False,
    )
    ingest_source.create(op.get_bind(), checkfirst=True)

    alert_severity = postgresql.ENUM(
        "info", "warning", "critical",
        name="alert_severity", create_type=False,
    )
    alert_severity.create(op.get_bind(), checkfirst=True)

    alert_category = postgresql.ENUM(
        "threshold", "communication", "data_missing", "device_offline",
        name="alert_category", create_type=False,
    )
    alert_category.create(op.get_bind(), checkfirst=True)

    alert_status = postgresql.ENUM(
        "open", "acknowledged", "resolved",
        name="alert_status", create_type=False,
    )
    alert_status.create(op.get_bind(), checkfirst=True)

    # ───── users ─────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("phone", sa.String(40)),
        sa.Column("role", user_role, nullable=False, server_default="client"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ───── sites ─────
    op.create_table(
        "sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("address", sa.String(500)),
        sa.Column("latitude", sa.Float),
        sa.Column("longitude", sa.Float),
        sa.Column("manager_user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("customer_user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("status", site_status, nullable=False, server_default="normal"),
        sa.Column("last_data_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sites_code", "sites", ["code"])

    # ───── user_site_access ─────
    op.create_table(
        "user_site_access",
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("can_edit", sa.Boolean, server_default=sa.false()),
    )

    # ───── devices ─────
    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("site_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("serial_number", sa.String(120)),
        sa.Column("device_type", device_type, nullable=False),
        sa.Column("primary_protocol", device_protocol, nullable=False),
        sa.Column("ip_address", postgresql.INET),
        sa.Column("port", sa.Integer),
        sa.Column("modbus_unit_id", sa.Integer),
        sa.Column("api_key_hash", sa.String(128)),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("is_online", sa.Boolean, server_default=sa.false()),
        sa.Column("config", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("site_id", "code", name="uq_device_site_code"),
    )
    op.create_index("ix_devices_site_id", "devices", ["site_id"])
    op.create_index("ix_devices_api_key_hash", "devices", ["api_key_hash"])

    # ───── sensors ─────
    op.create_table(
        "sensors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("device_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("serial_number", sa.String(120)),
        sa.Column("sensor_type", sensor_type, nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("modbus_register_address", sa.Integer),
        sa.Column("modbus_register_count", sa.Integer, server_default="2"),
        sa.Column("modbus_data_type", sa.String(20)),
        sa.Column("calibration_offset", sa.Float, server_default="0"),
        sa.Column("calibration_scale", sa.Float, server_default="1"),
        sa.Column("initial_baseline", sa.Float),
        sa.Column("expected_interval_seconds", sa.Integer, server_default="3600"),
        sa.Column("last_reading_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("device_id", "code", name="uq_sensor_device_code"),
    )
    op.create_index("ix_sensors_device_id", "sensors", ["device_id"])
    op.create_index("ix_sensors_sensor_type", "sensors", ["sensor_type"])

    # ───── sensor_thresholds ─────
    op.create_table(
        "sensor_thresholds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("sensor_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level", threshold_level, nullable=False),
        sa.Column("min_value", sa.Float),
        sa.Column("max_value", sa.Float),
        sa.Column("is_active", sa.Boolean, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sensor_thresholds_sensor_id", "sensor_thresholds", ["sensor_id"])

    # ───── raw_readings (hypertable) ─────
    op.create_table(
        "raw_readings",
        sa.Column("sensor_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sensors.id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), primary_key=True, nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("quality", quality_flag, server_default="good"),
        sa.Column("source", ingest_source),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
    )
    op.create_index("ix_raw_sensor_time", "raw_readings", ["sensor_id", "ts"])

    # ───── calculated_readings (hypertable) ─────
    op.create_table(
        "calculated_readings",
        sa.Column("sensor_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sensors.id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), primary_key=True, nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("delta_from_baseline", sa.Float),
        sa.Column("quality", quality_flag, server_default="good"),
    )
    op.create_index("ix_calc_sensor_time", "calculated_readings", ["sensor_id", "ts"])

    # ───── ingest_errors ─────
    op.create_table(
        "ingest_errors",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("source", ingest_source),
        sa.Column("device_id", postgresql.UUID(as_uuid=True)),
        sa.Column("sensor_code", sa.String(64)),
        sa.Column("error_type", sa.String(80)),
        sa.Column("message", sa.String(2000)),
        sa.Column("payload", postgresql.JSONB, server_default="{}"),
    )
    op.create_index("ix_ingest_errors_ts", "ingest_errors", ["ts"])

    # ───── alerts ─────
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("ts", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sensor_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sensors.id", ondelete="SET NULL")),
        sa.Column("device_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("devices.id", ondelete="SET NULL")),
        sa.Column("severity", alert_severity, nullable=False),
        sa.Column("category", alert_category, nullable=False),
        sa.Column("status", alert_status, nullable=False, server_default="open"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.String(2000), nullable=False),
        sa.Column("triggered_value", sa.Float),
        sa.Column("threshold_value", sa.Float),
        sa.Column("notified", sa.Boolean, server_default=sa.false()),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("acknowledged_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", postgresql.JSONB, server_default="{}"),
    )
    op.create_index("ix_alerts_status_ts", "alerts", ["status", "ts"])
    op.create_index("ix_alerts_site", "alerts", ["site_id"])

    # ───── Hypertables ─────
    op.execute(
        "SELECT create_hypertable('raw_readings', 'ts', "
        "chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);"
    )
    op.execute(
        "SELECT create_hypertable('calculated_readings', 'ts', "
        "chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);"
    )

    # ───── Compression policy (after 30 days) ─────
    op.execute("""
        ALTER TABLE raw_readings SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'sensor_id'
        );
    """)
    op.execute("""
        ALTER TABLE calculated_readings SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'sensor_id'
        );
    """)
    op.execute(
        "SELECT add_compression_policy('raw_readings', INTERVAL '30 days');"
    )
    op.execute(
        "SELECT add_compression_policy('calculated_readings', INTERVAL '30 days');"
    )

    # ───── Retention (drop raw after 2 years; calculated kept indefinitely) ─────
    op.execute(
        "SELECT add_retention_policy('raw_readings', INTERVAL '2 years');"
    )


def downgrade() -> None:
    op.execute("SELECT remove_retention_policy('raw_readings', if_exists => TRUE);")
    op.execute("SELECT remove_compression_policy('raw_readings', if_exists => TRUE);")
    op.execute("SELECT remove_compression_policy('calculated_readings', if_exists => TRUE);")

    op.drop_table("alerts")
    op.drop_table("ingest_errors")
    op.drop_table("calculated_readings")
    op.drop_table("raw_readings")
    op.drop_table("sensor_thresholds")
    op.drop_table("sensors")
    op.drop_table("devices")
    op.drop_table("user_site_access")
    op.drop_table("sites")
    op.drop_table("users")

    for enum_name in [
        "alert_status", "alert_category", "alert_severity",
        "ingest_source", "quality_flag", "threshold_level",
        "sensor_type", "device_protocol", "device_type",
        "site_status", "user_role",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name};")
