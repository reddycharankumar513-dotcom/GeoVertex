# GEOVERTEX
## MASTER SYSTEM ARCHITECTURE

Version: 1.0

---

# 1. ARCHITECTURAL PRINCIPLE

GeoVertex shall be modular.

The architecture must allow:

- GIS
- AI
- 3D visualization
- Property management
- Survey workflows
- Document processing
- Change detection
- Government workflows

to evolve independently.

Avoid building the entire system as one monolithic application file.

---

# 2. HIGH-LEVEL ARCHITECTURE

                         GEOVERTEX
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
       CITIZEN            SURVEYOR            OFFICER
          │                  │                  │
          └──────────────────┼──────────────────┘
                             ↓
                   WEB / MOBILE CLIENT
                             ↓
                    React + TypeScript
                             ↓
                ┌──────────────────────┐
                │  API / BFF LAYER     │
                │      FastAPI         │
                └──────────────────────┘
                             ↓
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ↓                    ↓                    ↓
 PROPERTY DOMAIN        GIS DOMAIN            AI DOMAIN
        │                    │                    │
        ↓                    ↓                    ↓
Property Service       Spatial Service       AI Service
Parcel Service         Geometry Engine       Building AI
Building Service       CRS Engine             Floor AI
Floor Service           Validation             Change AI
Unit Service
Survey Service
Review Service
                             │
        ┌────────────────────┼────────────────────┐
        ↓                    ↓                    ↓
   DOCUMENT AI          JOB PROCESSING       NOTIFICATION
        │                    │                    │
        ↓                    ↓                    ↓
 OCR / Extraction       Redis + Workers       Notification
 Comparison             Celery                Service
        │                    │
        └────────────────────┼────────────────────┘
                             ↓
                    DATA STORAGE LAYER
                             │
            ┌────────────────┼────────────────┐
            ↓                ↓                ↓
       PostgreSQL         PostGIS        Object Storage
       relational         spatial         images/docs/
       data               data            point clouds
            │
            ↓
       Audit / Version Store

---

# 3. FRONTEND ARCHITECTURE

Technology:

React
TypeScript
Vite
Tailwind CSS
CesiumJS
MapLibre/OpenLayers
TanStack Query
React Hook Form
Zod

Structure:

frontend/
src/
app/
components/
layouts/
pages/
features/
hooks/
services/
api/
store/
types/
utils/

Feature modules:

features/
auth/
dashboard/
properties/
parcels/
buildings/
floors/
units/
maps/
threeD/
surveys/
ai/
documents/
changes/
utilities/
reviews/
audit/
administration/

Each feature should own:

* components
* hooks
* API calls
* types
* validation
* state

---

# 4. BACKEND ARCHITECTURE

Use FastAPI.

Structure:

backend/
app/
main.py

    core/
        config.py
        security.py
        logging.py

    api/
        v1/
            auth.py
            properties.py
            parcels.py
            buildings.py
            floors.py
            units.py
            surveys.py
            ai.py
            documents.py
            changes.py
            utilities.py
            validation.py
            reviews.py
            audit.py
            dashboard.py

    models/

    schemas/

    repositories/

    services/

    workflows/

    gis/

    ai/

    documents/

    audit/

    notifications/

---

# 5. SERVICE ARCHITECTURE

Use:

API
↓
SERVICE
↓
REPOSITORY
↓
DATABASE

Example:

POST /properties
    ↓
PropertyRouter
    ↓
PropertyService
    ↓
PropertyRepository
    ↓
PostgreSQL/PostGIS

Do not put database logic directly inside route handlers.

---

# 6. DOMAIN SERVICES

PropertyService
ParcelService
BuildingService
FloorService
UnitService
SurveyService
ReviewService
ApprovalService
AuditService
NotificationService
DocumentService
UtilityService
ChangeDetectionService
IdentifierService

---

# 7. GIS ARCHITECTURE

GIS stack:

PostGIS
GEOS
Shapely
GeoPandas
GDAL
pyproj
PDAL
Open3D

Pipeline:

