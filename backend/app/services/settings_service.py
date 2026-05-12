"""Helpers for reading/writing key/value system settings."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import db_session
from app.models.system_settings import (
    DEFAULT_MEASUREMENT_INTERVAL,
    MEASUREMENT_INTERVAL_KEY,
    SystemSetting,
)


async def get_setting(db: AsyncSession, key: str, default: str | None = None) -> str | None:
    res = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    row = res.scalar_one_or_none()
    return row.value if row else default


async def set_setting(db: AsyncSession, key: str, value: str) -> SystemSetting:
    row = await db.get(SystemSetting, key)
    if row is None:
        row = SystemSetting(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    await db.commit()
    await db.refresh(row)
    return row


async def get_measurement_interval_minutes() -> int:
    """Read measurement_interval_minutes from DB. Falls back to default on any error."""
    async with db_session() as db:
        try:
            raw = await get_setting(db, MEASUREMENT_INTERVAL_KEY, DEFAULT_MEASUREMENT_INTERVAL)
        except Exception:
            raw = DEFAULT_MEASUREMENT_INTERVAL
    try:
        v = int(raw or DEFAULT_MEASUREMENT_INTERVAL)
    except ValueError:
        v = int(DEFAULT_MEASUREMENT_INTERVAL)
    return max(1, min(v, 1440))


def cron_from_minutes(minutes: int) -> str:
    """Translate an interval-in-minutes into a 5-field cron expression.

    - 60 (or any divisor of 60 from 1..60 that equals 60) => `0 * * * *`
    - other values <= 60 => `*/N * * * *`
    - >60 => fall back to running once per N minutes via `*/N` (capped at 59 in cron)
    """
    if minutes <= 0:
        minutes = 1
    if minutes >= 60:
        # >= 60 minutes: run at minute 0 every hour (hour-precision)
        return "0 * * * *"
    return f"*/{minutes} * * * *"
