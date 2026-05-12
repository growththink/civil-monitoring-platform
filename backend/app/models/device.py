"""Device model — gateway/data-logger/PLC/RTU."""
import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, pg_enum


class DeviceType(str, enum.Enum):
    DATALOGGER = "datalogger"
    PLC = "plc"
    RTU = "rtu"
    GATEWAY = "gateway"
    STANDALONE = "standalone"


class Protocol(str, enum.Enum):
    MQTT = "mqtt"
    HTTP = "http"
    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"
    CSV = "csv"


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("site_id", "code", name="uq_device_site_code"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    device_type: Mapped[DeviceType] = mapped_column(
        pg_enum(DeviceType, name="device_type"), nullable=False
    )
    primary_protocol: Mapped[Protocol] = mapped_column(
        pg_enum(Protocol, name="device_protocol"), nullable=False
    )

    # Modbus TCP
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    modbus_unit_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Auth
    api_key_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    # Status
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)

    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    site: Mapped["Site"] = relationship(back_populates="devices")  # noqa: F821
    sensors: Mapped[list["Sensor"]] = relationship(  # noqa: F821
        back_populates="device", cascade="all, delete-orphan"
    )
