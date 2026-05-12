"""Device CRUD endpoints. API key returned only at creation."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DBSession, require_admin, require_operator
from app.core.exceptions import http_404, http_409
from app.core.security import generate_device_api_key
from app.models.device import Device
from app.models.user import User
from app.schemas.device import (
    DeviceCreate,
    DeviceCreatedResponse,
    DeviceOut,
    DeviceUpdate,
)

router = APIRouter(prefix="/devices", tags=["devices"])


def _to_created_response(device: Device, plain_key: str) -> DeviceCreatedResponse:
    return DeviceCreatedResponse(
        id=device.id,
        site_id=device.site_id,
        code=device.code,
        name=device.name,
        serial_number=device.serial_number,
        device_type=device.device_type,
        primary_protocol=device.primary_protocol,
        ip_address=str(device.ip_address) if device.ip_address else None,
        port=device.port,
        modbus_unit_id=device.modbus_unit_id,
        config=device.config,
        last_heartbeat_at=device.last_heartbeat_at,
        is_online=device.is_online,
        created_at=device.created_at,
        api_key=plain_key,
    )


@router.get("", response_model=list[DeviceOut])
async def list_devices(
    db: DBSession,
    _op: Annotated[User, Depends(require_operator)],
    site_id: uuid.UUID | None = None,
):
    stmt = select(Device).order_by(Device.name)
    if site_id:
        stmt = stmt.where(Device.site_id == site_id)
    return (await db.execute(stmt)).scalars().all()


@router.post("", response_model=DeviceCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    body: DeviceCreate,
    db: DBSession,
    _admin: Annotated[User, Depends(require_admin)],
):
    plain_key, hashed = generate_device_api_key()
    device = Device(**body.model_dump(), api_key_hash=hashed)
    db.add(device)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise http_409("Device code already exists for this site")
    await db.refresh(device)
    return _to_created_response(device, plain_key)


@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(
    device_id: uuid.UUID,
    db: DBSession,
    _op: Annotated[User, Depends(require_operator)],
):
    device = await db.get(Device, device_id)
    if not device:
        raise http_404("Device not found")
    return device


@router.patch("/{device_id}", response_model=DeviceOut)
async def update_device(
    device_id: uuid.UUID,
    body: DeviceUpdate,
    db: DBSession,
    _admin: Annotated[User, Depends(require_admin)],
):
    device = await db.get(Device, device_id)
    if not device:
        raise http_404("Device not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(device, k, v)
    await db.commit()
    await db.refresh(device)
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: uuid.UUID,
    db: DBSession,
    _admin: Annotated[User, Depends(require_admin)],
):
    device = await db.get(Device, device_id)
    if not device:
        raise http_404("Device not found")
    await db.delete(device)
    await db.commit()


@router.post("/{device_id}/rotate-key", response_model=DeviceCreatedResponse)
async def rotate_device_key(
    device_id: uuid.UUID,
    db: DBSession,
    _admin: Annotated[User, Depends(require_admin)],
):
    device = await db.get(Device, device_id)
    if not device:
        raise http_404("Device not found")
    plain_key, hashed = generate_device_api_key()
    device.api_key_hash = hashed
    await db.commit()
    await db.refresh(device)
    return _to_created_response(device, plain_key)
