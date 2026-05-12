"""APScheduler — orchestrates the periodic background jobs.

Jobs (defaults):
  * Modbus poll            (cron from system_settings.measurement_interval_minutes,
                             defaults to '0 * * * *')
  * Hourly CSV export       (cron: '5 * * * *')
  * 5-minute health check   (cron: '*/5 * * * *')
  * 10-minute data-missing  (cron: '*/10 * * * *')
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.logging import get_logger
from app.services.settings_service import cron_from_minutes, get_measurement_interval_minutes
from app.workers.health_check import run_data_missing_check, run_health_check
from app.workers.hourly_export import run_hourly_export
from app.workers.modbus_poller import run_modbus_poll_cycle

log = get_logger(__name__)
scheduler = AsyncIOScheduler(timezone=settings.APP_TIMEZONE)

MODBUS_JOB_ID = "modbus_poll"


def _trigger(cron: str) -> CronTrigger:
    return CronTrigger.from_crontab(cron, timezone=settings.APP_TIMEZONE)


async def _resolve_modbus_cron() -> str:
    """Read measurement_interval_minutes from system_settings → cron string."""
    minutes = await get_measurement_interval_minutes()
    return cron_from_minutes(minutes)


async def configure_scheduler() -> AsyncIOScheduler:
    """Register all jobs on the singleton scheduler."""

    modbus_cron = await _resolve_modbus_cron()
    scheduler.add_job(
        run_modbus_poll_cycle,
        trigger=_trigger(modbus_cron),
        id=MODBUS_JOB_ID,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
        replace_existing=True,
    )

    scheduler.add_job(
        run_hourly_export,
        trigger=_trigger(settings.HOURLY_EXPORT_CRON),
        id="hourly_export",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=600,
        replace_existing=True,
    )

    scheduler.add_job(
        run_health_check,
        trigger=_trigger(settings.HEALTH_CHECK_CRON),
        id="health_check",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )

    scheduler.add_job(
        run_data_missing_check,
        trigger=CronTrigger(minute="*/10", timezone=settings.APP_TIMEZONE),
        id="data_missing_check",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )

    log.info(
        "scheduler.configured",
        jobs=[j.id for j in scheduler.get_jobs()],
        modbus_cron=modbus_cron,
        export_cron=settings.HOURLY_EXPORT_CRON,
    )
    return scheduler


async def reschedule_modbus_poll() -> str:
    """Reread system_settings and rebuild the modbus poll trigger. Returns the new cron."""
    modbus_cron = await _resolve_modbus_cron()
    if scheduler.running:
        scheduler.reschedule_job(MODBUS_JOB_ID, trigger=_trigger(modbus_cron))
    log.info("scheduler.modbus_rescheduled", cron=modbus_cron)
    return modbus_cron