RAW DATA
↓
FILE VALIDATION
↓
CRS DETECTION
↓
CRS NORMALIZATION
↓
GEOMETRY VALIDATION
↓
SPATIAL TRANSFORMATION
↓
DATABASE INGESTION
↓
SPATIAL INDEXING

---

# 8. GIS DATA TYPES

Support:

Point
LineString
Polygon
MultiPolygon

For 3D:

PointZ
LineStringZ
PolygonZ
3D mesh/volumetric representations where appropriate

Always preserve:

* CRS
* Source
* Capture date
* Accuracy metadata
* Dataset version

---

# 9. POSTGIS ARCHITECTURE

PostgreSQL stores:

* Users
* Properties
* Metadata
* Workflow
* Documents metadata
* AI metadata
* Audit

PostGIS stores:

* Parcel geometry
* Building geometry
* Floor geometry
* Unit geometry
* Utility geometry
* Survey geometry
* Change geometry

Create GIST indexes.

Example:

CREATE INDEX idx_parcels_geometry
ON parcels
USING GIST (geometry);

---

# 10. 3D ARCHITECTURE (Phase 3 Core Implementation)

CesiumJS is the authoritative 3D WebGL visualization engine for GeoVertex.

### 10.1 Data Flow Pipeline
```
PostgreSQL / PostGIS (Authoritative Spatial Truth)
  ├── 2D Building Footprints (geometry EPSG:4326)
  └── 2.5D Building Representations (base_elevation_m, height_m, vertical_datum)
        │
        ▼
FastAPI 3D Service (/api/v1/3d)
  ├── Geometry 3D Engine (geodesic area, volume m³, bbox [minLon, minLat, minAlt, maxLon, maxLat, maxAlt])
  └── Cesium Extrusion Formatter (exterior rings, interior hole polygons, extrudedHeight, height)
        │
        ▼
CesiumJS WebGL Viewer (Frontend /digital-twin)
  ├── Carto Dark Matter / OSM Tile Imagery (Offline-capable, token-free)
  ├── Extruded Building Polygons & Ground Parcel Boundaries
  ├── 3D Measurement Tools (Euclidean Distance & Vertical Height Delta)
  ├── Interactive Feature Raycast & Selection HUD
  └── 2D/3D Dual-Viewport URL Sync (?building_id=...&parcel_id=...)
```

### 10.2 Vertical Datums & Reference Systems
The 3D engine strictly tracks vertical reference datums:
- `WGS84_ELLIPSOID`: Global GPS ellipsoidal height datum.
- `EGM96_GEOID`: Global gravitational geoid model.
- `LOCAL_MSL`: Local Mean Sea Level height.
- `GROUND_RELATIVE`: Height relative to local terrain surface.

---

# 11. 3D DIGITAL TWIN & VERTICAL PROPERTY HIERARCHY ARCHITECTURE

The 3D Digital Twin integrates horizontal 2D cadastre with vertical property volumetric structures:

### 11.1 Layered Spatial Stack
1. **Ground Context**: Authoritative Cadastral Parcel boundaries projected at ground altitude ($Z=0.0$).
2. **Building Volume (2.5D)**: Outer building footprint envelope extruded from $H_{base}$ to $H_{base} + H_{roof}$.
3. **Vertical Floor Slabs**: Discrete horizontal slices $[Z_{min}, Z_{max}]$ bounded by the building footprint.
4. **Property Unit Prisms**: Subdivided interior polygons extruded between floor bounds $[Z_{min}, Z_{max}]$, representing distinct legal property interests (apartments, retail suites, commercial offices).

### 11.2 Hierarchical Data Structure
```
Cadastral Parcel (2D Surface)
  └── Building Footprint (Ground Envelope)
        └── Building 3D Representation (Extrusion Height, Base Elevation, Datum)
              └── Floor Slabs [Z_min .. Z_max]
                    └── Property Units (Subdivided Prisms)
                          └── Legal Property Record (Deed / Ownership)
```

