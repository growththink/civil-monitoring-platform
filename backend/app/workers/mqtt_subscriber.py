"""MQTT subscriber service.

Subscribes to:
  sites/+/sensors/+/data
  sites/+/devices/+/heartbeat

Payload (JSON):
{
  "device_code": "GW-001",
  "sensor_code": "INC-001-X",
  "ts": "2026-05-07T10:30:00+00:00",
  "value": 123.456,
  "quality": "good",
  "metadata": {}
}

Heartbeat:
{
  "device_code": "GW-001",
  "ts": "...",
  "status": "online"
}

Robust to disconnect — uses asyncio_mqtt with built-in reconnect via outer loop.
"""
import asyncio
import json
from datetime import datetime, timezone

import asyncio_mqtt as aiomqtt

from app.core.config import settings
from app.core.database import db_session
from app.core.logging import get_logger
from app.models.device import Device
from app.models.reading import IngestError, IngestSource, QualityFlag
from app.models.sensor import IngestionMode, Sensor
from app.services.ingestion_service import ingest_one_reading
from sqlalchemy import select

log = get_logger(__name__)

DATA_TOPIC = settings.MQTT_TOPIC_DATA
HEARTBEAT_TOPIC = settings.MQTT_TOPIC_HEARTBEAT


def _parse_topic(topic: str) -> tuple[str, str, str | None]:
    """sites/{site_id}/sensors/{sensor_code}/data → returns (kind, site_id, sensor_code)."""
    parts = topic.split("/")
    if len(parts) >= 5 and parts[0] == "sites" and parts[2] == "sensors" and parts[4] == "data":
        return ("data", parts[1], parts[3])
    if len(parts) >= 5 and parts[0] == "sites" and parts[2] == "devices" and parts[4] == "heartbeat":
        return ("heartbeat", parts[1], parts[3])
    return ("unknown", "", None)


async def _handle_data_message(topic: str, payload_bytes: bytes) -> None:
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        log.warning("mqtt.invalid_json", topic=topic, error=str(e))
        return

    device_code = payload.get("device_code")
    sensor_code = payload.get("sensor_code")
    if not (device_code and sensor_code):
        log.warning("mqtt.missing_codes", topic=topic, payload=payload)
        return

    try:
        ts_str = payload.get("ts")
        ts = datetime.fromisoformat(ts_str) if ts_str else datetime.now(timezone.utc)
        value = float(payload["value"])
        quality = QualityFlag(payload.get("quality", "good"))
    except Exception as e:
        log.warning("mqtt.invalid_payload", error=str(e), payload=payload)
        return

    async with db_session() as db:
        # Look up the sensor first so we can reject messages from non-MQTT sensors.
        # We resolve through device→sensor because sensor codes are unique-per-device.
        device = (
            await db.execute(select(Device).where(Device.code == device_code))
        ).scalar_one_or_none()
        sensor = None
        if device:
            sensor = (
                await db.execute(
                    select(Sensor).where(
                        Sensor.device_id == device.id, Sensor.code == sensor_code
                    )
                )
            ).scalar_one_or_none()

        if sensor and sensor.ingestion_mode != IngestionMode.MQTT:
            log.warning(
                "mqtt.rejected_wrong_mode",
                device=device_code,
                sensor=sensor_code,
                mode=sensor.ingestion_mode.value,
            )
            db.add(IngestError(
                source=IngestSource.MQTT,
                device_id=device.id if device else None,
                sensor_code=sensor_code,
                error_type="ingestion_mode_mismatch",
                message=(
                    f"sensor {sensor_code} has ingestion_mode="
                    f"{sensor.ingestion_mode.value}; MQTT message rejected"
                ),
                payload={"value": value, "expected": "mqtt"},
            ))
            await db.commit()
            return

        await ingest_one_reading(
            db,
            device_code=device_code,
            sensor_code=sensor_code,
            ts=ts,
            raw_value=value,
            quality=quality,
            source=IngestSource.MQTT,
            metadata=payload.get("metadata", {}),
        )


async def _handle_heartbeat(topic: str, payload_bytes: bytes) -> None:
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
        device_code = payload.get("device_code")
        if not device_code:
            return
        async with db_session() as db:
            res = await db.execute(select(Device).where(Device.code == device_code))
            device = res.scalar_one_or_none()
            if not device:
                return
            device.last_heartbeat_at = datetime.now(timezone.utc)
            device.is_online = True
            await db.commit()
    except Exception as e:
        log.warning("mqtt.heartbeat_failed", error=str(e))


async def _client_loop() -> None:
    log.info("mqtt.connecting", host=settings.MQTT_HOST, port=settings.MQTT_PORT)
    async with aiomqtt.Client(
        hostname=settings.MQTT_HOST,
        port=settings.MQTT_PORT,
        username=settings.MQTT_USERNAME,
        password=settings.MQTT_PASSWORD,
        client_id=settings.MQTT_CLIENT_ID,
        keepalive=settings.MQTT_KEEPALIVE,
    ) as client:
        log.info("mqtt.connected")
        async with client.messages() as messages:
            await client.subscribe(DATA_TOPIC, qos=settings.MQTT_QOS)
            await client.subscribe(HEARTBEAT_TOPIC, qos=settings.MQTT_QOS)
            async for message in messages:
                topic = message.topic.value
                kind, _, _ = _parse_topic(topic)
                if kind == "data":
                    asyncio.create_task(_handle_data_message(topic, message.payload))
                elif kind == "heartbeat":
                    asyncio.create_task(_handle_heartbeat(topic, message.payload))


async def run_mqtt_subscriber() -> None:
    """Outer loop — reconnect with backoff on any failure."""
    backoff = 1
    while True:
        try:
            await _client_loop()
            backoff = 1
        except aiomqtt.MqttError as e:
            log.warning("mqtt.disconnected", error=str(e), retry_in=backoff)
        except Exception as e:
            log.error("mqtt.unexpected", error=str(e), retry_in=backoff)
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60)
