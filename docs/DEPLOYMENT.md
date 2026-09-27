# GeoVertex Production Deployment Guide

## 1. Executive Summary

GeoVertex is an enterprise-grade 3D Cadastral Intelligence and Vertical Property Mapping Platform. This document provides authoritative instructions for deploying GeoVertex to production infrastructure, covering both multi-container Docker Compose architectures and scalable Kubernetes orchestration.

> [!IMPORTANT]
> The platform adheres to strict cadastral integrity: no mock spatial calculations, no fabricated ownership titles, and no synthetic AI outputs are permitted in production environments.

---

## 2. Infrastructure Prerequisites

| Component | Minimum Specification | Recommended Production Specification |
| :--- | :--- | :--- |
| **CPU** | 4 Cores (x86_64) | 8–16 Cores |
| **RAM** | 8 GB | 32 GB |
| **Disk Storage** | 50 GB SSD (NVMe preferred) | 250 GB+ NVMe SSD |
| **Operating System** | Ubuntu 22.04 LTS / Debian 12 / RHEL 9 | Ubuntu 22.04 LTS |
| **Container Engine** | Docker Engine 24.0+ & Compose v2.20+ | Docker Engine 26.0+ |
| **GPU Acceleration** | *Optional*: CPU fallback supported | NVIDIA T4 / A10G (for high-volume AI inference) |

---

## 3. Architecture Topology

```mermaid
flowchart TD
    subgraph Public_Internet["Public Internet"]
        Client["Browser Client / Cesium 3D"]
    end

    subgraph Edge_DMZ["Edge DMZ / Ingress"]
        Nginx["Nginx Reverse Proxy\n(Port 80/443 TLS, CSP, Rate Limiting)"]
    end

    subgraph Internal_Network["Internal Application Network (Isolated)"]
        Frontend["Frontend SPA Container\n(Static React / Vite Bundle)"]
        Backend["FastAPI Backend Workers\n(4 ASGI Workers, Gunicorn/Uvicorn)"]
        Worker["Celery Background Worker\n(Concurrency: 4, Spatial & OCR Tasks)"]
    end

    subgraph Storage_Tier["Data Persistence Tier"]
        Postgres["PostgreSQL 16 + PostGIS 3.4\n(Spatial DB, Connection Pool: 20/10)"]
        Redis["Redis 7 (AOF Persistent)\n(Pub/Sub Broker & Cache)"]
        MinIO["MinIO / AWS S3\n(Document Object Storage)"]
    end

    Client -->|HTTPS / WSS| Nginx
    Nginx -->|Static Assets| Frontend
    Nginx -->|API / Health / Metrics| Backend
    Backend -->|Async SQLAlchemy| Postgres
    Backend -->|Cache & Tasks| Redis
    Backend -->|Document Storage| MinIO
    Worker -->|Fetch Jobs| Redis
    Worker -->|Read/Write State| Postgres
    Worker -->|Deed & Mesh Storage| MinIO
```

---

## 4. Production Environment Configuration

All production configurations must be specified via environment variables or a secured `.env` file (permissions `600` owned by `geovertex`).

### 4.1 Fail-Fast Production Validation Rules

The backend server strictly enforces fail-fast validation upon startup if `ENVIRONMENT=production`:
1. `DEBUG` must be set to `false`. Application fails to boot if set to `true`.
2. `JWT_SECRET` must be set to a cryptographically secure string of at least 32 characters. Default placeholder keys are rejected.
3. `DATABASE_URL` must point to PostgreSQL with PostGIS enabled. SQLite connections are rejected.
4. `CORS_ORIGINS` must not contain wildcards (`*`) or `localhost`.

### 4.2 Production Environment Template

```bash
# Core Environment
ENVIRONMENT="production"
DEBUG=false
PROJECT_NAME="GeoVertex Cadastral Intelligence Platform"
API_V1_STR="/api/v1"
LOG_LEVEL="INFO"

# Cryptographic Keys (Generate with: openssl rand -hex 32)
JWT_SECRET="c8e6a1d490b411ef88b10242ac120002f5a6b7c8d9e0123456789abcdef01234"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# PostgreSQL 16 + PostGIS 3.4 Database
POSTGRES_USER="geovertex_app"
POSTGRES_PASSWORD="[SECURE_STRONG_PASSWORD]"
POSTGRES_DB="geovertex_db"
DATABASE_URL="postgresql+psycopg://geovertex_app:[SECURE_STRONG_PASSWORD]@postgres:5432/geovertex_db"
DATABASE_URL_SYNC="postgresql+psycopg://geovertex_app:[SECURE_STRONG_PASSWORD]@postgres:5432/geovertex_db"

# Connection Pool Settings
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
DB_POOL_PRE_PING=true

# Redis Cache & Message Broker
REDIS_PASSWORD="[SECURE_REDIS_PASSWORD]"
REDIS_URL="redis://:[SECURE_REDIS_PASSWORD]@redis:6379/0"
CELERY_BROKER_URL="redis://:[SECURE_REDIS_PASSWORD]@redis:6379/1"
CELERY_RESULT_BACKEND="redis://:[SECURE_REDIS_PASSWORD]@redis:6379/2"

# Object Storage (AWS S3 or MinIO)
STORAGE_BACKEND="minio"
S3_ENDPOINT_URL="http://minio:9000"
S3_BUCKET_NAME="geovertex-documents"
MINIO_ROOT_USER="geovertex_storage"
MINIO_ROOT_PASSWORD="[SECURE_STORAGE_PASSWORD]"
S3_ACCESS_KEY="geovertex_storage"
S3_SECRET_KEY="[SECURE_STORAGE_PASSWORD]"
S3_REGION="us-east-1"
S3_USE_SSL=false

# Notification SMTP Delivery
SMTP_HOST="smtp.mailgun.org"
SMTP_PORT=587
SMTP_USER="postmaster@geovertex.gov"
SMTP_PASSWORD="[SMTP_PASSWORD]"
SMTP_FROM_EMAIL="notifications@geovertex.gov"
SMTP_TLS=true

# CORS Allowed Origins
CORS_ORIGINS="https://geovertex.gov,https://app.geovertex.gov"
```

