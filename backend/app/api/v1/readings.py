"""Time-series query endpoints (raw + downsampled)."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DBSession, require_operator
from app.core.exceptions import http_400, http_404
from app.models.sensor import Sensor
from app.models.user import User
from app.schemas.reading import TimeSeriesPoint, TimeSeriesResponse

router = APIRouter(prefix="/readings", tags=["readings"])


_INTERVAL_PRESETS: dict[str, timedelta] = {
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


def _parse_window(window: str | None, from_ts: datetime | None, to_ts: datetime | None):
    now = datetime.now(timezone.utc)
    if window:
        if window not in _INTERVAL_PRESETS:
            raise http_400(f"Invalid window. Allowed: {','.join(_INTERVAL_PRESETS)}")
        return now - _INTERVAL_PRESETS[window], now
    if not from_ts or not to_ts:
        raise http_400("Provide either window or from_ts/to_ts")
    if from_ts >= to_ts:
        raise http_400("from_ts must be before to_ts")
    return from_ts, to_ts


def _bucket_for(span: timedelta) -> str:
    total_seconds = span.total_seconds()
    if total_seconds <= 3600:
        return "1 minute"
    if total_seconds <= 86400:
        return "5 minutes"
    if total_seconds <= 7 * 86400:
        return "30 minutes"
    return "2 hours"


@router.get("/{sensor_id}", response_model=TimeSeriesResponse)
async def get_readings(
    sensor_id: uuid.UUID,
    db: DBSession,
    user: CurrentUser,
    window: str | None = Query(None, description="1h | 24h | 7d | 30d"),
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    downsample: bool = True,
):
    sensor = await db.get(Sensor, sensor_id)
    if not sensor:
        raise http_404("Sensor not found")

    start, end = _parse_window(window, from_ts, to_ts)

    if downsample and (end - start).total_seconds() > 3600:
        bucket = _bucket_for(end - start)
        sql = text(f"""
            SELECT time_bucket(:bucket, ts) AS bucket_ts,
                   AVG(value) AS value
              FROM calculated_readings
             WHERE sensor_id = :sid AND ts >= :start AND ts < :end
             GROUP BY bucket_ts
             ORDER BY bucket_ts
        """)
        rows = await db.execute(sql, {"bucket": bucket, "sid": sensor_id, "start": start, "end": end})
        points = [TimeSeriesPoint(ts=r.bucket_ts, value=float(r.value)) for r in rows]
    else:
        sql = text("""
            SELECT ts, value, quality::text AS quality
              FROM calculated_readings
             WHERE sensor_id = :sid AND ts >= :start AND ts < :end
             ORDER BY ts
        """)
        rows = await db.execute(sql, {"sid": sensor_id, "start": start, "end": end})
        from app.models.reading import QualityFlag
        points = [
            TimeSeriesPoint(ts=r.ts, value=float(r.value), quality=QualityFlag(r.quality))
            for r in rows
        ]

    return TimeSeriesResponse(sensor_id=sensor_id, points=points, count=len(points))


@router.get("/{sensor_id}/export.csv")
async def export_readings_csv(
    sensor_id: uuid.UUID,
    db: DBSession,
    user: CurrentUser,
    from_ts: datetime,
    to_ts: datetime,
):
    sensor = await db.get(Sensor, sensor_id)
    if not sensor:
        raise http_404("Sensor not found")

    sql = text("""
        SELECT ts, value, quality::text AS quality
          FROM calculated_readings
         WHERE sensor_id = :sid AND ts >= :start AND ts < :end
         ORDER BY ts
    """)
    rows = await db.execute(sql, {"sid": sensor_id, "start": from_ts, "end": to_ts})

    def _stream():
        yield "ts,value,quality,unit\n"
        for r in rows:
            yield f"{r.ts.isoformat()},{r.value},{r.quality},{sensor.unit}\n"

    filename = f"sensor-{sensor.code}-{from_ts.date()}-to-{to_ts.date()}.csv"
    return StreamingResponse(
        _stream(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
