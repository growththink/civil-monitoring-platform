"""Global key/value system settings (e.g. measurement_interval_minutes)."""
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(String(2000), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


MEASUREMENT_INTERVAL_KEY = "measurement_interval_minutes"
DEFAULT_MEASUREMENT_INTERVAL = "60"
