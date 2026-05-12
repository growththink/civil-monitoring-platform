"""Periodic health check — flags devices offline and creates communication alerts."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.core.config import settings
from app.core.database import db_session
from app.core.logging import get_logger
from app.models.alert import Alert, AlertCategory, AlertSeverity, AlertStatus
from app.models.device import Device
from app.models.site import Site, SiteStatus
from app.services.notification_service import dispatch_alert_notifications

log = get_logger(__name__)


async def run_health_check() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(
        minutes=settings.DEVICE_OFFLINE_THRESHOLD_MINUTES
    )

    async with db_session() as db:
        # Find devices that are currently marked online but have no recent heartbeat
        res = await db.execute(
            select(Device).where(
                Device.is_online.is_(True),
                Device.last_heartbeat_at < cutoff,
            )
        )
        going_offline = res.scalars().all()
        new_alerts: list[Alert] = []

        for d in going_offline:
            d.is_online = False
            alert = Alert(
                site_id=d.site_id,
                device_id=d.id,
                severity=AlertSeverity.WARNING,
                category=AlertCategory.DEVICE_OFFLINE,
                status=AlertStatus.OPEN,
                title=f"Device {d.code} offline",
                message=(
                    f"Device {d.code} has not sent any data in over "
                    f"{settings.DEVICE_OFFLINE_THRESHOLD_MINUTES} minutes."
                ),
            )
            db.add(alert)
            new_alerts.append(alert)

            # Bump site status
            site = await db.get(Site, d.site_id)
            if site and site.status == SiteStatus.NORMAL:
                site.status = SiteStatus.DISCONNECTED

        await db.commit()

        # Dispatch notifications
        for a in new_alerts:
            await dispatch_alert_notifications(db, a)

    if going_offline:
        log.info("health.devices_offline", count=len(going_offline))


async def run_data_missing_check() -> None:
    """Detect sensors that haven't reported data within their expected interval × 2."""
    from app.models.sensor import Sensor

    async with db_session() as db:
        sensors = (await db.execute(
            select(Sensor).where(Sensor.is_active.is_(True))
        )).scalars().all()
        new_alerts: list[Alert] = []

        for s in sensors:
            if not s.last_reading_at:
                continue
            # tolerance = 2x the expected interval
            tol = timedelta(seconds=s.expected_interval_seconds * 2)
            if datetime.now(timezone.utc) - s.last_reading_at > tol:
                # Avoid spam: only one open data_missing alert per sensor
                from sqlalchemy import select as sa_select
                existing = (await db.execute(
                    sa_select(Alert).where(
                        Alert.sensor_id == s.id,
                        Alert.category == AlertCategory.DATA_MISSING,
                        Alert.status == AlertStatus.OPEN,
                    )
                )).scalar_one_or_none()
                if existing:
                    continue

                alert = Alert(
                    site_id=s.device.site_id if s.device else None,
                    sensor_id=s.id,
                    device_id=s.device_id,
                    severity=AlertSeverity.WARNING,
                    category=AlertCategory.DATA_MISSING,
                    status=AlertStatus.OPEN,
                    title=f"Sensor {s.code} no data",
                    message=(
                        f"Sensor {s.code} expected interval is "
                        f"{s.expected_interval_seconds}s but no data for >{tol.total_seconds():.0f}s."
                    ),
                )
                db.add(alert)
                new_alerts.append(alert)

        if new_alerts:
            await db.commit()
            for a in new_alerts:
                await dispatch_alert_notifications(db, a)
            log.info("health.data_missing", count=len(new_alerts))
