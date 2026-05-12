"""Threshold evaluation: turns readings into alerts."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.alert import Alert, AlertCategory, AlertSeverity, AlertStatus
from app.models.sensor import Sensor, ThresholdLevel

log = get_logger(__name__)


def _exceeds(value: float, min_v: float | None, max_v: float | None) -> bool:
    if min_v is not None and value < min_v:
        return True
    if max_v is not None and value > max_v:
        return True
    return False


async def evaluate_thresholds(
    db: AsyncSession,
    sensor: Sensor,
    value: float,
    ts: datetime,
) -> Alert | None:
    """Return new Alert (already added to session) if a threshold is breached."""
    if not sensor.thresholds:
        return None

    # Load device for site_id
    device_id = sensor.device_id
    site_id = None
    if sensor.device:
        site_id = sensor.device.site_id
    else:
        # fetch lazily
        from app.models.device import Device
        d = await db.get(Device, device_id)
        if d:
            site_id = d.site_id
    if site_id is None:
        return None

    breached_level: ThresholdLevel | None = None
    breached_threshold: float | None = None

    # Critical takes precedence
    for level in (ThresholdLevel.CRITICAL, ThresholdLevel.WARNING):
        for th in sensor.thresholds:
            if th.level == level and th.is_active and _exceeds(value, th.min_value, th.max_value):
                breached_level = level
                breached_threshold = (
                    th.max_value if (th.max_value is not None and value > th.max_value) else th.min_value
                )
                break
        if breached_level:
            break

    if not breached_level:
        return None

    severity = (
        AlertSeverity.CRITICAL if breached_level == ThresholdLevel.CRITICAL else AlertSeverity.WARNING
    )
    alert = Alert(
        ts=ts.astimezone(timezone.utc),
        site_id=site_id,
        sensor_id=sensor.id,
        device_id=device_id,
        severity=severity,
        category=AlertCategory.THRESHOLD,
        status=AlertStatus.OPEN,
        title=f"{sensor.name} {breached_level.value.upper()} threshold breach",
        message=(
            f"Sensor {sensor.code} value {value:.4f} {sensor.unit} "
            f"breached {breached_level.value} threshold ({breached_threshold})."
        ),
        triggered_value=value,
        threshold_value=breached_threshold,
        notified=False,
    )
    db.add(alert)
    log.info(
        "threshold.breach",
        sensor_id=str(sensor.id),
        level=breached_level.value,
        value=value,
        threshold=breached_threshold,
    )
    return alert


async def load_sensor_with_thresholds(db: AsyncSession, sensor_id) -> Sensor | None:
    res = await db.execute(
        select(Sensor)
        .options(selectinload(Sensor.thresholds), selectinload(Sensor.device))
        .where(Sensor.id == sensor_id)
    )
    return res.scalar_one_or_none()
