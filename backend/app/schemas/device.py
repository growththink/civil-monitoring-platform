"""Device schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.device import DeviceType, Protocol


class DeviceBase(BaseModel):
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=200)
    serial_number: str | None = None
    device_type: DeviceType
    primary_protocol: Protocol
    ip_address: str | None = None
    port: int | None = Field(None, ge=1, le=65535)
    modbus_unit_id: int | None = Field(None, ge=0, le=255)
    config: dict[str, Any] = Field(default_factory=dict)


class DeviceCreate(DeviceBase):
    site_id: uuid.UUID


class DeviceUpdate(BaseModel):
    name: str | None = None
    serial_number: str | None = None
    ip_address: str | None = None
    port: int | None = None
    modbus_unit_id: int | None = None
    config: dict[str, Any] | None = None


class DeviceOut(DeviceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    site_id: uuid.UUID
    last_heartbeat_at: datetime | None
    is_online: bool
    created_at: datetime


class DeviceCreatedResponse(DeviceOut):
    """Returned only on creation; contains the plain API key."""
    api_key: str
