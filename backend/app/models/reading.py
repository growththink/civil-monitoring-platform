"""Reading models — time-series data stored as TimescaleDB hypertables.

Note: TimescaleDB requires the time column to be part of the primary key.
We model these as composite-PK tables. Conversion to hypertables is done
in the Alembic migration via `SELECT create_hypertable(...)`.
"""
import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, pg_enum


class QualityFlag(str, enum.Enum):
    GOOD = "good"
    SUSPECT = "suspect"
    BAD = "bad"
    MISSING = "missing"


class IngestSource(str, enum.Enum):
    MQTT = "mqtt"
    HTTP = "http"
    MODBUS = "modbus"
    CSV = "csv"


class RawReading(Base):
    """As-received raw values from sensors."""
    __tablename__ = "raw_readings"
    __table_args__ = (
        Index("ix_raw_sensor_time", "sensor_id", "ts"),
    )

    sensor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sensors.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    quality: Mapped[QualityFlag] = mapped_column(
        pg_enum(QualityFlag, name="quality_flag"), default=QualityFlag.GOOD
    )
    source: Mapped[IngestSource] = mapped_column(pg_enum(IngestSource, name="ingest_source"))
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class CalculatedReading(Base):
    """Calibrated/converted engineering values."""
    __tablename__ = "calculated_readings"
    __table_args__ = (
        Index("ix_calc_sensor_time", "sensor_id", "ts"),
    )

    sensor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sensors.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    delta_from_baseline: Mapped[float | None] = mapped_column(Float)
    quality: Mapped[QualityFlag] = mapped_column(
        pg_enum(QualityFlag, name="quality_flag"),
        default=QualityFlag.GOOD,
    )


class IngestError(Base):
    """Records validation/communication failures."""
    __tablename__ = "ingest_errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    source: Mapped[IngestSource] = mapped_column(
        pg_enum(IngestSource, name="ingest_source")
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    sensor_code: Mapped[str | None] = mapped_column(String(64))
    error_type: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(String(2000))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