### 11.3 Vertical & Topological Invariant Rules
- **Stacking Continuity & Non-Clash**: Two floors belonging to the same building cannot overlap in vertical elevation:
  $$\forall i \neq j, \quad (Z_{min}^{(i)} < Z_{max}^{(j)}) \land (Z_{max}^{(i)} > Z_{min}^{(j)}) = \text{False}$$
- **Footprint Containment**: $\text{ST\_Within}(\text{FloorGeometry}, \text{BuildingGeometry}) = \text{True}$
- **Unit Containment**: $\text{ST\_Within}(\text{UnitGeometry}, \text{FloorGeometry}) = \text{True}$
- **Unit Interior Disjointness**: On any given floor, unit horizontal geometries must not overlap:
  $$\forall u_1, u_2 \in \text{Floor}, \quad \text{Area}(u_1 \cap u_2) = 0$$

### 11.4 Interactive 3D Viewing Modes
- **Exploded View Mode**: Vertically offsets each floor slab by $\Delta Z = \text{floor\_number} \times 12.0\text{m}$, allowing instant inspection of stacked floor layouts.
- **Isolated Floor Mode**: Clamps camera view and entity visibility to a single selected floor slab and its contained unit prisms while rendering parent building as a translucent wireframe envelope ($20\%$ opacity).
- **Unit Tree Explorer**: Bi-directional tree synchronization linking Cesium entity selection to the collapsible hierarchy tree view.

Subsequent phases will layer point clouds, AI segmentation, and utility linestrings.

---

# 12. SURVEYOR FIELD WORKFLOW & GEOSPATIAL DATA COLLECTION ARCHITECTURE (Phase 5)

The Surveyor Field Workflow architecture enables accredited cadastral surveyors to capture ground truth observations and photo evidence on mobile/tablet devices in both connected and disconnected environments.

### 12.1 End-to-End System Topology
```
                     FIELD ENVIRONMENT (PWA / MOBILE BROWSER)
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  HTML5 Geolocation (watchPosition)  │  Camera API (capture="environment")   │
  │  Latitude, Longitude, Altitude      │  Raw JPEG / PNG / WebP binary         │
  │  Horizontal & Vertical Accuracy     │  Web Cryptography API (SHA-256 Hash)  │
  └───────────────────────┬─────────────────────────────────┬───────────────────┘
                          │                                 │
                          ▼                                 ▼
              ┌────────────────────────────────────────────────────────┐
              │           FRONTEND FIELD WORKSPACE LAYER               │
              │  - SurveyMap (2D GPS canvas & boundary overlays)       │
              │  - SurveyFormEngine (Observation capture)              │
              │  - EvidenceGallery (Photo capture & SHA-256 display)   │
              │  - ValidationChecklist (Pre-submission gate)          │
              └───────────────────────────┬────────────────────────────┘
                                          │
                     ┌────────────────────┴────────────────────┐
                     ▼ (Online)                                ▼ (Offline)
           ┌──────────────────────┐                  ┌───────────────────┐
           │ REST API Client      │                  │ IndexedDB Store   │
           │ (Axios / Fetch)      │                  │ (geovertex_offline)│
           └──────────┬───────────┘                  └─────────┬─────────┘
                      │                                        │ (When online)
                      │                                        ▼
                      │                              ┌───────────────────┐
                      │                              │ Offline Sync Hook │
                      │                              │ (Auto-Batch Queue)│
                      │                              └─────────┬─────────┘
                      │                                        │
                      ▼                                        ▼
    ================== HTTPS / JSON & MULTIPART BOUNDARY ======================
                      │                                        │
                      ▼                                        ▼
          ┌──────────────────────┐                  ┌───────────────────┐
          │ Surveys Router       │                  │ Sync Router       │
          │ (/api/v1/surveys)    │                  │ (/api/v1/sync)    │
          └──────────┬───────────┘                  └─────────┬─────────┘
                     │                                        │
                     ▼                                        ▼
          ┌─────────────────────────────────────────────────────────────┐
          │                    BACKEND SERVICE LAYER                    │
          │  - SurveyService (Lifecycle coordinator)                    │
          │  - SurveyStateMachine (Strict status guard)                 │
          │  - SurveyValidationService (Discrepancy engine)             │
          │  - SurveySyncService (Atomic batch processor)               │
          │  - StorageService (SHA-256 verification & storage)          │
          └──────────────────────────────┬──────────────────────────────┘
                                         │
                     ┌───────────────────┴───────────────────┐
                     ▼                                       ▼
          ┌──────────────────────┐               ┌──────────────────────┐
          │ Relational Database  │               │ Secure Disk Storage  │
          │ PostgreSQL / PostGIS │               │ uploads/evidence/    │
          │ - survey_projects    │               │ - {session_id}/      │
          │ - survey_assignments │               │   {uuid}_{filename}  │
          │ - survey_sessions    │               └──────────────────────┘
          │ - survey_observations│
          │ - survey_evidence    │
          │ - survey_submissions │
          │ - sync_operations    │
          │ - audit_logs         │
          └──────────────────────┘
```

