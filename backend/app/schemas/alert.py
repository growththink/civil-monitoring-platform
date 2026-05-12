"""Alert schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.alert import AlertCategory, AlertSeverity, AlertStatus


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ts: datetime
    site_id: uuid.UUID
    sensor_id: uuid.UUID | None
    device_id: uuid.UUID | None
    severity: AlertSeverity
    category: AlertCategory
    status: AlertStatus
    title: str
    message: str
    triggered_value: float | None
    threshold_value: float | None
    notified: bool
    acknowledged_at: datetime | None
    resolved_at: datetime | None


class AlertAck(BaseModel):
    note: str | None = None
