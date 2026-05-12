"""Alert models — threshold breach + communication failure alarms."""
import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, pg_enum


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertCategory(str, enum.Enum):
    THRESHOLD = "threshold"
    COMMUNICATION = "communication"
    DATA_MISSING = "data_missing"
    DEVICE_OFFLINE = "device_offline"


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_status_ts", "status", "ts"),
        Index("ix_alerts_site", "site_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
    )
    sensor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sensors.id", ondelete="SET NULL"),
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="SET NULL"),
    )

    severity: Mapped[AlertSeverity] = mapped_column(
        pg_enum(AlertSeverity, name="alert_severity"), nullable=False
    )
    category: Mapped[AlertCategory] = mapped_column(
        pg_enum(AlertCategory, name="alert_category"), nullable=False
    )
    status: Mapped[AlertStatus] = mapped_column(
        pg_enum(AlertStatus, name="alert_status"),
        default=AlertStatus.OPEN,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(String(2000), nullable=False)
    triggered_value: Mapped[float | None] = mapped_column(Float)
    threshold_value: Mapped[float | None] = mapped_column(Float)

    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
