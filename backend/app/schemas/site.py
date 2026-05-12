"""Site schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.site import SiteStatus


class SiteBase(BaseModel):
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=200)
    address: str | None = None
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    manager_user_id: uuid.UUID | None = None
    customer_user_id: uuid.UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SiteCreate(SiteBase):
    pass


class SiteUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    manager_user_id: uuid.UUID | None = None
    customer_user_id: uuid.UUID | None = None
    metadata: dict[str, Any] | None = None


class SiteOut(SiteBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    status: SiteStatus
    last_data_at: datetime | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")


class SiteSummary(BaseModel):
    """For dashboard overview list."""
    id: uuid.UUID
    code: str
    name: str
    status: SiteStatus
    latitude: float | None
    longitude: float | None
    sensor_count: int
    online_device_count: int
    open_alerts: int
    last_data_at: datetime | None