### 12.2 Architectural Components

#### 1. Progressive Web App (PWA) & Offline-First Engine
- **IndexedDB Client Storage**: Built on `idb`, storing cached assignments, active sessions, draft observations, and pending mutation operations.
- **Client Idempotency**: Each mutation is tagged with a client-generated UUID (`operation_id`). Re-sending a batch upon network jitter is guaranteed idempotent.
- **Dynamic Network Monitor**: The `useOnlineStatus` hook tracks browser `navigator.onLine` and `online`/`offline` window events. Upon re-establishing connection, pending sync operations are flushed automatically.

#### 2. GNSS Quality Classification & Spatial Canvas
- **Real-Time GPS Tracking**: HTML5 Geolocation API with `enableHighAccuracy: true`, continuous heading, and altitude tracking.
- **Accuracy Halo**: Visualized dynamically on the 2D survey map. Observation accuracy is categorized into 4 tiers:
  - High Precision ($<1\text{m}$)
  - Differential ($1-3\text{m}$)
  - Standalone GNSS ($3-10\text{m}$)
  - Coarse / Unacceptable ($>10\text{m}$)
- **Boundary Overlays**: Vector rendering of parcel polygon, building footprint, GPS location dot, accuracy buffer, and tagged observation pins.

#### 3. Evidence Integrity & Cryptographic Chain of Custody
- **Browser-Side SHA-256 Calculation**: Calculated via `crypto.subtle.digest('SHA-256', buffer)` prior to transmission.
- **Server Verification**: The backend recomputes the SHA-256 digest on the incoming stream. Mismatches are rejected immediately (`400 Bad Request`).
- **Object Storage**: Stored in partitioned directory structures (`uploads/evidence/{session_id}/...`) with restricted download endpoints enforcing role authorization.

#### 4. Cadastral Validation & Discrepancy Engine
- Deterministic comparison between empirical field measurements and authoritative cadastral records.
- Compares measured height vs official building height with percentage delta calculation.
- Compares field floor counts vs registered floors.
- Identifies boundary discrepancy flags and potential setback encroachments.
- Generates pre-submission validation summaries with explicit `can_submit` gating.

#### 5. Frozen Snapshot Submissions & Cadastral Separation
- **Submission Snapshot**: Submissions freeze all observations, evidence links, and discrepancy reports into an immutable JSON document.
- **Version Numbering**: Sequential version counter ($V_1, V_2, \dots$) preserves full revision history if an officer requests amendments.
- **Cadastral Separation Principle**: Field surveys serve as legal evidence snapshots. Government Officer approval marks the submission as `APPROVED` and records an immutable audit log entry. It does **not** directly mutate authoritative parcel or building footprints in PostGIS without formal legislative cadastral amendment procedures.

---

# 13. AI ARCHITECTURE

AI service:

ai/
models/
preprocessing/
inference/
evaluation/
building_detection/
floor_detection/
change_detection/

Common interface:

Model
├── load()
├── preprocess()
├── predict()
├── postprocess()
├── confidence()
└── metadata()

All AI predictions must contain:

* model
* model_version
* input_dataset
* timestamp
* prediction
* confidence

