"""Demo alert publisher — drives sensors past warning then critical in 30s.

Phases (10s each, 1s tick):
  1. normal     — values inside the warning band
  2. warning    — values cross the warning threshold but stay below critical
  3. critical   — values cross the critical threshold

Run inside the backend container so it can resolve `mosquitto` by service name:

    docker compose exec backend python -m scripts.send_demo_alert
"""
import argparse
import asyncio
import json
import random
from datetime import datetime, timezone

import asyncio_mqtt as aiomqtt


# Three end-of-phase targets per sensor: (normal, warning, critical).
# Picked so that each phase visibly crosses the corresponding threshold.
SENSORS = {
    "INC-001-X": {"targets": (0.5, 1.5, 3.0),  "noise": 0.05},
    "SET-001":   {"targets": (3.0, 7.0, 12.0), "noise": 0.2},
    "PZ-001":    {"targets": (70.0, 90.0, 110.0), "noise": 0.5},
    "CR-001":    {"targets": (0.5, 1.5, 3.0),  "noise": 0.03},
    "WL-001":    {"targets": (7.0, 9.0, 11.0), "noise": 0.05},
}

PHASE_LABELS = ("normal", "warning", "critical")


def value_at(targets: tuple[float, float, float], tick: int, ticks_per_phase: int) -> tuple[float, str]:
    """Linear ramp through the three targets; returns (value, phase_label)."""
    total = ticks_per_phase * 3
    t = min(tick, total - 1)
    phase = t // ticks_per_phase
    progress = (t % ticks_per_phase) / ticks_per_phase
    start = targets[phase - 1] if phase > 0 else targets[0] * 0.5
    end = targets[phase]
    return start + (end - start) * progress, PHASE_LABELS[phase]


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="mosquitto")
    p.add_argument("--port", type=int, default=1883)
    p.add_argument("--username", default="ingest")
    p.add_argument("--password", default="ingest_pw")
    p.add_argument("--site", default="DEMO-001")
    p.add_argument("--device", default="DL-001")
    p.add_argument("--duration", type=int, default=30, help="total seconds (3 phases)")
    args = p.parse_args()

    if args.duration % 3 != 0:
        raise SystemExit("--duration must be divisible by 3 (3 equal phases)")

    ticks_per_phase = args.duration // 3
    total_ticks = ticks_per_phase * 3

    async with aiomqtt.Client(
        hostname=args.host, port=args.port,
        username=args.username, password=args.password,
    ) as client:
        print(f"[demo] connected to {args.host}:{args.port}")
        print(f"[demo] phases: normal({ticks_per_phase}s) → warning({ticks_per_phase}s) → critical({ticks_per_phase}s)")

        # Heartbeat so device is marked online
        await client.publish(
            f"sites/{args.site}/devices/{args.device}/heartbeat",
            json.dumps({
                "device_code": args.device,
                "ts": datetime.now(timezone.utc).isoformat(),
                "status": "online",
            }),
            qos=1,
        )

        for tick in range(total_ticks):
            now = datetime.now(timezone.utc).isoformat()
            phase = PHASE_LABELS[tick // ticks_per_phase]

            for code, spec in SENSORS.items():
                base, _ = value_at(spec["targets"], tick, ticks_per_phase)
                value = base + random.gauss(0, spec["noise"])

                await client.publish(
                    f"sites/{args.site}/sensors/{code}/data",
                    json.dumps({
                        "device_code": args.device,
                        "sensor_code": code,
                        "ts": now,
                        "value": round(value, 4),
                        "quality": "good",
                        "metadata": {"demo": True, "phase": phase},
                    }),
                    qos=1,
                )

            print(f"[demo] t={tick + 1:>2}s  phase={phase:<8} sent {len(SENSORS)} readings")
            if tick < total_ticks - 1:
                await asyncio.sleep(1)

        print("[demo] done — alerts should now be visible on the dashboard")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[demo] stopped")
