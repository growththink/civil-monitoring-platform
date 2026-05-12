"""Reading and ingestion schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.reading import IngestSource, QualityFlag


class ReadingPoint(BaseModel):
    ts: datetime
    value: float
    quality: QualityFlag = QualityFlag.GOOD


class IngestPayload(BaseModel):
    """Payload posted by gateway via HTTP or published via MQTT."""
    device_code: str = Field(..., description="Device code (must match device record)")
    sensor_code: str = Field(..., description="Sensor code under that device")
    ts: datetime
    value: float
    quality: QualityFlag = QualityFlag.GOOD
    metadata: dict[str, Any] = Field(default_factory=dict)


class BatchIngestPayload(BaseModel):
    device_code: str
    readings: list[dict] = Field(..., description="List of {sensor_code, ts, value, quality?}")


class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sensor_id: uuid.UUID
    ts: datetime
    value: float
    quality: QualityFlag


class TimeSeriesQuery(BaseModel):
    sensor_id: uuid.UUID
    from_ts: datetime
    to_ts: datetime
    interval: str | None = None  # e.g. '1 minute', '1 hour' for downsampling


class TimeSeriesPoint(BaseModel):
    ts: datetime
    value: float
    quality: QualityFlag = QualityFlag.GOOD


class TimeSeriesResponse(BaseModel):
    sensor_id: uuid.UUID
    points: list[TimeSeriesPoint]
    count: int


class IngestResponse(BaseModel):
    accepted: int
    rejected: int
    errors: list[str] = Field(default_factory=list)
