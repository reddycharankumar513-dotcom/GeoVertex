# GeoVertex
## 3D Cadastral Intelligence & Vertical Property Mapping Platform

[![CI Validation](https://github.com/geovertex/geovertex/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://reactjs.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-blue.svg)](https://postgis.net)

---

## 1. Project Overview
**GeoVertex** is an advanced 3D cadastral intelligence platform designed to bridge conventional 2D surface cadastres and complex vertical real-world property structures. It models multi-level land administration:
```
Jurisdiction ──> Parcel ──> Building ──> Floor ──> Unit ──> Underground Assets
```

### Current Status: Phase 1 (Platform Foundation) ONLY
> [!IMPORTANT]
> This codebase currently implements **Phase 1: PLATFORM FOUNDATION**. Phase 2 (2D Parcel GIS), Phase 3 (3D Digital Twin), Phase 4 (Vertical Hierarchy), AI model extraction, and document pipelines are strictly planned on the 15-phase roadmap and **not yet active**. No simulated or mock GIS/AI data is present.

---

## 2. Monorepo Structure

```text
GeoVertex/
├── docs/                        # Master specifications & architecture
│   ├── MASTER_PRD.md            # Highest-level Product Requirements Document
│   ├── ARCHITECTURE.md          # Master System Architecture
│   ├── DEVELOPMENT_ROADMAP.md   # 15-Phase execution and governance gates
│   ├── DATA_MODEL.md            # Relational & PostGIS schema definitions
│   ├── API_CONTRACT.md          # OpenAPI REST v1 endpoints and error specs
│   ├── AI_PIPELINE.md           # Building, floor & change detection specs
│   ├── GIS_PIPELINE.md          # Coordinate Reference System (CRS) & PostGIS topology
│   └── WORKFLOWS.md             # Citizen, Surveyor, Officer, and Admin state machines
│
├── frontend/                    # React 18 + TypeScript + Vite + Tailwind CSS
│   ├── src/
│   │   ├── api/                 # API client with token injection & error unwrapping
│   │   ├── auth/                # AuthContext, session hooks, token rotation
│   │   ├── components/          # ProtectedRoute, UI primitives
│   │   ├── layouts/             # Role-aware DashboardLayout & navigation
│   │   ├── pages/               # Login, Dashboard, Profile, Users, Audit, 403, 404
│   │   ├── types/               # TypeScript interfaces
│   │   └── __tests__/           # Vitest unit & RBAC tests
│   └── package.json
│
├── backend/                     # FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic
│   ├── app/
│   │   ├── api/v1/              # Versioned API routes (auth, users, orgs, audit, health)
│   │   ├── core/                # Typed config, security (bcrypt/JWT), logging, errors
│   │   ├── database/            # Async/Sync engines, base classes, sessions
│   │   ├── dependencies/        # get_current_user, require_role, get_db
│   │   ├── middleware/          # RequestTracingMiddleware with X-Request-ID
│   │   ├── models/              # User, Role, Organization, Jurisdiction, AuditEvent
│   │   ├── repositories/        # Asynchronous data access layer
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── services/            # Domain services (auth, user, org, audit)
│   │   ├── main.py              # Application entrypoint & OpenAPI docs
│   │   └── seed.py              # Idempotent development data seeder
│   ├── migrations/              # Alembic versioned migration scripts
│   └── requirements.txt
│
├── docker/                      # Multi-stage Dockerfiles (Backend, Frontend, Worker)
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── Dockerfile.worker
│   └── nginx.conf
│
├── tests/
│   ├── backend/                 # Pytest suite (health, auth, rbac, users, orgs, audit)
│   └── frontend/                # Vitest frontend tests
│
├── .github/workflows/ci.yml     # Automated CI verification workflow
├── docker-compose.yml           # Complete containerized orchestration stack
├── .env.example                 # Environment configuration template
└── README.md
```

---

## 3. Development Accounts & Credentials

The seed script creates the following accounts for verifying role-based access:

| Role | Email Credential | Password | Primary Permissions |
|---|---|---|---|
| **Admin** | `admin@geovertex.local` | `GeoVertexAdmin2026!` | User management, role modification, account activation, audit inspection |
| **Officer** | `officer@geovertex.local` | `GeoVertexOfficer2026!` | Cadastral review queue, inspection, user directory viewing |
| **Surveyor** | `surveyor@geovertex.local` | `GeoVertexSurveyor2026!` | Field survey creation, geometry correction, submission |
| **Citizen** | `citizen@geovertex.local` | `GeoVertexCitizen2026!` | Public parcel search, discrepancy reporting, document submission |
| **Planner** | `planner@geovertex.local` | `GeoVertexPlanner2026!` | Cadastral spatial read, urban utility overlay inspection |

---

## 4. Local Quickstart (Without Docker)

### Prerequisites
- **Python**: 3.12+
- **Node.js**: 20+ (with npm)
- **PostgreSQL 16 + PostGIS 3.4** (or SQLite fallback for standalone quick testing)

### Step 1: Clone and Configure Environment
```bash
cp .env.example .env
```

### Step 2: Set up Backend
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Linux / macOS:
source venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Run database migrations
cd backend
alembic upgrade head

# Seed development users and sample administrative jurisdiction
python -m app.seed
```

### Step 3: Run Backend Server
```bash
# From backend/ directory:
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Base URL: `http://127.0.0.1:8000/api/v1`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`
- Health / Readiness Probe: `http://127.0.0.1:8000/health/ready`

### Step 4: Set up and Run Frontend
```bash
cd frontend
npm install
npm run dev
```
- Frontend Web App: `http://localhost:5173`

---

## 5. Docker Orchestration Quickstart

To run the complete production-grade containerized stack with PostgreSQL/PostGIS and Redis:

```bash
docker compose up --build
```

Services started:
- `geovertex_postgres`: PostGIS 16-3.4 on port `5432`
- `geovertex_redis`: Redis 7-alpine on port `6379`
- `geovertex_backend`: FastAPI API server on port `8000`
- `geovertex_frontend`: React + Nginx on port `3000`

---

## 6. Running Automated Tests

### Backend Tests (Pytest)
```bash
# Run the 21 automated backend tests
.\venv\Scripts\python.exe -m pytest tests/backend -v
```
Test suite verifies:
- Health and readiness probes (`/health`, `/health/ready`)
- Citizen registration (`/auth/register`)
- Login authentication, credential verification, and failure handling
- Inactive user login rejection and protected endpoint blocking
- Token rotation and revocation on logout
- 5-role authorization matrix and admin-only endpoint protection
- User directory CRUD and role modification
- Admin audit trail generation
- Organizations and jurisdictions registration

### Frontend Tests (Vitest)
```bash
cd frontend
npm test
```
Verifies:
- Session storage management
- API client error unwrapping
- Role-based route guard permissions
- Admin and Officer exclusivity rules

---

## 7. Security Architecture

1. **Password Hashing**: Direct, salted Bcrypt implementation preventing plain password exposure and bypasses.
2. **Token Rotation**: Refresh tokens are cryptographically hashed (SHA-256) and single-use; token reuse triggers immediate rejection.
3. **Server-Side Enforcement**: All authorization decisions are strictly evaluated on the FastAPI backend using dependency injection (`require_role(...)`).
4. **Append-Only Auditing**: Security occurrences (`LOGIN_SUCCESS`, `LOGIN_FAILED`, `ROLE_CHANGED`, `USER_DEACTIVATED`) create tamper-evident `audit_logs` records.
5. **No Leaked Credentials**: Pydantic schemas filter out password hashes from all outbound responses; structured logging explicitly redacts sensitive keys.
