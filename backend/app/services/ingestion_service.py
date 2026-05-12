"""Core data ingestion logic.

Single function `ingest_one_reading` accepts a normalized payload (from any
source — MQTT, HTTP, Modbus poller, CSV) and:
  1. Resolves device + sensor from codes
  2. Inserts raw reading
  3. Applies calibration → calculated reading
  4. Updates last_reading_at on sensor + last_data_at on site + heartbeat on device
  5. Evaluates thresholds → may create an Alert
  6. Returns the inserted CalculatedReading (or None)
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.alert import Alert
from app.models.device import Device
from app.models.reading import (
    CalculatedReading,
    IngestError,
    IngestSource,
    QualityFlag,
    RawReading,
)
from app.models.sensor import Sensor
from app.models.site import Site, SiteStatus
from app.services.notification_service import dispatch_alert_notifications
from app.services.threshold_service import evaluate_thresholds
from app.ws.manager import broadcaster

log = get_logger(__name__)


def _to_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


async def _resolve_sensor(
    db: AsyncSession,
    device_code: str,
    sensor_code: str,
    api_key_device_id: Optional[str] = None,
) -> tuple[Optional[Device], Optional[Sensor]]:
    stmt = select(Device).where(Device.code == device_code)
    if api_key_device_id:
        stmt = stmt.where(Device.id == api_key_device_id)
    device = (await db.execute(stmt)).scalar_one_or_none()
    if not device:
        return None, None

    sensor_stmt = (
        select(Sensor)
        .options(selectinload(Sensor.thresholds))
        .where(Sensor.device_id == device.id, Sensor.code == sensor_code)
    )
    sensor = (await db.execute(sensor_stmt)).scalar_one_or_none()
    return device, sensor


async def ingest_one_reading(
    db: AsyncSession,
    *,
    device_code: str,
    sensor_code: str,
    ts: datetime,
    raw_value: float,
    quality: QualityFlag,
    source: IngestSource,
    metadata: dict | None = None,
    api_key_device_id: Optional[str] = None,
) -> Optional[CalculatedReading]:
    """Ingest a single reading. Idempotent on (sensor_id, ts) PK conflict."""
    metadata = metadata or {}
    ts_utc = _to_utc(ts)

    device, sensor = await _resolve_sensor(db, device_code, sensor_code, api_key_device_id)
    if not device or not sensor:
        db.add(IngestError(
            source=source,
            sensor_code=sensor_code,
            error_type="unknown_sensor",
            message=f"device={device_code} sensor={sensor_code} not found",
            payload={"value": raw_value},
        ))
        return None

    if not sensor.is_active:
        return None

    # Insert raw
    db.add(RawReading(
        sensor_id=sensor.id,
        ts=ts_utc,
        value=raw_value,
        quality=quality,
        source=source,
        metadata_=metadata,
    ))

    # Calibrated value
    calibrated = (raw_value + sensor.calibration_offset) * sensor.calibration_scale
    delta = (calibrated - sensor.initial_baseline) if sensor.initial_baseline is not None else None

    calc = CalculatedReading(
        sensor_id=sensor.id,
        ts=ts_utc,
        value=calibrated,
        delta_from_baseline=delta,
        quality=quality,
    )
    db.add(calc)

    # Update sensor / device / site freshness
    sensor.last_reading_at = ts_utc
    device.last_heartbeat_at = ts_utc
    device.is_online = True

    site = await db.get(Site, device.site_id)
    if site:
        site.last_data_at = ts_utc
        if site.status == SiteStatus.DISCONNECTED:
            site.status = SiteStatus.NORMAL

    # Threshold evaluation
    alert: Alert | None = await evaluate_thresholds(db, sensor, calibrated, ts_utc)
    if alert and site:
        # bump site status
        if alert.severity.value == "critical":
            site.status = SiteStatus.CRITICAL
        elif site.status == SiteStatus.NORMAL:
            site.status = SiteStatus.WARNING

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        log.error("ingest.commit_failed", error=str(e), sensor=sensor_code)
        return None

    # Side effects after successful commit
    await broadcaster.broadcast_reading(
        site_id=str(device.site_id),
        sensor_id=str(sensor.id),
        ts=ts_utc.isoformat(),
        value=calibrated,
        quality=quality.value,
    )
    if alert:
        await dispatch_alert_notifications(db, alert)

    return calc


async def mark_devices_offline(db: AsyncSession, threshold_minutes: int) -> int:
    """Mark devices offline if no heartbeat in threshold_minutes. Returns count flipped."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)
    res = await db.execute(
        update(Device)
        .where(Device.is_online.is_(True), Device.last_heartbeat_at < cutoff)
        .values(is_online=False)
        .returning(Device.id)
    )
    flipped = len(list(res))
    if flipped:
        await db.commit()
    return flipped
