"""Sensor model — physical sensor attached to a device."""
import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, pg_enum


class SensorType(str, enum.Enum):
    INCLINOMETER = "inclinometer"
    SETTLEMENT = "settlement"
    CRACK = "crack"
    LVDT = "lvdt"
    PIEZOMETER = "piezometer"
    WATER_LEVEL = "water_level"
    LOAD_CELL = "load_cell"
    STRAIN_GAUGE = "strain_gauge"
    VIBRATION = "vibration"
    SOUND_LEVEL = "sound_level"
    TOTAL_STATION = "total_station"
    GNSS = "gnss"
    TEMPERATURE = "temperature"
    OTHER = "other"


class IngestionMode(str, enum.Enum):
    MODBUS = "modbus"
    MQTT = "mqtt"
    MANUAL = "manual"


class Sensor(Base):
    __tablename__ = "sensors"
    __table_args__ = (
        UniqueConstraint("device_id", "code", name="uq_sensor_device_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sensor_type: Mapped[SensorType] = mapped_column(
        pg_enum(SensorType, name="sensor_type"), nullable=False, index=True
    )
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

    # How readings reach the platform (modbus polled, mqtt-pushed, manual excel)
    ingestion_mode: Mapped[IngestionMode] = mapped_column(
        pg_enum(IngestionMode, name="ingestion_mode"),
        nullable=False,
        default=IngestionMode.MQTT,
        server_default=IngestionMode.MQTT.value,
        index=True,
    )

    # Modbus mapping (used only when ingestion_mode = modbus)
    modbus_register_address: Mapped[int | None] = mapped_column(Integer)
    modbus_register_count: Mapped[int] = mapped_column(Integer, default=2)
    modbus_data_type: Mapped[str | None] = mapped_column(String(20))  # float32, int16, int32

    # Calibration
    calibration_offset: Mapped[float] = mapped_column(Float, default=0.0)
    calibration_scale: Mapped[float] = mapped_column(Float, default=1.0)
    initial_baseline: Mapped[float | None] = mapped_column(Float)

    # Health
    expected_interval_seconds: Mapped[int] = mapped_column(Integer, default=3600)
    last_reading_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    device: Mapped["Device"] = relationship(back_populates="sensors")  # noqa: F821
    thresholds: Mapped[list["SensorThreshold"]] = relationship(
        back_populates="sensor", cascade="all, delete-orphan"
    )


class ThresholdLevel(str, enum.Enum):
    WARNING = "warning"
    CRITICAL = "critical"


class SensorThreshold(Base):
    __tablename__ = "sensor_thresholds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sensor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sensors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level: Mapped[ThresholdLevel] = mapped_column(
        pg_enum(ThresholdLevel, name="threshold_level"), nullable=False
    )
    min_value: Mapped[float | None] = mapped_column(Float)
    max_value: Mapped[float | None] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    sensor: Mapped["Sensor"] = relationship(back_populates="thresholds")
