"""Hourly export job — generates per-site CSV snapshots and writes to EXPORT_DIR.

Runs hourly (configurable via HOURLY_EXPORT_CRON). For each active site, queries
the last hour of `calculated_readings` for all its sensors and writes a single
wide-form CSV file.

Files are written to:
  {EXPORT_DIR}/{site_code}/{YYYY}/{MM}/{DD}/{HH}_readings.csv
"""
import csv
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import db_session
from app.core.logging import get_logger
from app.models.device import Device
from app.models.sensor import Sensor
from app.models.site import Site

log = get_logger(__name__)


async def _export_site_hourly(db: AsyncSession, site: Site, end_ts: datetime) -> Path | None:
    start_ts = end_ts - timedelta(hours=1)

    # All sensors at this site
    sensor_rows = await db.execute(
        select(Sensor.id, Sensor.code, Sensor.unit, Sensor.name)
        .join(Device, Device.id == Sensor.device_id)
        .where(Device.site_id == site.id, Sensor.is_active.is_(True))
        .order_by(Sensor.code)
    )
    sensors = list(sensor_rows.all())
    if not sensors:
        return None

    sensor_ids = [s.id for s in sensors]

    # 1-minute buckets averaged across the hour, wide form
    sql = text("""
        SELECT time_bucket('1 minute', ts) AS bucket_ts,
               sensor_id,
               AVG(value) AS value
          FROM calculated_readings
         WHERE sensor_id = ANY(:sensor_ids)
           AND ts >= :start AND ts < :end
         GROUP BY bucket_ts, sensor_id
         ORDER BY bucket_ts
    """)
    rows = (await db.execute(
        sql, {"sensor_ids": sensor_ids, "start": start_ts, "end": end_ts}
    )).all()

    if not rows:
        return None

    # Pivot in Python
    grid: dict[datetime, dict] = {}
    for r in rows:
        grid.setdefault(r.bucket_ts, {})[str(r.sensor_id)] = float(r.value)

    # Build path
    base = Path(settings.EXPORT_DIR) / site.code / f"{end_ts:%Y}" / f"{end_ts:%m}" / f"{end_ts:%d}"
    base.mkdir(parents=True, exist_ok=True)
    file_path = base / f"{end_ts:%H}_readings.csv"

    headers = ["ts"] + [f"{s.code}({s.unit})" for s in sensors]
    with file_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for ts in sorted(grid.keys()):
            row = [ts.isoformat()]
            for s in sensors:
                row.append(grid[ts].get(str(s.id), ""))
            writer.writerow(row)

    log.info(
        "export.site_done",
        site_code=site.code,
        path=str(file_path),
        sensors=len(sensors),
        rows=len(grid),
    )
    return file_path


async def run_hourly_export() -> None:
    if not settings.HOURLY_EXPORT_ENABLED:
        return
    end_ts = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    os.makedirs(settings.EXPORT_DIR, exist_ok=True)
    log.info("export.cycle_start", end_ts=end_ts.isoformat())

    async with db_session() as db:
        sites = (await db.execute(select(Site))).scalars().all()
        for site in sites:
            try:
                await _export_site_hourly(db, site, end_ts)
            except Exception as e:
                log.error("export.site_failed", site_code=site.code, error=str(e))

    log.info("export.cycle_done", sites=len(sites))
