"""Modbus TCP polling worker.

For every Device with primary_protocol = MODBUS_TCP and at least one Sensor
with a `modbus_register_address`, this worker:

  1. Connects to the device's IP/port
  2. Reads each sensor's holding registers
  3. Decodes per `modbus_data_type`
  4. Pushes each value through `ingest_one_reading()`

Runs periodically via `scheduler.py` (default: hourly).
"""
import asyncio
import struct
from datetime import datetime, timezone

from pymodbus.client import AsyncModbusTcpClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import db_session
from app.core.logging import get_logger
from app.models.device import Device, Protocol
from app.models.reading import IngestError, IngestSource, QualityFlag
from app.models.sensor import IngestionMode, Sensor
from app.services.ingestion_service import ingest_one_reading

log = get_logger(__name__)


def _decode_registers(regs: list[int], data_type: str | None) -> float:
    """Decode raw Modbus registers (16-bit words) per data type."""
    dt = (data_type or "float32").lower()

    if dt == "float32":
        if len(regs) < 2:
            raise ValueError("float32 needs 2 registers")
        # Big-endian by default; many vendors swap. Adjust per device if needed.
        b = struct.pack(">HH", regs[0], regs[1])
        return struct.unpack(">f", b)[0]

    if dt == "int32":
        if len(regs) < 2:
            raise ValueError("int32 needs 2 registers")
        b = struct.pack(">HH", regs[0], regs[1])
        return float(struct.unpack(">i", b)[0])

    if dt == "uint32":
        b = struct.pack(">HH", regs[0], regs[1])
        return float(struct.unpack(">I", b)[0])

    if dt == "int16":
        return float(struct.unpack(">h", struct.pack(">H", regs[0]))[0])

    if dt == "uint16":
        return float(regs[0])

    raise ValueError(f"Unsupported modbus_data_type: {data_type}")


async def _poll_device(device: Device, sensors: list[Sensor]) -> None:
    if not (device.ip_address and device.port):
        log.warning("modbus.skip_no_addr", device_code=device.code)
        return

    client = AsyncModbusTcpClient(
        host=str(device.ip_address),
        port=device.port,
        timeout=settings.MODBUS_TIMEOUT_SECONDS,
        retries=settings.MODBUS_RETRIES,
    )

    try:
        connected = await client.connect()
        if not connected:
            log.warning("modbus.connect_failed", device=device.code)
            async with db_session() as db:
                db.add(IngestError(
                    source=IngestSource.MODBUS,
                    device_id=device.id,
                    error_type="connect_failed",
                    message=f"Could not connect to {device.ip_address}:{device.port}",
                    payload={"device_code": device.code},
                ))
                await db.commit()
            return

        ts = datetime.now(timezone.utc)
        unit_id = device.modbus_unit_id or 1

        for sensor in sensors:
            if sensor.modbus_register_address is None:
                continue
            try:
                rr = await client.read_holding_registers(
                    address=sensor.modbus_register_address,
                    count=sensor.modbus_register_count or 2,
                    slave=unit_id,
                )
                if rr.isError():
                    raise IOError(f"Modbus error: {rr}")
                value = _decode_registers(rr.registers, sensor.modbus_data_type)

                async with db_session() as db:
                    await ingest_one_reading(
                        db,
                        device_code=device.code,
                        sensor_code=sensor.code,
                        ts=ts,
                        raw_value=value,
                        quality=QualityFlag.GOOD,
                        source=IngestSource.MODBUS,
                        metadata={"register": sensor.modbus_register_address},
                    )
            except Exception as e:
                log.warning(
                    "modbus.read_failed",
                    device=device.code,
                    sensor=sensor.code,
                    error=str(e),
                )
                async with db_session() as db:
                    db.add(IngestError(
                        source=IngestSource.MODBUS,
                        device_id=device.id,
                        sensor_code=sensor.code,
                        error_type="read_failed",
                        message=str(e),
                        payload={"register": sensor.modbus_register_address},
                    ))
                    await db.commit()
    finally:
        client.close()


async def run_modbus_poll_cycle() -> None:
    """One cycle: enumerate active Modbus devices and poll them in parallel."""
    log.info("modbus.cycle_start")
    async with db_session() as db:
        res = await db.execute(
            select(Device)
            .options(selectinload(Device.sensors))
            .where(Device.primary_protocol == Protocol.MODBUS_TCP)
        )
        devices = res.scalars().all()

        device_sensor_pairs = [
            (
                d,
                [
                    s
                    for s in d.sensors
                    if s.is_active
                    and s.ingestion_mode == IngestionMode.MODBUS
                    and s.modbus_register_address is not None
                ],
            )
            for d in devices
        ]

    # Fan out
    tasks = [
        _poll_device(d, sensors) for d, sensors in device_sensor_pairs if sensors
    ]
    if not tasks:
        log.info("modbus.cycle_no_devices")
        return

    await asyncio.gather(*tasks, return_exceptions=True)
    log.info("modbus.cycle_done", devices=len(tasks))
