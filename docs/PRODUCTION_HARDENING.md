# Production Hardening

Concrete checklist before going live. Each item explains *why*, not just *what*.

## 1. Secrets

- [ ] **`SECRET_KEY`** — generate with `openssl rand -hex 32`. Never commit; load
      from a secrets manager (AWS Secrets Manager, Hashicorp Vault, Doppler).
- [ ] **`POSTGRES_PASSWORD`** — long random; rotate every 90 days.
- [ ] **MQTT credentials** — separate username per gateway, not shared. Enables
      revocation and audit. Run `mosquitto_passwd` per device.
- [ ] **Device API keys** — generated server-side with `secrets.token_urlsafe(32)`,
      stored as SHA-256 hash. Plain key shown only once at creation. Rotation
      endpoint: `POST /api/v1/devices/{id}/rotate-key`.
- [ ] **SMTP credentials** — use app passwords or service-account tokens, not
      the user's main password.

## 2. TLS everywhere

| Channel               | Required port | Cert source |
|-----------------------|---------------|-------------|
| HTTPS web/API         | 443           | Let's Encrypt via Caddy/Traefik |
| WebSocket             | 443 (`wss://`)| Same as HTTPS |
| MQTT                  | 8883          | Internal CA or Let's Encrypt for public broker |
| Postgres              | 5432 (TLS)    | RDS / managed = automatic; self-host = manual |

For internal Docker network you can stay HTTP between containers, but:
- The edge proxy MUST terminate TLS.
- If gateways connect directly to MQTT over the public internet, use 8883 + cert auth.
- Never expose port 8000 (raw FastAPI) or 5432 (Postgres) on a public IP.

## 3. CORS

`backend/.env`:
```
CORS_ORIGINS=https://app.your-domain.com,https://admin.your-domain.com
```
**Never** use `*` in production. Wildcard + credentials = CSRF risk.

## 4. Rate limiting

The MVP has none. Add SlowAPI:

```bash
pip install slowapi
```

```python
# app/main.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

```python
# app/api/v1/auth.py
@router.post("/login")
@limiter.limit("5/minute")
async def login(...): ...
```

```python
# app/api/v1/ingest.py — per device key, not IP
@router.post("/batch")
@limiter.limit("60/minute", key_func=lambda r: r.headers.get("X-API-Key", "anon"))
async def ingest_batch(...): ...
```

Recommended initial limits:
- `POST /auth/login`: 5/min per IP
- `POST /ingest`: 600/min per device (enough for 10 readings/sec)
- `POST /ingest/batch`: 60/min per device, with bodies up to 1000 readings each
- All other endpoints: 100/min per user

## 5. JWT lifecycle

- Access token: 60 min — short enough that a stolen token expires fast.
- Refresh token: 14 days — stored in localStorage in MVP. For higher-security
  deployments move it to an `HttpOnly; Secure; SameSite=Strict` cookie.
- Revocation: MVP has none (stateless JWT). To add, persist a `token_blacklist`
  table or a Redis set keyed by JWT `jti`; check on each request in
  `app/api/deps.py:get_current_user`.

## 6. Database

- [ ] **Connection pool sizing**: `DATABASE_POOL_SIZE` should be ≤
      `(max_connections - 10) / num_pods`. Default 10 is fine for a single
      backend pod with 100-conn Postgres.
- [ ] **Statement timeout**: set `statement_timeout = 30s` on the role to
      kill runaway queries (huge time-series scans without `ts` filter).
- [ ] **Backups**: nightly `pg_dump` is OK to start, but switch to
      continuous WAL archival via `pgBackRest` or `barman` once you have
      paying customers — `pg_dump` alone means up to 24h of data loss.
- [ ] **Monitoring**: track `pg_stat_statements` for slow queries.
      The hot queries are time-series reads; ensure
      `idx_calc_sensor_time` is being used (`EXPLAIN ANALYZE`).

## 7. TimescaleDB tuning

The migration creates compression after 30 days and retention after 2 years.
After running for a few weeks, validate:

```sql
-- Compression effectiveness
SELECT chunk_name, before_compression_total_bytes, after_compression_total_bytes,
       round(100.0 * (1 - after_compression_total_bytes::numeric /
             nullif(before_compression_total_bytes, 0)), 1) AS ratio_pct
FROM timescaledb_information.compression_settings
JOIN timescaledb_information.chunks USING (hypertable_name);

-- Continuous aggregates for fast dashboard queries (recommended after 1M rows)
CREATE MATERIALIZED VIEW readings_hourly
WITH (timescaledb.continuous) AS
SELECT sensor_id,
       time_bucket('1 hour', ts) AS bucket,
       AVG(value) AS avg_value,
       MIN(value) AS min_value,
       MAX(value) AS max_value,
       COUNT(*)   AS n
FROM calculated_readings
GROUP BY sensor_id, bucket;

