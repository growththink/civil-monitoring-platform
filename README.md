# Civil Monitoring Platform

Production-ready geotechnical / civil-engineering instrumentation monitoring SaaS.

Sensors → Data loggers / PLCs / RTUs → Industrial LTE/5G routers → Cloud → Web dashboard.
Supports MQTT, HTTP POST, Modbus TCP polling, and CSV import. Hourly automatic Modbus
poll + per-site CSV export are scheduled out of the box.

## Stack

| Layer       | Choice                                            |
|-------------|---------------------------------------------------|
| Backend     | FastAPI (Python 3.12), async SQLAlchemy 2         |
| DB          | PostgreSQL 16 + TimescaleDB (hypertables)         |
| Cache/queue | Redis                                             |
| MQTT broker | Mosquitto 2 (swap to EMQX in prod)                |
| Realtime    | WebSocket (server) + asyncio_mqtt (subscriber)    |
| Modbus      | pymodbus 3 (async TCP client)                     |
| Scheduler   | APScheduler (cron triggers)                       |
| Frontend    | Next.js 15 + React 19 + TypeScript + Tailwind     |
| Charts      | ECharts 5 (LTTB sampling, threshold lines)        |
| Reverse proxy| NGINX                                            |
| Deployment  | Docker Compose (single host) → AWS / Hetzner ready|

## Quick start (local)

```bash
# 1. Copy env templates
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 2. IMPORTANT — generate a real SECRET_KEY:
echo "SECRET_KEY=$(openssl rand -hex 32)" >> backend/.env

# 3. Create the MQTT user file (one-time)
docker compose run --rm --no-deps mosquitto \
  mosquitto_passwd -c -b /mosquitto/config/passwd ingest ingest_pw

# 4. Boot the stack
docker compose up -d --build

# 5. Tail logs
docker compose logs -f backend
```

The backend container automatically:
1. Runs `alembic upgrade head` (creates schema + TimescaleDB hypertables)
2. Runs the seed script (creates admin user, demo site, demo device, 5 sensors)
3. Boots FastAPI

After startup look in `docker compose logs backend` for a line like:
```
[seed] >>> DEVICE_API_KEY (save this!) = AbCdEf1234...
```
Save that key — it's used by the gateway to push HTTP data.

## Access

| Service              | URL                          |
|----------------------|------------------------------|
| Web dashboard        | http://localhost              |
| API docs (Swagger)   | http://localhost/docs         |
| API docs (ReDoc)     | http://localhost/redoc        |
| Direct backend       | http://localhost:8000         |
| Direct frontend      | http://localhost:3000         |
| Postgres             | localhost:5432                |
| MQTT                 | localhost:1883                |

Default login (from seed):
```
Email:    admin@civil-monitoring.local
Password: ChangeMe!2026
```
**Change this immediately in production.**

## Send test data

In a separate shell:

```bash
cd backend
pip install asyncio-mqtt
python -m scripts.send_test_mqtt --host localhost --port 1883 \
  --username ingest --password ingest_pw \
  --site DEMO-001 --device DL-001 --interval 5
```

Open the dashboard → DEMO-001 → live readings start streaming.

## How the 1-hour automatic data collection works

`backend/app/workers/scheduler.py` registers four cron jobs:

| Job             | Default cron     | Effect |
|-----------------|------------------|--------|
| `modbus_poll`   | `0 * * * *`      | Polls every Modbus TCP device once an hour, ingests all sensors |
| `hourly_export` | `5 * * * *`      | Generates a per-site CSV snapshot of the last hour at `EXPORT_DIR` |
| `health_check`  | `*/5 * * * *`    | Marks devices offline if no heartbeat in 15 min, raises alerts |
| `data_missing_check` | `*/10 * * * *` | Per-sensor missing-data detection |

All four are configurable via env vars in `backend/.env`.

## Folder map

```
civil-monitoring-platform/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entrypoint + lifespan
│   │   ├── core/                 # config, db, security, logging, exceptions
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── schemas/              # Pydantic DTOs
│   │   ├── api/v1/               # REST + WebSocket routers
│   │   ├── services/             # ingestion / threshold / notification / auth
│   │   ├── workers/              # MQTT subscriber, Modbus poller, scheduler, export
│   │   └── ws/                   # WebSocket connection manager
│   ├── alembic/versions/         # 0001_init.py — TimescaleDB hypertables
│   ├── scripts/                  # seed.py, send_test_mqtt.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/                      # Next.js 15 App Router pages
│   ├── components/               # SiteCard, SensorChart, AlertList, …
│   ├── lib/                      # api.ts, ws.ts, types.ts
│   ├── Dockerfile
│   ├── package.json
│   └── tailwind.config.ts
├── nginx/nginx.conf
├── mosquitto/config/             # mosquitto.conf + setup_users.sh
├── docs/                         # ARCHITECTURE.md, DEPLOYMENT.md, MQTT_PAYLOADS.md, PRODUCTION_HARDENING.md
└── docker-compose.yml
```

## Useful commands

```bash
# Open psql
docker compose exec postgres psql -U civil -d civil_monitoring

# Run a new migration after model edits
docker compose exec backend alembic revision --autogenerate -m "add_xxx"
docker compose exec backend alembic upgrade head

# Re-run seed
docker compose exec backend python -m scripts.seed

# Tail MQTT broker
docker compose logs -f mosquitto

# Listen to a topic
docker compose exec mosquitto \
  mosquitto_sub -u ingest -P ingest_pw -t 'sites/+/sensors/+/data' -v
```

See:
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system design
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — AWS / Hetzner deployment
- [`docs/MQTT_PAYLOADS.md`](docs/MQTT_PAYLOADS.md) — gateway payload formats
- [`docs/PRODUCTION_HARDENING.md`](docs/PRODUCTION_HARDENING.md) — TLS, secrets, scaling
