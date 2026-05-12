# MQTT Payload Reference

## Topic structure

```
sites/{site_code}/sensors/{sensor_code}/data
sites/{site_code}/devices/{device_code}/heartbeat
```

The backend subscribes to (with QoS 1):
- `sites/+/sensors/+/data`
- `sites/+/devices/+/heartbeat`

The `site_code` segment is informational only — actual routing is by
`device_code` + `sensor_code` in the JSON body, which must match records in
the `devices` and `sensors` tables.

## Sensor reading payload

```json
{
  "device_code": "DL-001",
  "sensor_code": "INC-001-X",
  "ts": "2026-05-08T10:30:00+00:00",
  "value": 0.342,
  "quality": "good",
  "metadata": {
    "battery_v": 3.78,
    "signal_db": -67
  }
}
```

| Field        | Required | Notes |
|--------------|----------|-------|
| device_code  | yes      | Must match `devices.code` |
| sensor_code  | yes      | Must match `sensors.code` (unique within device) |
| ts           | yes      | ISO 8601 with timezone, UTC recommended |
| value        | yes      | Raw value (calibration applied server-side) |
| quality      | no       | `good` (default), `suspect`, `bad`, `missing` |
| metadata     | no       | Free-form JSON, stored as-is on raw_readings.metadata |

## Heartbeat payload

```json
{
  "device_code": "DL-001",
  "ts": "2026-05-08T10:30:00+00:00",
  "status": "online"
}
```

The backend updates `devices.last_heartbeat_at` and sets `is_online = true`.
Devices that don't heartbeat within `DEVICE_OFFLINE_THRESHOLD_MINUTES` (default
15) get flagged offline by the health-check job and trigger a `device_offline`
alert.

## Recommended publish frequency

| Sensor type                | Interval |
|----------------------------|----------|
| Inclinometer / settlement  | 1 hour   |
| Piezometer                 | 30 min   |
| Crack gauge                | 1 hour   |
| Vibration / GNSS           | 5 min    |
| Heartbeat                  | 5 min    |

For sensors set `expected_interval_seconds` to **2× the publish interval** —
the data-missing checker uses 2× as its tolerance.

## Authentication

Mosquitto requires username/password for all clients:
- Backend subscriber: `ingest` / `<MQTT_PASSWORD>`
- Each gateway: dedicated `device_<code>` / strong password
- ACL recommendation in production: restrict each device to publishing only
  to `sites/{site_code}/sensors/+/data` and `sites/{site_code}/devices/{device_code}/heartbeat`

## Test publisher

```bash
python -m scripts.send_test_mqtt \
  --host localhost --port 1883 \
  --username ingest --password ingest_pw \
  --site DEMO-001 --device DL-001 \
  --interval 5
```

## Gateway buffering recommendation

Field LTE links are unreliable. Gateways should:
1. Persist outgoing messages to a local SQLite/file buffer
2. Send with QoS 1 and `retain = false`
3. Drop only on broker `PUBACK` (mosquitto handles this automatically with QoS 1)
4. On reconnect, replay the queue oldest-first

The backend's idempotent ingestion (PK on `(sensor_id, ts)`) makes replays safe.