---

# 13. BUILDING AI

Input:

Drone / Satellite / LiDAR

Output:

Building geometry

Pipeline:

IMAGE
↓
PREPROCESS
↓
MODEL
↓
SEGMENTATION
↓
POSTPROCESS
↓
VECTOR GEOMETRY
↓
CONFIDENCE
↓
REVIEW

---

# 14. FLOOR AI

Input:

Point cloud
+
Building geometry
+
Optional floor plan

Output:

Floor geometries

Pipeline:

POINT CLOUD
↓
FILTER
↓
HEIGHT ANALYSIS
↓
FLOOR DETECTION
↓
GEOMETRY
↓
CONFIDENCE
↓
REVIEW

---

# 15. CHANGE DETECTION ARCHITECTURE

Historical:

V1

Current:

V2

Pipeline:

V1
+
V2
↓
CRS ALIGNMENT
↓
GEOMETRY NORMALIZATION
↓
DIFFERENCE
↓
CHANGE CLASSIFICATION
↓
CONFIDENCE
↓
REVIEW

---

# 16. DOCUMENT AI ARCHITECTURE

DOCUMENT
↓
UPLOAD
↓
VALIDATION
↓
OCR
↓
TEXT
↓
FIELD EXTRACTION
↓
STRUCTURED JSON
↓
PROPERTY MATCHING
↓
SPATIAL COMPARISON
↓
ALERT

---

# 17. BACKGROUND PROCESSING ARCHITECTURE

API must not process large AI/GIS operations synchronously.

Architecture:

Frontend
↓
API
↓
Create Job
↓
Redis
↓
Celery Worker
↓
Processing
↓
Database/Object Storage
↓
Job Completed
↓
Notification

Job table:

id
type
status
progress
created_by
started_at
completed_at
error
result_reference

---

# 18. OBJECT STORAGE

Use object storage for:

* Drone imagery
* Orthophotos
* LiDAR
* LAS/LAZ
* Documents
* Generated reports
* AI artifacts

Development:

MinIO/local storage.

Production:

S3-compatible storage.

PostgreSQL stores only metadata and object references.

---

# 19. AUTHENTICATION ARCHITECTURE

JWT authentication.

Flow:

LOGIN
↓
ACCESS TOKEN
↓
API
↓
JWT VALIDATION
↓
USER
↓
ROLE
↓
PERMISSION
↓
RESOURCE

Backend must enforce authorization.

---

# 20. RBAC

Roles:

CITIZEN
SURVEYOR
GOVERNMENT_OFFICER
ADMIN
URBAN_PLANNER

Example:

Citizen:
READ permitted property information.

Surveyor:
CREATE/EDIT survey.

Officer:
REVIEW/APPROVE.

Admin:
SYSTEM MANAGEMENT.

Planner:
SPATIAL READ/ANALYSIS.

---

# 21. WORKFLOW ENGINE

Property workflow:

DRAFT
↓
PROCESSING
↓
AI_COMPLETED
↓
SURVEYOR_REVIEW
↓
SUBMITTED
↓
OFFICER_REVIEW
↓
APPROVED

Alternative:

REJECTED
REVISION_REQUIRED

State transitions must be validated on the backend.

---

# 22. AUDIT ARCHITECTURE

Every important action creates:

AuditEvent

Fields:

event_id
actor_id
entity_type
entity_id
action
old_value
new_value
reason
timestamp
source

Audit records should be append-oriented.

---

# 23. VERSION ARCHITECTURE

Every important spatial record supports:

version_number
created_at
created_by
source
geometry
status

Example:

PROPERTY V1
PROPERTY V2
PROPERTY V3

Do not overwrite historical authoritative versions.

---

# 24. API ARCHITECTURE

Base URL:

/api/v1

Domain grouping:

/auth
/users
/properties
/parcels
/buildings
/floors
/units
/surveys
/ai
/documents
/changes
/utilities
/validation
/reviews
/audit
/dashboard

Use:

* pagination
* filtering
* sorting
* validation
* consistent response format
* error codes

---

