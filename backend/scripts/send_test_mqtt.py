"""MQTT test publisher — simulates a gateway sending data.

Usage:
    python -m scripts.send_test_mqtt --site DEMO-001 --device DL-001 --interval 5

Sends randomized but realistic readings for the seeded sensors every N seconds.
"""
import argparse
import asyncio
import json
import random
from datetime import datetime, timezone

import asyncio_mqtt as aiomqtt


SENSORS = {
    "INC-001-X": {"base": 0.0, "noise": 0.3, "drift": 0.001},
    "SET-001":   {"base": -2.0, "noise": 0.5, "drift": -0.01},
    "PZ-001":    {"base": 55.0, "noise": 1.5, "drift": 0.02},
    "CR-001":    {"base": 0.2, "noise": 0.05, "drift": 0.0005},
    "WL-001":    {"base": 5.5, "noise": 0.1, "drift": 0.0},
}


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=1883)
    p.add_argument("--username", default="ingest")
    p.add_argument("--password", default="ingest_pw")
    p.add_argument("--site", default="DEMO-001",
                   help="Site code; used as topic site segment")
    p.add_argument("--device", default="DL-001")
    p.add_argument("--interval", type=float, default=5.0)
    args = p.parse_args()

    # Track per-sensor cumulative drift
    state = {k: v["base"] for k, v in SENSORS.items()}

    async with aiomqtt.Client(
        hostname=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
    ) as client:
        print(f"[pub] connected to {args.host}:{args.port}")
        # Heartbeat
        hb_topic = f"sites/{args.site}/devices/{args.device}/heartbeat"
        tick = 0
        while True:
            now = datetime.now(timezone.utc).isoformat()

            # Heartbeat every 10 cycles
            if tick % 10 == 0:
                await client.publish(
                    hb_topic,
                    json.dumps({"device_code": args.device, "ts": now, "status": "online"}),
                    qos=1,
                )

            for sensor_code, spec in SENSORS.items():
                # Apply drift + noise
                state[sensor_code] += spec["drift"]
                value = state[sensor_code] + random.gauss(0, spec["noise"])

                topic = f"sites/{args.site}/sensors/{sensor_code}/data"
                payload = {
                    "device_code": args.device,
                    "sensor_code": sensor_code,
                    "ts": now,
                    "value": round(value, 4),
                    "quality": "good",
                    "metadata": {"sim": True},
                }
                await client.publish(topic, json.dumps(payload), qos=1)

            print(f"[pub] {now} sent {len(SENSORS)} readings")
            tick += 1
            await asyncio.sleep(args.interval)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[pub] stopped")
