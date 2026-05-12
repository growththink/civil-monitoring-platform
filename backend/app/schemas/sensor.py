"""Sensor schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.sensor import IngestionMode, SensorType, ThresholdLevel


class ThresholdIn(BaseModel):
    level: ThresholdLevel
    min_value: float | None = None
    max_value: float | None = None


class ThresholdOut(ThresholdIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    is_active: bool


class SensorBase(BaseModel):
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=200)
    serial_number: str | None = None
    sensor_type: SensorType
    unit: str = Field(..., max_length=20)
    ingestion_mode: IngestionMode = IngestionMode.MQTT
    modbus_register_address: int | None = None
    modbus_register_count: int = 2
    modbus_data_type: str | None = "float32"
    calibration_offset: float = 0.0
    calibration_scale: float = 1.0
    initial_baseline: float | None = None
    expected_interval_seconds: int = 3600
    metadata: dict[str, Any] = Field(default_factory=dict)


class SensorCreate(SensorBase):
    device_id: uuid.UUID
    thresholds: list[ThresholdIn] = Field(default_factory=list)


class SensorUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None
    ingestion_mode: IngestionMode | None = None
    modbus_register_address: int | None = None
    modbus_register_count: int | None = None
    modbus_data_type: str | None = None
    calibration_offset: float | None = None
    calibration_scale: float | None = None
    initial_baseline: float | None = None
    expected_interval_seconds: int | None = None
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


class SensorOut(SensorBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    device_id: uuid.UUID
    is_active: bool
    last_reading_at: datetime | None
    created_at: datetime
    thresholds: list[ThresholdOut] = Field(default_factory=list)
    # ORM attribute is `metadata_` (the column literal "metadata" conflicts with
    # SQLAlchemy DeclarativeBase.metadata); read via alias, serialize as "metadata"
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")


class SensorWithLatest(SensorOut):
    latest_value: float | None = None
    latest_ts: datetime | None = None
    latest_quality: str | None = None
