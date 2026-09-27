# GeoVertex Operations Runbook

## 1. Operational Overview

This runbook provides Standard Operating Procedures (SOPs), incident response protocols, and routine maintenance instructions for site reliability engineers (SREs), system administrators, and cadastral IT operations teams managing the GeoVertex platform.

---

## 2. System Monitoring & Health Check Interpretation

### 2.1 Endpoint Probes

| Endpoint | Target Probe | Expected Output | Remediation if Degraded / Failed |
| :--- | :--- | :--- | :--- |
| `GET /health/live` | Process Liveness | `200 OK` `{"status": "healthy"}` | Restart container process: `docker compose restart backend` |
| `GET /health/ready` | Operational Readiness | `200 OK` `{"status": "ready"}` | Check PostgreSQL, Redis, and Object Storage connectivity |
| `GET /metrics` | Prometheus Metrics | `200 OK` text/plain metrics | Verify Prometheus scraper target configuration |

### 2.2 Critical Metric Alerting Thresholds

| Metric | Warning Threshold | Critical Alert | Action |
| :--- | :--- | :--- | :--- |
| `geovertex_uptime_seconds` | Process restart | Reset < 60s | Investigate application crash logs |
| `geovertex_db_pool_size` | Active connections > 80% | Pool exhaustion (100%) | Increase `DB_POOL_SIZE` or investigate long-running transactions |
| `geovertex_storage_backend_type` | Local storage > 80% disk | Disk > 90% | Purge temporary files, expand volume, or migrate to S3 |
| HTTP Request Error Rate | > 1% 5xx errors (5m) | > 5% 5xx errors (2m) | Check Sentry / tracing middleware logs |

---

## 3. Incident Response Runbooks

### Runbook 101: Database Connection Pool Exhaustion

**Symptoms:**
- HTTP 500 errors on database-backed endpoints.
- Log message: `TimeoutError: QueuePool limit of size 20 overflow 10 reached, connection timed out`.

**Immediate Remediation:**
1. Check active database connections:
   ```bash
   docker compose -f docker-compose.production.yml exec postgres \
     psql -U geovertex -d geovertex_db -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"
   ```
2. Identify long-running idle or blocked queries:
   ```bash
   docker compose -f docker-compose.production.yml exec postgres \
     psql -U geovertex -d geovertex_db -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state FROM pg_stat_activity WHERE (now() - pg_stat_activity.query_start) > interval '2 minutes' AND state != 'idle';"
   ```
3. Terminate stuck transactions if necessary:
   ```bash
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = [STUCK_PID];
   ```
4. Adjust pool sizing in `.env`:
   ```bash
   DB_POOL_SIZE=30
   DB_MAX_OVERFLOW=15
   ```
   Restart backend workers:
   ```bash
   docker compose -f docker-compose.production.yml up -d --no-deps backend
   ```

---

### Runbook 102: Celery Worker Queue Backlog

**Symptoms:**
- Spatial validation, AI building extraction, or change detection jobs stuck in `PENDING` or `PROCESSING`.
- Redis queue depth growing unbounded.

**Immediate Remediation:**
1. Inspect queue length in Redis:
   ```bash
   docker compose -f docker-compose.production.yml exec redis redis-cli -a "$REDIS_PASSWORD" llen celery
   ```
2. Inspect worker process status:
   ```bash
   docker compose -f docker-compose.production.yml exec worker \
     celery -A app.workers.celery_app inspect active
   ```
3. Scale worker concurrency:
   Increase worker replicas in `docker-compose.production.yml`:
   ```bash
   docker compose -f docker-compose.production.yml up -d --scale worker=3 --no-deps worker
   ```
4. Check worker memory usage to rule out OOM kills:
   ```bash
   docker stats geovertex_prod_worker
   ```

---

### Runbook 103: Disk Space Exhaustion on Storage Volume

**Symptoms:**
- Document uploads failing with `OSError: [Errno 28] No space left on device`.
- Database write operations failing with disk full error.

**Immediate Remediation:**
1. Identify high-consumption directories:
   ```bash
   df -h
   du -sh /var/lib/docker/volumes/*
   ```
2. Clean up old rotated backup files (retaining minimum 30 days):
   ```bash
   find /opt/geovertex/backend/backups/ -name "*.gz" -mtime +30 -exec rm {} \;
   ```
3. Clean unused Docker resources:
   ```bash
   docker system prune -f --volumes=false
   ```
4. Vacuum database to reclaim space:
   ```bash
   docker compose -f docker-compose.production.yml exec postgres \
     vacuumdb -U geovertex -d geovertex_db --analyze --verbose
   ```

---

## 4. Routine Maintenance Procedures

### 4.1 Scheduled Database Vacuum & Reindex
Run weekly during low-traffic maintenance window:
```bash
docker compose -f docker-compose.production.yml exec postgres \
  psql -U geovertex -d geovertex_db -c "VACUUM ANALYZE;"
docker compose -f docker-compose.production.yml exec postgres \
  psql -U geovertex -d geovertex_db -c "REINDEX DATABASE geovertex_db;"
```

### 4.2 Automated Daily Backup Execution
Backups are executed daily at 02:00 UTC via cron:
```bash
# /etc/cron.d/geovertex_backup
0 2 * * * root /usr/bin/docker compose -f /opt/geovertex/docker-compose.production.yml run --rm backend python scripts/backup.py --output-dir /opt/geovertex/backend/backups >> /var/log/geovertex_backup.log 2>&1
```

### 4.3 JWT Secret & Credential Rotation Protocol
1. Generate new 64-character hex secret: `NEW_SECRET=$(openssl rand -hex 32)`.
2. Schedule a 5-minute maintenance window.
3. Update `JWT_SECRET` in `.env`.
4. Perform rolling reload of backend workers. Note: Existing user sessions will require re-login.
