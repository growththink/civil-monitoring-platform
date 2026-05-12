"""Sensor CRUD + threshold management endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession, require_admin, require_operator
from app.core.exceptions import http_404, http_409
from app.models.sensor import Sensor, SensorThreshold
from app.models.user import User
from app.schemas.sensor import (
    SensorCreate,
    SensorOut,
    SensorUpdate,
    ThresholdIn,
    ThresholdOut,
)

router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.get("", response_model=list[SensorOut])
async def list_sensors(
    db: DBSession,
    _op: Annotated[User, Depends(require_operator)],
    device_id: uuid.UUID | None = None,
):
    stmt = select(Sensor).options(selectinload(Sensor.thresholds)).order_by(Sensor.name)
    if device_id:
        stmt = stmt.where(Sensor.device_id == device_id)
    return (await db.execute(stmt)).scalars().all()


@router.post("", response_model=SensorOut, status_code=status.HTTP_201_CREATED)
async def create_sensor(
    body: SensorCreate,
    db: DBSession,
    _admin: Annotated[User, Depends(require_admin)],
):
    payload = body.model_dump(exclude={"thresholds", "metadata"})
    sensor = Sensor(**payload, metadata_=body.metadata)
    for t in body.thresholds:
        sensor.thresholds.append(
            SensorThreshold(level=t.level, min_value=t.min_value, max_value=t.max_value)
        )
    db.add(sensor)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise http_409("Sensor code already exists for this device")
    await db.refresh(sensor, attribute_names=["thresholds"])
    return sensor


@router.get("/{sensor_id}", response_model=SensorOut)
async def get_sensor(
    sensor_id: uuid.UUID,
    db: DBSession,
    _op: Annotated[User, Depends(require_operator)],
):
    stmt = select(Sensor).options(selectinload(Sensor.thresholds)).where(Sensor.id == sensor_id)
    sensor = (await db.execute(stmt)).scalar_one_or_none()
    if not sensor:
        raise http_404("Sensor not found")
    return sensor


@router.patch("/{sensor_id}", response_model=SensorOut)
async def update_sensor(
    sensor_id: uuid.UUID,
    body: SensorUpdate,
    db: DBSession,
    _admin: Annotated[User, Depends(require_admin)],
):
    sensor = await db.get(Sensor, sensor_id)
    if not sensor:
        raise http_404("Sensor not found")
    data = body.model_dump(exclude_unset=True)
    if "metadata" in data:
        sensor.metadata_ = data.pop("metadata")
    for k, v in data.items():
        setattr(sensor, k, v)
    await db.commit()
    await db.refresh(sensor, attribute_names=["thresholds"])
    return sensor


@router.delete("/{sensor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sensor(
    sensor_id: uuid.UUID,
    db: DBSession,
    _admin: Annotated[User, Depends(require_admin)],
):
    sensor = await db.get(Sensor, sensor_id)
    if not sensor:
        raise http_404("Sensor not found")
    await db.delete(sensor)
    await db.commit()


@router.post(
    "/{sensor_id}/thresholds",
    response_model=ThresholdOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_threshold(
    sensor_id: uuid.UUID,
    body: ThresholdIn,
    db: DBSession,
    _admin: Annotated[User, Depends(require_admin)],
):
    sensor = await db.get(Sensor, sensor_id)
    if not sensor:
        raise http_404("Sensor not found")
    th = SensorThreshold(
        sensor_id=sensor_id,
        level=body.level,
        min_value=body.min_value,
        max_value=body.max_value,
    )
    db.add(th)
    await db.commit()
    await db.refresh(th)
    return th


@router.delete("/thresholds/{threshold_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_threshold(
    threshold_id: uuid.UUID,
    db: DBSession,
    _admin: Annotated[User, Depends(require_admin)],
):
    th = await db.get(SensorThreshold, threshold_id)
    if not th:
        raise http_404("Threshold not found")
    await db.delete(th)
    await db.commit()
