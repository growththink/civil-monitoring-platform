"""Alert listing + acknowledge/resolve endpoints."""
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession, require_operator
from app.core.exceptions import http_404
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.user import User
from app.schemas.alert import AlertAck, AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    db: DBSession,
    user: CurrentUser,
    status_filter: AlertStatus | None = Query(None, alias="status"),
    severity: AlertSeverity | None = None,
    site_id: uuid.UUID | None = None,
    limit: int = Query(100, le=500),
):
    stmt = select(Alert).order_by(Alert.ts.desc()).limit(limit)
    if status_filter:
        stmt = stmt.where(Alert.status == status_filter)
    if severity:
        stmt = stmt.where(Alert.severity == severity)
    if site_id:
        stmt = stmt.where(Alert.site_id == site_id)

    return (await db.execute(stmt)).scalars().all()


@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    body: AlertAck,
    db: DBSession,
    user: CurrentUser,
):
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise http_404("Alert not found")
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = user.id
    if body.note:
        meta = dict(alert.metadata_ or {})
        meta["ack_note"] = body.note
        alert.metadata_ = meta
    await db.commit()
    await db.refresh(alert)
    return alert


@router.post("/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert(
    alert_id: uuid.UUID,
    db: DBSession,
    _op: Annotated[User, Depends(require_operator)],
):
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise http_404("Alert not found")
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(alert)
    return alert
