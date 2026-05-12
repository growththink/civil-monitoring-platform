# Architecture

## High-level

```
                       ┌──── Field site ────┐
Sensors ─RS485/4-20mA─▶│ Datalogger / PLC   │
                       │ ─Modbus RTU──────▶ │
                       │ Industrial LTE/5G  │
                       │ router (gateway)   │
                       └──┬──────────┬──────┘
                          │          │
                  MQTT/TLS │  HTTPS  │ Modbus TCP
                          ▼          ▼
                  ┌─────────────────────────────┐
                  │  Cloud (Docker Compose)     │
                  │                             │
                  │  Mosquitto ─▶ MQTT subscriber│
                  │              (background)   │
                  │                ▼            │
                  │            FastAPI ─▶ Postgres+TS │
                  │              ▲              │
                  │  APScheduler─┤              │
                  │   (hourly poll, export)     │
                  │              ▼              │
                  │  WebSocket → Next.js dashboard │
                  └─────────────────────────────┘
```

## Key design decisions

### 1. Single Postgres + TimescaleDB
We chose TimescaleDB hypertables for `raw_readings` and `calculated_readings`
instead of a dedicated TSDB (InfluxDB). Reasons:
- Relational data (sites, sensors, users, thresholds) is just as important
  as time-series; one DB simplifies operations and JOINs.
- TimescaleDB compression policy at 30 days saves >90% on disk for raw data.
- Standard SQL — Grafana, BI tools, Pandas all just work.

Hypertable chunk interval: **7 days**. Compression segmentby: `sensor_id`.
Retention: drop raw data after **2 years**, keep calibrated indefinitely.

### 2. Idempotent ingestion
`(sensor_id, ts)` is the primary key on both reading tables. Re-publishing
the same MQTT message or replaying a batch is safe — duplicates are silently
absorbed at the DB level.

### 3. One ingestion service for four protocols
`app/services/ingestion_service.py:ingest_one_reading()` is the only function
that writes to the readings tables. MQTT subscriber, HTTP `/ingest`, Modbus
poller, and CSV uploader all funnel through it. This guarantees calibration
and threshold evaluation logic is shared across all paths.

### 4. APScheduler in-process vs Celery
For MVP scale (single backend pod) we use APScheduler in the same process as
the API. When you need to scale beyond a single host, switch to Celery beat
+ workers; the worker functions (`run_modbus_poll_cycle`, `run_hourly_export`)
are already pure async functions that work either way.

### 5. WebSocket fanout
`app/ws/manager.py:Broadcaster` is in-memory and works for single-process
deployments. To scale across multiple backend pods, replace the `_fanout`
internals with Redis pub/sub:
- Each pod subscribes to a Redis channel
- `broadcast_reading()` publishes to Redis instead of fanning out locally
- Each pod fans out to its own connected WebSockets

### 6. RBAC
Four roles: `super_admin`, `admin`, `operator`, `client`.
- super_admin / admin: full access, including device API key creation
- operator: read+ack alerts, view sensors
- client: read-only, restricted to assigned sites via `user_site_access`

### 7. Device authentication
Devices authenticate to the HTTP `/ingest` endpoint via `X-API-Key` header.
The plain key is shown only at device creation; only the SHA-256 hash is
stored. Rotation is supported via `POST /devices/{id}/rotate-key`.

For MQTT, devices use Mosquitto username/password. In production add ACL
restrictions so a device can only publish to its own topic prefix.

## Data flow — single reading

```
gateway publishes
sites/{site_id}/sensors/{sensor_code}/data
  ↓
Mosquitto
  ↓
asyncio_mqtt subscriber  (app/workers/mqtt_subscriber.py)
  ↓
ingest_one_reading()
  ├── resolves device + sensor
  ├── INSERT raw_readings  (idempotent on PK)
  ├── apply calibration → INSERT calculated_readings
  ├── update sensor.last_reading_at, device.last_heartbeat_at, site.last_data_at
  ├── evaluate thresholds → maybe INSERT alerts
  ├── COMMIT
  ├── broadcast on WebSocket
  └── dispatch_alert_notifications (Slack/Discord/email)
```

## Time-series query path

```
GET /api/v1/readings/{sensor_id}?window=24h
  ↓
readings.py
  ├── parse window → start/end timestamps
  ├── if span > 1h → use time_bucket() to downsample
  └── return TimeSeriesResponse
```

ECharts on the frontend uses LTTB sampling on top, so even 30-day windows
with millions of points stay snappy.

## Failure modes & resilience

| Failure                          | Behavior |
|----------------------------------|----------|
| Mosquitto down                   | Subscriber loop reconnects with exponential backoff (1s → 60s) |
| Postgres down                    | Ingestion writes fail; gateway should buffer locally and retry |
| Backend pod restart              | APScheduler picks up where it left off; misfire grace = 5–10 min |
| Modbus device unreachable        | `IngestError` row written; alert raised by health_check after 15 min |
| Duplicate MQTT delivery          | Silent absorb via PK constraint |
| Threshold flap                   | One alert per breach; manual ack/resolve required |