# 25. ERROR ARCHITECTURE

Standard error:

{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Resource was not found",
    "details": {}
  }
}

Do not expose stack traces to users.

---

# 26. NOTIFICATION ARCHITECTURE

Events:

AI_JOB_COMPLETED
AI_JOB_FAILED
SURVEY_SUBMITTED
REVIEW_ASSIGNED
REVISION_REQUIRED
PROPERTY_APPROVED
PROPERTY_REJECTED
CHANGE_DETECTED
DOCUMENT_MISMATCH
TOPOLOGY_CONFLICT

Channels can initially be:

In-app

Later:

Email
SMS
Push

---

# 27. SEARCH ARCHITECTURE

Global search:

Technical 3D ID
Parcel ID
Survey number
Property ID
Building ID
Unit ID

Future:

Spatial search
Coordinates
Nearby properties

---

# 28. IMPORT PIPELINE

Supported inputs:

GeoJSON
CSV
KML/KMZ
Shapefile
GeoTIFF
LAS/LAZ

Pipeline:

UPLOAD
↓
VALIDATE
↓
DETECT FORMAT
↓
READ CRS
↓
TRANSFORM
↓
VALIDATE GEOMETRY
↓
STORE
↓
INDEX
↓
READY

---

# 29. EXPORT PIPELINE

Export:

GeoJSON
CSV
PDF report

3D exports depend on supported implementation.

Export must respect user permissions.

---

# 30. OBSERVABILITY

Implement:

Structured logs
Request IDs
Job IDs
Error logs
Health checks
Worker monitoring

Endpoints:

/health
/ready

Docker health checks should be configured.

---

# 31. SECURITY ARCHITECTURE

Implement:

HTTPS
JWT
RBAC
Password hashing
CORS
Secure headers
Input validation
File validation
File size limits
MIME validation
Rate limiting
Secret management

Never commit:

Passwords
JWT secrets
API keys
Cloud credentials

---

# 32. DEPLOYMENT ARCHITECTURE

Development:

Docker Compose

Services:

frontend
backend
postgres
redis
worker
minio
nginx

Production:

Client
↓
Nginx / Load Balancer
↓
Frontend
↓
API
↓
Application Services
↓
PostGIS
Redis
Object Storage
Workers

---

# 33. CI/CD

GitHub Actions:

1. Checkout
2. Install dependencies
3. Lint
4. Type checking
5. Unit tests
6. Integration tests
7. Build frontend
8. Build Docker images
9. Security checks
10. Deploy

---

# 34. TEST ARCHITECTURE

Backend:

pytest

Frontend:

Vitest
React Testing Library

E2E:

Playwright

GIS:

Geometry test suite

AI:

Model/pipeline tests

Critical test:

LOGIN
→ PROPERTY
→ PARCEL
→ BUILDING
→ FLOOR
→ UNIT
→ ID
→ SURVEY
→ AI
→ VALIDATION
→ REVIEW
→ APPROVAL
→ AUDIT

---

# 35. DEVELOPMENT PHASE ARCHITECTURE

PHASE 1
Foundation

PHASE 2
Property + Parcel GIS

PHASE 3
3D Digital Twin

PHASE 4
Building + Floor + Unit

PHASE 5
Surveyor Workflow

PHASE 6
AI Building/Floor Extraction

PHASE 7
Topology Validation

PHASE 8
Document Intelligence

PHASE 9
Change Detection

PHASE 10
Underground Infrastructure

PHASE 11
Citizen + Government Workflow

PHASE 12
Technical 3D Identifier

PHASE 13
Audit + Versioning

PHASE 14
Integration + Testing

PHASE 15
Production Deployment

---

# 36. PHASE GATE

A phase cannot be considered complete until:

✓ Requirements implemented
✓ Database migration works
✓ APIs work
✓ UI works
✓ Tests pass
✓ No critical errors
✓ Documentation updated
✓ Demo workflow works
✓ No regression in previous phase

Only then:

NEXT PHASE

---

# 37. REPOSITORY ARCHITECTURE

GeoVertex/

