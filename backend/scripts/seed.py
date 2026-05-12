"""Seed script — bootstraps the DB with:
  - 1 super_admin user (email/password from env or default)
  - 1 demo site (DEMO-001)
  - 1 datalogger device (DL-001) with API key printed
  - 5 sensors (inclinometer, settlement, piezometer, crack, water_level)
  - threshold rules per sensor

Run via:
    python -m scripts.seed
"""
import asyncio
import os

from sqlalchemy import select

from app.core.database import db_session
from app.core.security import generate_device_api_key, hash_password
from app.models.device import Device, DeviceType, Protocol
from app.models.sensor import (
    IngestionMode,
    Sensor,
    SensorThreshold,
    SensorType,
    ThresholdLevel,
)
from app.models.system_settings import (
    DEFAULT_MEASUREMENT_INTERVAL,
    MEASUREMENT_INTERVAL_KEY,
    SystemSetting,
)
from app.models.site import Site
from app.models.user import User, UserRole

ADMIN_EMAIL = os.environ.get("SEED_ADMIN_EMAIL", "admin@civil-monitoring.local")
ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "ChangeMe!2026")


async def seed():
    async with db_session() as db:
        # Admin user
        admin = (
            await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        ).scalar_one_or_none()
        if not admin:
            admin = User(
                email=ADMIN_EMAIL,
                password_hash=hash_password(ADMIN_PASSWORD),
                name="Super Admin",
                role=UserRole.SUPER_ADMIN,
            )
            db.add(admin)
            await db.flush()
            print(f"[seed] admin created: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        else:
            print(f"[seed] admin already exists: {ADMIN_EMAIL}")

        # Demo site
        site = (
            await db.execute(select(Site).where(Site.code == "DEMO-001"))
        ).scalar_one_or_none()
        if not site:
            site = Site(
                code="DEMO-001",
                name="Demo Construction Site",
                address="Seoul, Korea",
                latitude=37.5665,
                longitude=126.9780,
                manager_user_id=admin.id,
            )
            db.add(site)
            await db.flush()
            print(f"[seed] site created: {site.code}")

        # Demo device with new API key
        device = (
            await db.execute(
                select(Device).where(Device.site_id == site.id, Device.code == "DL-001")
            )
        ).scalar_one_or_none()
        if not device:
            plain_key, hashed = generate_device_api_key()
            device = Device(
                site_id=site.id,
                code="DL-001",
                name="Datalogger 1",
                serial_number="SN-DL-2026-001",
                device_type=DeviceType.DATALOGGER,
                primary_protocol=Protocol.MQTT,
                api_key_hash=hashed,
            )
            db.add(device)
            await db.flush()
            print(f"[seed] device created: {device.code}")
            print(f"[seed] >>> DEVICE_API_KEY (save this!) = {plain_key}")

        # Sensors
        sensor_specs = [
            {
                "code": "INC-001-X",
                "name": "Inclinometer 1 (X-axis)",
                "type": SensorType.INCLINOMETER,
                "unit": "degree",
                "baseline": 0.0,
                "thresholds": [
                    (ThresholdLevel.WARNING, -1.0, 1.0),
                    (ThresholdLevel.CRITICAL, -2.5, 2.5),
                ],
            },
            {
                "code": "SET-001",
                "name": "Settlement Gauge 1",
                "type": SensorType.SETTLEMENT,
                "unit": "mm",
                "baseline": 0.0,
                "thresholds": [
                    (ThresholdLevel.WARNING, -20.0, 5.0),
                    (ThresholdLevel.CRITICAL, -40.0, 10.0),
                ],
            },
            {
                "code": "PZ-001",
                "name": "Piezometer 1",
                "type": SensorType.PIEZOMETER,
                "unit": "kPa",
                "baseline": 50.0,
                "thresholds": [
                    (ThresholdLevel.WARNING, None, 80.0),
                    (ThresholdLevel.CRITICAL, None, 100.0),
                ],
            },
            {
                "code": "CR-001",
                "name": "Crack Gauge 1",
                "type": SensorType.CRACK,
                "unit": "mm",
                "baseline": 0.0,
                "thresholds": [
                    (ThresholdLevel.WARNING, None, 1.0),
                    (ThresholdLevel.CRITICAL, None, 2.5),
                ],
            },
            {
                "code": "WL-001",
                "name": "Water Level 1",
                "type": SensorType.WATER_LEVEL,
                "unit": "m",
                "baseline": 5.0,
                "thresholds": [
                    (ThresholdLevel.WARNING, 2.0, 8.0),
                    (ThresholdLevel.CRITICAL, 1.0, 10.0),
                ],
            },
        ]

        for spec in sensor_specs:
            existing = (
                await db.execute(
                    select(Sensor).where(
                        Sensor.device_id == device.id,
                        Sensor.code == spec["code"],
                    )
                )
            ).scalar_one_or_none()
            if existing:
                continue
            s = Sensor(
                device_id=device.id,
                code=spec["code"],
                name=spec["name"],
                sensor_type=spec["type"],
                unit=spec["unit"],
                ingestion_mode=IngestionMode.MQTT,
                initial_baseline=spec["baseline"],
                expected_interval_seconds=3600,
            )
            for level, mn, mx in spec["thresholds"]:
                s.thresholds.append(
                    SensorThreshold(level=level, min_value=mn, max_value=mx)
                )
            db.add(s)

        # Global settings
        existing_setting = await db.get(SystemSetting, MEASUREMENT_INTERVAL_KEY)
        if not existing_setting:
            db.add(SystemSetting(
                key=MEASUREMENT_INTERVAL_KEY,
                value=DEFAULT_MEASUREMENT_INTERVAL,
            ))
            print(f"[seed] system_setting created: {MEASUREMENT_INTERVAL_KEY}={DEFAULT_MEASUREMENT_INTERVAL}")

        await db.commit()
        print("[seed] sensors + thresholds ensured")
        print("\n[seed] Done.")


if __name__ == "__main__":
    asyncio.run(seed())