---

## 5. Deployment Procedures

### 5.1 Docker Compose Deployment (Single-Node / Scaled Host)

1. **Clone repository and configure environment**:
   ```bash
   git clone https://github.com/reddycharankumar513-dotcom/GeoVertex.git /opt/geovertex
   cd /opt/geovertex
   cp .env.example .env
   chmod 600 .env
   # Edit .env with production credentials
   ```

2. **Generate TLS Certificates**:
   Place authoritative SSL certificates in `/opt/geovertex/certs/`:
   ```bash
   mkdir -p certs
   # Copy domain.crt and domain.key into certs/
   ```

3. **Initialize and Build Containers**:
   ```bash
   docker compose -f docker-compose.production.yml build
   ```

4. **Start Data Persistence Services**:
   ```bash
   docker compose -f docker-compose.production.yml up -d postgres redis minio
   # Verify healthcheck status:
   docker compose -f docker-compose.production.yml ps
   ```

5. **Apply Database Migrations & Initial Administrative Bootstrap**:
   ```bash
   docker compose -f docker-compose.production.yml run --rm backend alembic upgrade head
   docker compose -f docker-compose.production.yml run --rm backend python -m app.seed
   ```

6. **Start Application Services**:
   ```bash
   docker compose -f docker-compose.production.yml up -d
   ```

7. **Verify Deployment Health**:
   ```bash
   curl -f http://localhost/health
   curl -f http://localhost/health/ready
   curl -f http://localhost/metrics
   ```

---

### 5.2 Kubernetes Production Deployment Architecture

For high-availability clustered deployments, deploy via Helm or Kubernetes manifests:

- **Namespace**: `geovertex-production`
- **Database**: Managed Cloud SQL / AWS RDS PostgreSQL 16 with PostGIS extension, or Zalando Postgres Operator.
- **Cache**: AWS ElastiCache / Redis Cluster.
- **Storage**: AWS S3 Bucket with IAM Roles for Service Accounts (IRSA).
- **Backend Deployment**:
  - Replicas: 3 (Horizontal Pod Autoscaler target: 70% CPU, 75% Memory).
  - Liveness probe: `GET /health/live`, delay 15s, period 20s.
  - Readiness probe: `GET /health/ready`, delay 10s, period 10s.
- **Worker Deployment**:
  - Replicas: 2 (HPA based on Redis queue length).
- **Ingress Controller**: Nginx Ingress or AWS ALB Controller with cert-manager (Let's Encrypt ACME).

---

## 6. Zero-Downtime Rolling Updates

To update an active production deployment without service disruption:

1. **Pull updated images**:
   ```bash
   docker compose -f docker-compose.production.yml pull backend frontend worker
   ```

2. **Run schema migrations before container replacement**:
   ```bash
   docker compose -f docker-compose.production.yml run --rm backend alembic upgrade head
   ```

3. **Perform sequential rolling reload**:
   ```bash
   docker compose -f docker-compose.production.yml up -d --no-deps --build backend
   docker compose -f docker-compose.production.yml up -d --no-deps --build worker
   docker compose -f docker-compose.production.yml up -d --no-deps --build frontend
   docker compose -f docker-compose.production.yml exec nginx nginx -s reload
   ```

---

## 7. Rollback Procedures

If an operational anomaly occurs during or immediately after deployment:

1. **Revert Application Containers**:
   ```bash
   docker compose -f docker-compose.production.yml down backend worker frontend
   git checkout tags/v1.0.0-stable
   docker compose -f docker-compose.production.yml up -d backend worker frontend
   ```

2. **Downgrade Database Schema (if required)**:
   ```bash
   docker compose -f docker-compose.production.yml run --rm backend alembic downgrade -1
   ```

3. **Disaster Recovery Database Restore**:
   If data corruption occurred, invoke the automated restore script:
   ```bash
   docker compose -f docker-compose.production.yml run --rm backend \
     python scripts/restore.py --backup-file backups/geovertex_backup_latest.dump.gz --confirm
   ```
