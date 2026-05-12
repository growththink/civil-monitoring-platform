"""Site CRUD + summary endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DBSession, require_admin, require_operator
from app.core.exceptions import http_403, http_404, http_409
from app.models.alert import Alert, AlertStatus
from app.models.device import Device
from app.models.sensor import Sensor
from app.models.site import Site
from app.models.user import User, UserRole, UserSiteAccess
from app.schemas.site import SiteCreate, SiteOut, SiteSummary, SiteUpdate

router = APIRouter(prefix="/sites", tags=["sites"])


async def _user_can_view_site(db, user: User, site_id: uuid.UUID) -> bool:
    if user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.OPERATOR):
        return True
    res = await db.execute(
        select(UserSiteAccess).where(
            UserSiteAccess.user_id == user.id,
            UserSiteAccess.site_id == site_id,
        )
    )
    return res.scalar_one_or_none() is not None


@router.get("", response_model=list[SiteSummary])
async def list_sites(db: DBSession, user: CurrentUser):
    """List sites with summary info; clients only see assigned sites."""
    base = select(Site)
    if user.role == UserRole.CLIENT:
        base = base.join(UserSiteAccess, UserSiteAccess.site_id == Site.id).where(
            UserSiteAccess.user_id == user.id
        )

    sites = (await db.execute(base.order_by(Site.name))).scalars().all()

    summaries: list[SiteSummary] = []
    for s in sites:
        sensor_count = (
            await db.execute(
                select(func.count(Sensor.id))
                .join(Device, Device.id == Sensor.device_id)
                .where(Device.site_id == s.id, Sensor.is_active.is_(True))
            )
        ).scalar_one()
        online_devices = (
            await db.execute(
                select(func.count(Device.id)).where(
                    Device.site_id == s.id, Device.is_online.is_(True)
                )
            )
        ).scalar_one()
        open_alerts = (
            await db.execute(
                select(func.count(Alert.id)).where(
                    Alert.site_id == s.id, Alert.status == AlertStatus.OPEN
                )
            )
        ).scalar_one()
        summaries.append(
            SiteSummary(
                id=s.id,
                code=s.code,
                name=s.name,
                status=s.status,
                latitude=s.latitude,
                longitude=s.longitude,
                sensor_count=sensor_count,
                online_device_count=online_devices,
                open_alerts=open_alerts,
                last_data_at=s.last_data_at,
            )
        )
    return summaries


@router.post("", response_model=SiteOut, status_code=status.HTTP_201_CREATED)
async def create_site(
    body: SiteCreate,
    db: DBSession,
    _admin: Annotated[User, Depends(require_admin)],
):
    site = Site(**body.model_dump(by_alias=False, exclude={"metadata"}), metadata_=body.metadata)
    db.add(site)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise http_409("Site code already exists")
    await db.refresh(site)
    return site


@router.get("/{site_id}", response_model=SiteOut)
async def get_site(site_id: uuid.UUID, db: DBSession, user: CurrentUser):
    site = await db.get(Site, site_id)
    if not site:
        raise http_404("Site not found")
    if not await _user_can_view_site(db, user, site_id):
        raise http_403()
    return site


@router.patch("/{site_id}", response_model=SiteOut)
async def update_site(
    site_id: uuid.UUID,
    body: SiteUpdate,
    db: DBSession,
    _op: Annotated[User, Depends(require_operator)],
):
    site = await db.get(Site, site_id)
    if not site:
        raise http_404("Site not found")
    data = body.model_dump(exclude_unset=True)
    if "metadata" in data:
        site.metadata_ = data.pop("metadata")
    for k, v in data.items():
        setattr(site, k, v)
    await db.commit()
    await db.refresh(site)
    return site


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    site_id: uuid.UUID,
    db: DBSession,
    _admin: Annotated[User, Depends(require_admin)],
):
    site = await db.get(Site, site_id)
    if not site:
        raise http_404("Site not found")
    await db.delete(site)
    await db.commit()
