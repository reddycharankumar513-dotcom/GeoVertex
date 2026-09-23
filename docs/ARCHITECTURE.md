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

# 10. 3D ARCHITECTURE

CesiumJS is the primary 3D visualization engine.

Data flow:

PostGIS
↓
3D API
↓
GeoJSON / 3D Tiles / supported geometry
↓
CesiumJS
↓
3D View

The system should eventually support tiled 3D datasets for large-scale visualization.

---

# 11. 3D DIGITAL TWIN ARCHITECTURE

The digital twin is composed of:

Terrain
+
Parcel
+
Building
+
Floor
+
Unit
+
Utility

Each object has:

* ID
* Geometry
* Source
* Version
* Confidence
* Verification status

---

# 12. AI ARCHITECTURE

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