├── frontend/
├── backend/
├── database/
├── docker/
├── tests/
├── docs/
│   ├── MASTER_PRD.md
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT_ROADMAP.md
│   ├── DATA_MODEL.md
│   ├── API_CONTRACT.md
│   ├── AI_PIPELINE.md
│   ├── GIS_PIPELINE.md
│   └── WORKFLOWS.md
│
├── docker-compose.yml
├── .env.example
└── README.md

---

# 38. ARCHITECTURAL RULES

1. Do not put business logic in API routes.
2. Do not put secrets in code.
3. Do not fake AI results.
4. Do not fake GIS coordinates.
5. Do not store large files directly in PostgreSQL.
6. Do not perform long-running processing in API requests.
7. Do not bypass backend authorization.
8. Do not silently overwrite historical property records.
9. Do not hard-code the technical ID format.
10. Do not couple the system to one AI model.
11. Preserve CRS metadata.
12. Use PostGIS for authoritative spatial operations.
13. Use workers for heavy processing.
14. Keep phases independently testable.
15. Never break completed functionality while implementing a new phase.

---

# 39. FINAL ARCHITECTURE

REAL WORLD
↓
GNSS / DRONE / LiDAR / SATELLITE / GIS / BIM / DOCUMENTS
↓
DATA INGESTION
↓
QUALITY CONTROL
↓
CRS NORMALIZATION
↓
GIS / POINT-CLOUD PROCESSING
↓
AI EXTRACTION
↓
3D DIGITAL TWIN
↓
PARCEL
↓
BUILDING
↓
FLOOR
↓
UNIT
↓
UTILITY
↓
TOPOLOGY VALIDATION
↓
DOCUMENT INTELLIGENCE
↓
CHANGE DETECTION
↓
CONFIDENCE
↓
TECHNICAL 3D PROPERTY ID
↓
SURVEYOR REVIEW
↓
OFFICER REVIEW
↓
VERSIONED POSTGIS DATABASE
↓
CITIZEN / SURVEYOR / GOVERNMENT APPLICATIONS

---

# 40. PRODUCTION DEPLOYMENT & DEVOPS ARCHITECTURE (PHASE 15)

The production deployment architecture establishes an isolated, defense-in-depth, high-availability platform:

1. **Ingress & Edge Security Tier**:
   - Nginx reverse proxy with TLS 1.3 termination, HSTS (`max-age=31536000`), and Cesium-compatible Content Security Policy (CSP).
   - In-memory rate limiting zones protecting authentication (`10r/s`) and general API (`50r/s`).
   - Gzip compression and long-term caching for immutable frontend assets (`/assets/`).

2. **Application & Processing Tier**:
   - FastAPI application server running 4 Uvicorn ASGI workers with non-root security context (`geovertex`, UID 10001).
   - Celery background worker pool handling asynchronous spatial tasks, OCR, and AI candidate processing.
   - Dual health probes: `/health/live` (process liveness) and `/health/ready` (system readiness).
   - Prometheus metrics exposition (`/metrics`).

3. **Data & Storage Persistence Tier**:
   - PostgreSQL 16 + PostGIS 3.4 with async connection pooling (`pool_size=20`, `max_overflow=10`, `pool_pre_ping=True`).
   - Redis 7 with Append-Only File (AOF) persistence for caching and task brokerage.
   - Multi-backend object storage (`DocumentStorageService`) supporting local filesystem, AWS S3, and MinIO with SHA-256 integrity verification.

4. **Disaster Recovery & Operational Governance**:
   - Automated database backup tool (`backend/scripts/backup.py`) producing compressed archives with SHA-256 digests and JSON metadata manifests.
   - Disaster recovery restore tool (`backend/scripts/restore.py`) enforcing pre-restore checksum verification and mandatory confirmation flags.
   - Target objectives: Recovery Point Objective (RPO) $\le 1\text{ hour}$, Recovery Time Objective (RTO) $\le 15\text{ minutes}$.
   - Comprehensive CI/CD pipeline (`.github/workflows/ci.yml`) validating tests, migrations, types, and container builds.

