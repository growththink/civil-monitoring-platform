"""Global system settings endpoints (admin only)."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import DBSession, require_admin
from app.core.exceptions import http_400, http_404
from app.core.logging import get_logger
from app.models.system_settings import MEASUREMENT_INTERVAL_KEY, SystemSetting
from app.models.user import User
from app.schemas.system_settings import SystemSettingOut, SystemSettingUpdate
from app.services.settings_service import set_setting

router = APIRouter(prefix="/settings", tags=["settings"])
log = get_logger(__name__)


@router.get("", response_model=list[SystemSettingOut])
async def list_settings(
    db: DBSession,
    _admin: Annotated[User, Depends(require_admin)],
):
    res = await db.execute(select(SystemSetting).order_by(SystemSetting.key))
    return list(res.scalars().all())


@router.patch("/{key}", response_model=SystemSettingOut)
async def update_setting(
    key: str,
    body: SystemSettingUpdate,
    db: DBSession,
    _admin: Annotated[User, Depends(require_admin)],
):
    # Reject keys we don't recognise. Keeps the surface small for now.
    if key != MEASUREMENT_INTERVAL_KEY:
        raise http_404(f"Unknown setting: {key}")

    if key == MEASUREMENT_INTERVAL_KEY:
        try:
            v = int(body.value)
        except ValueError:
            raise http_400("measurement_interval_minutes must be an integer")
        if v < 1 or v > 1440:
            raise http_400("measurement_interval_minutes must be in [1, 1440]")

    row = await set_setting(db, key, body.value)
    log.info("settings.updated", key=key, value=body.value)

    # Reschedule any jobs that depend on this setting
    if key == MEASUREMENT_INTERVAL_KEY:
        try:
            from app.workers.scheduler import reschedule_modbus_poll
            await reschedule_modbus_poll()
        except Exception as e:
            log.warning("settings.reschedule_failed", error=str(e))

    return row
