"""Schemas for global system settings."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SystemSettingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: str
    updated_at: datetime


class SystemSettingUpdate(BaseModel):
    value: str = Field(..., max_length=2000)