SELECT add_continuous_aggregate_policy('readings_hourly',
  start_offset => INTERVAL '1 month',
  end_offset   => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 hour');
```

Then update `readings.py` to query `readings_hourly` for windows > 7d.

## 8. MQTT broker

For production move to **EMQX 5** (the bundled Mosquitto is fine for MVP):
- Native HA / clustering
- Web dashboard with per-client metrics
- Built-in ACL UI
- Authentication chain: JWT → HTTP → file → built-in DB
- Rate limiting per client

ACL example (Mosquitto-style):
```
# Each gateway: only its own topics
user device_dl001
topic write sites/DEMO-001/sensors/+/data
topic write sites/DEMO-001/devices/DL-001/heartbeat

# Backend ingester
user ingest
topic read sites/+/sensors/+/data
topic read sites/+/devices/+/heartbeat
```

## 9. Logging & audit

- [ ] **Structured logging**: already using `structlog` with JSON output.
      Ship to CloudWatch / Loki / ELK.
- [ ] **Audit trail**: add an `audit_log` table for:
      - User login attempts (success + fail)
      - Device API key creation / rotation
      - Threshold modifications
      - Alert acknowledgement / resolution
- [ ] **PII**: redact `password`, `password_hash`, `api_key`, JWT tokens from
      logs. The current code is clean — keep it that way in any new endpoint.

## 10. Scaling beyond a single host

Trigger points to scale:
- **>1,000 sensors at 5s intervals** → MQTT subscriber CPU-bound. Run
  multiple subscriber processes with shared subscriptions (`$share/...`).
- **>50 sites with active dashboards** → WebSocket fanout exceeds in-memory
  capacity. Switch `Broadcaster` to Redis pub/sub (already noted in
  `docs/ARCHITECTURE.md`).
- **>10M readings/day** → run scheduled jobs in a dedicated worker pod
  via Celery beat instead of in-process APScheduler.
- **>500GB on hypertables** → enable continuous aggregates; consider
  Timescale Cloud for managed multi-node.

## 11. Frontend

- [ ] Add `Content-Security-Policy` header at the proxy:
  ```
  default-src 'self';
  connect-src 'self' wss://your-domain.com;
  script-src 'self' 'unsafe-inline';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data:;
  ```
- [ ] Move JWT refresh token from `localStorage` to `HttpOnly` cookie if
      you're handling sensitive data (the MVP defaults are OK for internal use).
- [ ] Add Sentry for error tracking; both `@sentry/nextjs` and Python
      `sentry-sdk`.

## 12. Penetration test items before launch

- SQL injection: SQLAlchemy 2 ORM is parameterized — but verify any
  `text()` queries (we have one in `readings.py` — uses bound params, OK).
- Auth bypass: try hitting protected endpoints with no token, expired
  token, refresh token in `Authorization` header.
- Mass assignment: try sending `role: super_admin` on `PATCH /users/me`.
- IDOR: as a `client` user, can you read sites you don't have
  `user_site_access` for? `app/api/v1/sites.py:_user_can_view_site` is the
  gate — verify across `GET /sites/{id}`, `GET /sensors`, `GET /alerts`,
  `GET /readings/{sensor_id}`. **Note**: alerts and readings endpoints in
  the MVP do NOT check `user_site_access` yet — add this check before
  letting external clients log in.
- Storage of secrets in metadata: ensure no API keys leak into
  `sensors.metadata` or `devices.config`.

## 13. Disaster recovery runbook

Document and rehearse:
1. **Backend pod down**: docker compose health check + auto-restart already
   covers single-process crashes. For multi-host, use ECS / K8s liveness probe
   on `/health`.
2. **Postgres failure**: restore from latest WAL backup. RTO < 1 hour.
3. **MQTT broker down**: gateways buffer locally with QoS 1; on reconnect
   they replay. Idempotent ingestion absorbs replays. RTO = however long
   the broker is down (gateway buffer size dependent).
4. **Region failure** (AWS): cross-region read replica + S3 cross-region
   replication for export bucket. RTO 4 hours, RPO 15 minutes.

## 14. Compliance

If serving construction-site safety data, you may need:
- **Korean PIPA** (개인정보 보호법) — if storing personnel data, DPO
  appointment + consent records.
- **ISO 27001** — for B2B contracts with chaebol clients.
- **Data sovereignty** — Korean construction firms often require data to
  stay in Korea. Use Hetzner Frankfurt or a Korean cloud (Naver Cloud,
  KT Cloud) instead of AWS US.

## 15. Operational checklist (final)

Run the following before letting customers in:

```bash
# Schema applied?
docker compose exec backend alembic current

# Hypertables created?
docker compose exec postgres psql -U civil -d civil_monitoring \
  -c "SELECT hypertable_name FROM timescaledb_information.hypertables;"

# Compression policies registered?
docker compose exec postgres psql -U civil -d civil_monitoring \
  -c "SELECT * FROM timescaledb_information.jobs WHERE proc_name = 'policy_compression';"

# Scheduler jobs registered?
docker compose logs backend | grep "scheduler.configured"

# MQTT subscriber connected?
docker compose logs backend | grep "mqtt.connected"

# Test ingestion path end-to-end
curl -X POST http://localhost/api/v1/ingest \
  -H "X-API-Key: <DEVICE_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"device_code":"DL-001","sensor_code":"INC-001-X","ts":"2026-05-08T00:00:00Z","value":0.5}'
```

If any step fails, do not launch.
