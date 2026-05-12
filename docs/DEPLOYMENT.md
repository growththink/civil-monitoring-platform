# Deployment Guide

## Single-host (Hetzner / DigitalOcean / EC2)

For MVP through ~50 sites and ~5,000 sensors, a single host is fine.

### Recommended specs (Hetzner CPX31 / equivalent)
- 4 vCPU
- 8 GB RAM
- 160 GB SSD (NVMe preferred — TimescaleDB is I/O-heavy)
- Ubuntu 24.04 LTS

### Setup

```bash
# 1. Provision
ssh root@<your-server>
adduser deploy && usermod -aG sudo deploy
ufw allow 22 80 443 1883 8883/tcp
ufw enable

# 2. Install Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy

# 3. Clone + configure
su - deploy
git clone <your-repo> civil-monitoring && cd civil-monitoring
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 4. Generate strong secrets
sed -i "s|SECRET_KEY=.*|SECRET_KEY=$(openssl rand -hex 32)|" backend/.env
sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 16)|" backend/.env

# 5. Setup mosquitto users
docker compose run --rm --no-deps mosquitto \
  mosquitto_passwd -c -b /mosquitto/config/passwd ingest "$(openssl rand -hex 16)"

# 6. Boot
docker compose up -d --build
docker compose logs -f
```

### TLS with Let's Encrypt

Replace the bundled `nginx` service with Traefik or Caddy for automatic ACME:

```yaml
# docker-compose.prod.yml — Caddy variant
caddy:
  image: caddy:2-alpine
  restart: unless-stopped
  ports: ["80:80", "443:443"]
  volumes:
    - ./Caddyfile:/etc/caddy/Caddyfile
    - caddy_data:/data
```

`Caddyfile`:
```
your-domain.com {
  reverse_proxy /api/* backend:8000
  reverse_proxy /ws*  backend:8000
  reverse_proxy /docs backend:8000
  reverse_proxy frontend:3000
}
```

### MQTT over TLS

Edit `mosquitto/config/mosquitto.conf`:
```
listener 8883
cafile   /mosquitto/config/certs/ca.crt
certfile /mosquitto/config/certs/server.crt
keyfile  /mosquitto/config/certs/server.key
require_certificate false
```

Mount certs and expose 8883 in `docker-compose.yml`. Update gateway clients
to connect to port 8883 with TLS.

## AWS deployment (production scale)

Suggested architecture beyond ~50,000 sensors:

```
Route 53 ─▶ ALB (HTTPS)
              │
              ├──▶ ECS Fargate × N (FastAPI)         ─ RDS Postgres + TimescaleDB Cloud
              ├──▶ ECS Fargate × N (worker — beat)
              ├──▶ ECS Fargate × N (worker — exec)   ─ ElastiCache Redis (Celery broker + WS pub/sub)
              └──▶ ECS Fargate × N (frontend)        ─ S3 (CSV exports + reports)

IoT side:
  AWS IoT Core (managed MQTT) ─▶ Rule action ─▶ ECS Fargate (subscriber)
                                                or ─▶ Kinesis Firehose ─▶ S3 ─▶ TimescaleDB
```

Critical changes from the Compose version:
- Replace APScheduler with Celery beat (so jobs survive across multiple backend pods)
- Replace in-memory `Broadcaster` with Redis pub/sub
- Use `timescale/timescaledb-ha` on RDS or [Timescale Cloud](https://www.timescale.com/cloud)
- Move CSV exports to S3 (`backend/app/workers/hourly_export.py:run_hourly_export`
  already writes to a local path — change to `boto3.put_object`)

## Backups

Daily Postgres dump:
```bash
# /etc/cron.daily/civmon-backup
docker exec civmon-postgres \
  pg_dump -U civil civil_monitoring | gzip > /backup/civmon-$(date +%F).sql.gz
find /backup -name 'civmon-*.sql.gz' -mtime +30 -delete
```

For Postgres + Timescale, prefer continuous WAL backups via `pgBackRest`
or `barman` in production.

## Monitoring

Add to `docker-compose.yml`:
```yaml
prometheus:
  image: prom/prometheus
  volumes: [./prometheus.yml:/etc/prometheus/prometheus.yml]
grafana:
  image: grafana/grafana
  ports: ["3001:3000"]
```

Scrape:
- Postgres via `postgres_exporter`
- Mosquitto via `mosquitto-exporter`
- Backend via `prometheus_fastapi_instrumentator` (add to `requirements.txt`
  and instrument `app.main`)
