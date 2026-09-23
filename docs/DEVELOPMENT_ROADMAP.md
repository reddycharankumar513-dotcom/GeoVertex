# GEOVERTEX: DEVELOPMENT ROADMAP
## 15-Phase Execution Plan & Phase-Gate Governance

Version: 1.0  
Status: Authoritative Roadmap  
Associated Documents: [MASTER_PRD.md](MASTER_PRD.md), [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 1. Roadmap Overview & Phasing Strategy

GeoVertex is engineered using a modular, phase-gated methodology. Each phase produces concrete, testable software artifacts. Under no circumstances may features from future phases be simulated or prematurely implemented.

| Phase | Title | Focus Area | Status |
|---|---|---|---|
| **Phase 1** | **Platform Foundation** | Monorepo, PostGIS DB, Auth, JWT, RBAC, Core API, React Shell, Docker, Tests | **COMPLETED** |
| **Phase 2** | **Property & Parcel 2D GIS** | 2D Cadastral Parcels, Properties, Buildings, PostGIS/Shapely Geodesics, GIS Ingest/Export, Interactive Map | **COMPLETED** |
| Phase 3 | 3D Digital Twin Core | CesiumJS integration, 3D terrain, parcel extrusion, 3D camera controls | Planned |
| Phase 4 | Building, Floor & Unit Hierarchy | Vertical property structures, PointZ/PolygonZ, units, parent-child relations | Planned |
| Phase 5 | Surveyor Workflow & Field Ingestion | Survey projects, GNSS point capture, image/point cloud upload, field notes | Planned |
| Phase 6 | AI Building & Floor Extraction | Modular U-Net / Mask R-CNN segmentation, point-cloud height slice analysis | Planned |
| Phase 7 | Topology Validation Engine | GEOS/Shapely spatial rule validation, gap/overlap/crossing conflict detection | Planned |
| Phase 8 | Document Intelligence Pipeline | OCR, structured deed extraction, spatial-document reconciliation alerts | Planned |
| Phase 9 | Bi-Temporal Change Detection | Multi-survey differential comparison, unpermitted construction detection | Planned |
| Phase 10 | Underground Infrastructure | Utility 3D linestrings (water, power, gas, telecom), depth & clash detection | Planned |
| Phase 11 | Citizen & Government Workflows | Discrepancy reporting, officer adjudication queue, audit-logged approvals | Planned |
| Phase 12 | Technical 3D Property Identifier | Algorithmic hierarchical identifier generation (GV-P...-B...-F...-U...) | Planned |
| Phase 13 | Full Audit & Versioning System | Append-only event store, historical geometry rollbacks, temporal queries | Planned |
| Phase 14 | Integration & End-to-End Testing | Automated pipeline from raw survey to approved 3D cadastral record | Planned |
| Phase 15 | Production Hardening & Deployment | High-availability PostGIS, MinIO/S3 object storage, Celery scale, security audit | Planned |

---

## 2. Phase 1: Platform Foundation (Detailed Specification)

### 2.1 Scope & Objectives
1. Monorepo architecture with distinct layers (`frontend`, `backend`, `database`, `docker`, `tests`).
2. PostgreSQL database with active PostGIS extension.
3. Database migrations via Alembic.
4. User, Organization, Jurisdiction, and AuditLog relational models.
5. Secure Authentication: Password hashing (Argon2 / Bcrypt), JWT access and refresh tokens.
6. Role-Based Access Control (RBAC): `CITIZEN`, `SURVEYOR`, `GOVERNMENT_OFFICER`, `ADMIN`, `URBAN_PLANNER`.
7. Standardized API architecture with FastAPI, Pydantic schemas, dependency injection, and uniform JSON errors.
8. Structured logging with request tracing.
9. Health checks (`/health/live`, `/health/ready`).
10. Frontend React + TypeScript application with Tailwind CSS, authentication state, and role-aware navigation.
11. Docker Compose environment for local and containerized orchestration.
12. Comprehensive automated unit and integration tests.
13. Idempotent development seed scripts with documented test credentials.

### 2.2 Phase 1 Deliverables
- `backend/app/main.py`: FastAPI entrypoint with middleware, routers, and global exception handlers.
- `backend/app/core/config.py`: Typed configuration via Pydantic settings.
- `backend/app/core/security.py`: Password hashing and JWT generation/verification.
- `backend/app/core/errors.py`: Custom exceptions and standardized error response handlers.
- `backend/app/models/`: SQLAlchemy 2.0 models for User, Organization, Jurisdiction, and AuditLog.
- `backend/migrations/`: Alembic migrations configuration and initial schema migration.
- `frontend/src/`: React 18 / Vite frontend with auth context, protected routes, and dashboard shell.
- `database/seeds/seed.py`: Idempotent data seeder.
- `docker-compose.yml`: Multi-container definition (backend, frontend, postgres/postgis, redis).
- `tests/`: Pytest backend suite and Vitest frontend suite.

### 2.3 Phase 1 Phase-Gate Criteria
A phase cannot be marked complete without meeting all criteria:
- [x] Database migrations execute cleanly from scratch (`alembic upgrade head`).
- [x] PostGIS extension verified active in PostgreSQL.
- [x] All 5 user roles seed and authenticate via JWT.
- [x] Unauthenticated and unauthorized requests rejected with standard 401/403 responses.
- [x] Frontend protected routes prevent unauthenticated access.
- [x] Admin can list, activate/deactivate, and change roles of users.
- [x] Audit log captures security events (logins, role changes, deactivations).
- [x] Automated backend tests execute and pass 100%.
- [x] Frontend builds cleanly without TypeScript or bundling errors.
- [x] Complete Phase 1 demo workflow verified end-to-end.

---

## 3. Phase 2: Property, Parcel & 2D GIS Foundation (Detailed Specification)

### 3.1 Scope & Objectives
1. Authoritative 2D cadastral parcel data model with PostGIS 4326 geometries, geodesic area calculation on WGS84 ellipsoid, and centroid calculation.
2. Property and building footprint relational models with foreign key integrity to underlying cadastral parcels.
3. Strict spatial validation engine detecting self-intersections (bowtie polygons), invalid boundaries, out-of-jurisdiction polygons, and area overlaps.
4. Comprehensive 2D GIS REST API endpoints:
   - Cadastral Parcel CRUD & search (`/api/v1/parcels`)
   - Property CRUD & search (`/api/v1/properties`)
   - Building Footprint CRUD & search (`/api/v1/buildings`)
   - Viewport-bounded GeoJSON feature collections (`/api/v1/map/parcels`, `/api/v1/map/buildings`, `/api/v1/map/boundaries`)
   - Spatial identify & validation tools (`/api/v1/spatial/identify`, `/api/v1/spatial/validate`, `/api/v1/spatial/check-overlap`)
   - GIS batch GeoJSON ingestion and export (`/api/v1/gis/import`, `/api/v1/gis/export`)
5. Interactive 2D GIS frontend canvas with layer controls (boundaries, parcels, footprints, grid), debounced multi-entity search, interactive polygon digitization, and GeoJSON exchange.
6. Role-Based Access Control enforcing Citizen read-only permissions and Editor (Admin, Officer, Surveyor) mutation permissions.
7. Full audit logging for spatial and cadastral lifecycle actions.

### 3.2 Phase 2 Phase-Gate Criteria
- [x] Database migration `002_phase2_cadastral_gis` executes cleanly (`alembic upgrade head`).
- [x] PostGIS geometries with GiST spatial indexing and SQLite SafeGeometry dual-dialect support.
- [x] Authoritative geodesic area and centroid calculations on WGS84 ellipsoid.
- [x] Self-intersecting bowtie polygons and area overlaps strictly rejected.
- [x] Interactive 2D GIS canvas with pan, zoom, layer controls, and coordinate HUD.
- [x] Interactive polygon digitization with live spatial validation.
- [x] GeoJSON batch import with detailed acceptance/rejection summary report.
- [x] GeoJSON cadastre export with jurisdiction and status filters.
- [x] RBAC enforcement verified (Citizen read-only, Editor full GIS mutation).
- [x] Full security audit logging for all Phase 2 cadastral operations.
- [x] Automated backend tests pass 100% (46/46 passed).
- [x] Automated frontend unit tests pass 100% (4/4 passed).
- [x] Automated end-to-end Phase 2 demo script passes 100% (17/17 checks passed).
- [x] Both backend and frontend running live on localhost (`http://localhost:8000`, `http://localhost:5173`).

---

## 4. Phase Transition Rules

1. **No Leakage**: Features designated for Phase 3+ (CesiumJS 3D digital twin, floor/unit vertical mapping, LiDAR point clouds, AI building extraction, ULPIN) must not be simulated with hardcoded mocks or dummy buttons.
2. **Backward Compatibility**: Subsequent phases must never break the foundation established in Phases 1 and 2.
3. **Database Integrity**: All future schema modifications must occur strictly via versioned Alembic migration scripts.
4. **Authoritative Gate**: Advancement to Phase 3 requires explicit developer/stakeholder sign-off on the Phase 2 Completion Report.

