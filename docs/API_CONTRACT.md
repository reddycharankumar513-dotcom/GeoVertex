# GEOVERTEX: API CONTRACT SPECIFICATION
## RESTful v1 Endpoints, Schemas, Status Codes & Error Formats

Version: 1.0  
Status: Authoritative API Specification  
Base URL: `/api/v1`

---

## 1. General Principles

### 1.1 Response Envelope
Success responses return raw resource objects or collections with pagination metadata.

```json
{
  "items": [],
  "total": 12,
  "page": 1,
  "size": 20
}
```

### 1.2 Standard Error Response
All 4xx and 5xx responses strictly adhere to the unified error schema:

```json
{
  "error": {
    "code": "STRING_ERROR_CODE",
    "message": "Human-readable explanation of the error condition.",
    "details": {}
  }
}
```

| HTTP Status | Typical Error Code | Description |
|---|---|---|
| 400 | `BAD_REQUEST` | Validation or malformed syntax error |
| 401 | `UNAUTHORIZED` | Missing, expired, or invalid JWT token |
| 403 | `FORBIDDEN` | Insufficient role permissions for resource |
| 404 | `NOT_FOUND` | Target entity does not exist |
| 409 | `CONFLICT` | Unique key violation (e.g. email or code already exists) |
| 422 | `UNPROCESSABLE_ENTITY` | Pydantic schema validation failure |
| 429 | `RATE_LIMITED` | Too many requests on sensitive endpoint |
| 500 | `INTERNAL_SERVER_ERROR` | Unhandled server exception (redacted details) |

---

## 2. Health & System Observability

### `GET /health` / `GET /health/live`
- **Purpose**: Liveness probe for orchestration and container runtimes.
- **Auth**: Public
- **Response `200 OK`**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-09-22T15:20:00Z"
}
```

### `GET /health/ready` / `GET /api/v1/health`
- **Purpose**: Readiness probe verifying connectivity to PostgreSQL, PostGIS, and Redis.
- **Auth**: Public
- **Response `200 OK`**:
```json
{
  "status": "ready",
  "database": {
    "connected": true,
    "postgis_available": true,
    "postgis_version": "3.4.0"
  },
  "cache": {
    "connected": true
  },
  "timestamp": "2026-09-22T15:20:00Z"
}
```

---

## 3. Authentication & Session Management

### `POST /api/v1/auth/register`
- **Purpose**: Register a public citizen account.
- **Auth**: Public
- **Request Body**:
```json
{
  "email": "citizen@domain.com",
  "username": "citizen_user",
  "full_name": "Ravi Kumar",
  "password": "SecurePassword123!",
  "phone": "+919876543210"
}
```
- **Response `201 Created`**: User profile (sans credentials).

### `POST /api/v1/auth/login`
- **Purpose**: Authenticate credentials and receive JWT access/refresh token pair.
- **Auth**: Public
- **Request Body**:
```json
{
  "username_or_email": "admin@geovertex.local",
  "password": "SecurePassword123!"
}
```
- **Response `200 OK`**:
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "d8a7c2e...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "c1f7a050-4eb6-4f40-b6f1-a1e1bf83bb92",
    "email": "admin@geovertex.local",
    "username": "admin",
    "full_name": "System Administrator",
    "role": "ADMIN",
    "is_active": true
  }
}
```

### `POST /api/v1/auth/refresh`
- **Purpose**: Exchange a valid refresh token for a newly minted access token.
- **Auth**: Public (requires refresh token in payload)
- **Request Body**:
```json
{
  "refresh_token": "d8a7c2e..."
}
```
- **Response `200 OK`**: New token pair.

### `POST /api/v1/auth/logout`
- **Purpose**: Revoke the active refresh token and invalidate current session.
- **Auth**: Bearer Token
- **Response `200 OK`**:
```json
{
  "message": "Logged out successfully"
}
```

### `GET /api/v1/auth/me`
- **Purpose**: Retrieve current authenticated user profile and permissions.
- **Auth**: Bearer Token
- **Response `200 OK`**: Current user details, role, organization, and jurisdiction associations.

---

## 4. User Administration (`/api/v1/users`)

### `GET /api/v1/users`
- **Purpose**: List system users with filtering by role and status.
- **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`)
- **Query Params**: `role`, `is_active`, `page`, `size`
- **Response `200 OK`**: Paginated array of user schemas.

### `PATCH /api/v1/users/{id}/role`
- **Purpose**: Elevate or modify a user's role.
- **Auth**: Bearer Token (`ADMIN` only)
- **Request Body**:
```json
{
  "role": "SURVEYOR"
}
```
- **Response `200 OK`**: Updated user schema.

### `PATCH /api/v1/users/{id}/status`
- **Purpose**: Activate or deactivate a user account.
- **Auth**: Bearer Token (`ADMIN` only)
- **Request Body**:
```json
{
  "is_active": false
}
```
- **Response `200 OK`**: Updated user schema.

---

## 5. Organizations & Jurisdictions

### `GET /api/v1/organizations`
- **Purpose**: List registered cadastral and municipal entities.
- **Auth**: Bearer Token (All authenticated roles)

### `POST /api/v1/organizations`
- **Purpose**: Register a new organization.
- **Auth**: Bearer Token (`ADMIN` only)

### `GET /api/v1/jurisdictions`
- **Purpose**: List administrative territories (wards/districts).
- **Auth**: Bearer Token (All authenticated roles)

### `POST /api/v1/jurisdictions`
- **Purpose**: Register an administrative territory with native SRID and optional boundary.
- **Auth**: Bearer Token (`ADMIN` only)

---

## 6. Audit Logs (`/api/v1/audit`)

### `GET /api/v1/audit`
- **Purpose**: Query security, administrative, spatial, and vertical 3D events.
- **Auth**: Bearer Token (`ADMIN` only)
- **Query Params**: `entity_type`, `action`, `actor_user_id`, `page`, `size`
- **Response `200 OK`**: Paginated list of AuditLog items.

---

## 7. Phase 2 Cadastral GIS Endpoints

### 7.1 Parcels (`/api/v1/parcels`)
- `GET /api/v1/parcels`: List/search parcels with filters (`jurisdiction_id`, `status`, `land_use`, `query`).
- `POST /api/v1/parcels`: Create parcel with strict topology validation (`require_editor`).
- `GET /api/v1/parcels/{id}`: Detailed parcel record with linked properties and buildings.
- `PATCH /api/v1/parcels/{id}`: Update parcel attributes or boundary geometry (`require_editor`).
- `DELETE /api/v1/parcels/{id}`: Soft delete or retire parcel (`require_officer_or_admin`).

### 7.2 Properties (`/api/v1/properties`)
- `GET /api/v1/properties`: List registered legal properties.
- `POST /api/v1/properties`: Register legal property record (`require_editor`).
- `GET /api/v1/properties/{id}`: Property detail.
- `PATCH /api/v1/properties/{id}`: Update property attributes.

### 7.3 Buildings (`/api/v1/buildings`)
- `GET /api/v1/buildings`: List/search building footprints.
- `POST /api/v1/buildings`: Create footprint with containment and overlap validation (`require_editor`).
- `GET /api/v1/buildings/{id}`: Footprint details.
- `PATCH /api/v1/buildings/{id}`: Update footprint geometry.

### 7.4 GIS Spatial & Map Endpoints
- `GET /api/v1/map/layers`: Viewport GeoJSON features (boundaries, parcels, buildings).
- `GET /api/v1/map/identify`: 2D point-in-polygon identification.
- `POST /api/v1/spatial/validate`: Standalone geometry topology validation.
- `GET /api/v1/gis/export/geojson`: Export cadastral datasets as RFC 7946 GeoJSON.
- `POST /api/v1/gis/import/geojson`: Bulk ingest GeoJSON with rollback transaction (`require_editor`).

---

## 8. Phase 3 3D Digital Twin & Vertical GIS Endpoints (`/api/v1/3d`)

### 8.1 `GET /api/v1/3d/scene`
- **Purpose**: Retrieve lightweight, CesiumJS-ready 3D Digital Twin scene payload with 2.5D building extrusions and cadastral parcel wireframes.
- **Auth**: Bearer Token (All authenticated roles)
- **Query Params**:
  - `bbox`: Optional bounding box (`minLon,minLat,maxLon,maxLat`)
  - `jurisdiction_id`: Optional UUID filter
  - `limit`: Integer (default 150, max 500)
- **Response `200 OK`**:
```json
{
  "scene": {
    "crs": "EPSG:4326",
    "vertical_reference": "METERS_ABOVE_GROUND",
    "center": [78.4875, 17.3828, 0.0],
    "bounds": [78.4860, 17.3820, 78.4930, 17.3840],
    "camera_preset": {
      "destination": [78.4875, 17.3810, 450.0],
      "orientation": { "heading": 0.0, "pitch": -45.0, "roll": 0.0 }
    }
  },
  "buildings": [
    {
      "building_id": "7ea68058-3735-4464-aeb2-7be7c6d4a91f",
      "building_reference": "BLD-W101-001",
      "building_type": "COMMERCIAL",
      "status": "EXISTING",
      "parcel_id": "05df3ea9-3fb0-4d46-94e4-e6e2bb0fc59a",
      "parcel_code": "GV-W101-P101",
      "footprint_area_sq_m": 1250.0,
      "volume_cu_m": 56250.0,
      "height": 45.0,
      "height_source": "SURVEY",
      "height_confidence": 0.95,
      "height_unit": "METERS",
      "base_elevation": 0.0,
      "elevation_source": "LOCAL_REFERENCE_PLANE",
      "vertical_reference": "METERS_ABOVE_GROUND",
      "extruded_height": 45.0,
      "centroid": [78.4870, 17.3830, 0.0],
      "bbox_3d": [78.4863, 17.3823, 0.0, 78.4877, 17.3837, 45.0],
      "rings": [
        {
          "exterior": [78.4863, 17.3823, 78.4877, 17.3823, 78.4877, 17.3837, 78.4863, 17.3837, 78.4863, 17.3823],
          "holes": []
        }
      ]
    }
  ],
  "parcels": [
    {
      "type": "Feature",
      "id": "05df3ea9-3fb0-4d46-94e4-e6e2bb0fc59a",
      "properties": {
        "parcel_code": "GV-W101-P101",
        "land_use": "COMMERCIAL",
        "area_sq_m": 4200.0
      },
      "geometry": { "type": "Polygon", "coordinates": [...] }
    }
  ]
}
```

### 8.2 `GET /api/v1/3d/buildings/{id}`
- **Purpose**: Retrieve authoritative 3D representation, vertical datum, parent parcel, and property records for a building.
- **Auth**: Bearer Token (All authenticated roles)
- **Response `200 OK`**:
```json
{
  "building": { "id": "...", "building_reference": "BLD-W101-001", "area_sq_m": 1250.0 },
  "representation_3d": {
    "id": "...",
    "height": 45.0,
    "height_source": "SURVEY",
    "base_elevation": 0.0,
    "vertical_reference": "METERS_ABOVE_GROUND"
  },
  "parcel": { "id": "...", "parcel_code": "GV-W101-P101", "land_use": "COMMERCIAL" },
  "properties": [{ "property_reference": "PROP-W101-001", "address": "101 High Street" }],
  "cesium_extrusion": { ... }
}
```

### 8.3 `PATCH /api/v1/3d/buildings/{id}/height`
- **Purpose**: Update building vertical height and base elevation with geometric validation and audit trail.
- **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `SURVEYOR`)
- **Request Body**:
```json
{
  "height": 52.0,
  "base_elevation": 1.5,
  "height_source": "SURVEY",
  "height_confidence": 0.98,
  "vertical_reference": "METERS_ABOVE_GROUND"
}
```
- **Response `200 OK`**: Updated `Building3DRepresentationResponse`.

### 8.4 `GET /api/v1/3d/parcels/{id}`
- **Purpose**: Retrieve 3D context for a parcel including ground boundary, all contained extruded buildings, and camera preset.
- **Auth**: Bearer Token (All authenticated roles)

### 8.5 `GET /api/v1/3d/identify`
- **Purpose**: 3D point identify query.
- **Auth**: Bearer Token (All authenticated roles)
- **Query Params**: `lon`, `lat`, `height`, `radius`
- **Response `200 OK`**:
```json
{
  "building": { "id": "...", "building_reference": "BLD-W101-001", "height": 45.0 },
  "parcel": { "id": "...", "parcel_code": "GV-W101-P101" },
  "property": { "id": "...", "property_reference": "PROP-W101-001" },
  "jurisdiction": { "id": "...", "name": "Ward 101" }
}
```

### 8.6 `GET /api/v1/3d/assets` and `POST /api/v1/3d/assets`
- **Purpose**: Asset management for glTF, GLB, and JSON extrusion models.
- **Auth**: `POST` / `DELETE` require `ADMIN`, `GOVERNMENT_OFFICER`, or `SURVEYOR`.

---

## 9. Building, Floor & Unit Hierarchy (Phase 4)

### 9.1 `GET /api/v1/floors`
- **Purpose**: List floor slabs with filtering by building, floor number, or floor type.
- **Auth**: Bearer Token (All authenticated roles)
- **Query Params**: `building_id`, `floor_type`, `skip`, `limit`
- **Response `200 OK`**:
```json
{
  "items": [
    {
      "id": "7c9b0e12-4d3a-4a11-89b1-0987654321ab",
      "building_id": "3a1e2f34-5b6c-7d8e-9f0a-1b2c3d4e5f6a",
      "floor_number": 1,
      "floor_name": "Level 1 - Retail",
      "elevation_min_m": 0.0,
      "elevation_max_m": 4.5,
      "height_m": 4.5,
      "area_sqm": 850.0,
      "floor_type": "STANDARD",
      "unit_count": 4,
      "geometry": { "type": "Polygon", "coordinates": [...] }
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

### 9.2 `POST /api/v1/floors`
- **Purpose**: Create a floor slab with strict vertical clash validation and footprint containment checks.
- **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `SURVEYOR`)
- **Request Body**:
```json
{
  "building_id": "3a1e2f34-5b6c-7d8e-9f0a-1b2c3d4e5f6a",
  "floor_number": 2,
  "floor_name": "Level 2 - Offices",
  "elevation_min_m": 4.5,
  "elevation_max_m": 8.5,
  "floor_type": "STANDARD",
  "geometry": { "type": "Polygon", "coordinates": [...] }
}
```
- **Response `201 Created`**: Created `FloorDetailResponse`.

### 9.3 `GET /api/v1/floors/{id}`
- **Purpose**: Retrieve floor slab details including vertical elevation bounds and contained units.
- **Auth**: Bearer Token (All authenticated roles)

### 9.4 `PUT /api/v1/floors/{id}` & `DELETE /api/v1/floors/{id}`
- **Purpose**: Update floor properties/geometry or delete floor slab (cascades to units).
- **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `SURVEYOR`)

### 9.5 `GET /api/v1/buildings/{building_id}/floors`
- **Purpose**: Retrieve all stacked floors for a building ordered by `floor_number` ascending.
- **Auth**: Bearer Token (All authenticated roles)

### 9.6 `GET /api/v1/units`
- **Purpose**: List property units with filtering by floor, building, unit type, and ownership type.
- **Auth**: Bearer Token (All authenticated roles)
- **Query Params**: `floor_id`, `building_id`, `unit_type`, `ownership_type`, `skip`, `limit`
- **Response `200 OK`**:
```json
{
  "items": [
    {
      "id": "8d0c1f23-5e4b-4b22-90c2-1098765432bc",
      "floor_id": "7c9b0e12-4d3a-4a11-89b1-0987654321ab",
      "building_id": "3a1e2f34-5b6c-7d8e-9f0a-1b2c3d4e5f6a",
      "unit_number": "101",
      "unit_name": "Retail Suite 101",
      "unit_type": "COMMERCIAL",
      "ownership_type": "CONDOMINIUM",
      "elevation_min_m": 0.0,
      "elevation_max_m": 4.5,
      "height_m": 4.5,
      "gross_area_sqm": 220.0,
      "net_area_sqm": 195.0,
      "property_id": "f5e4d3c2-b1a0-4f9e-8d7c-6b5a4e3d2c1b",
      "geometry": { "type": "Polygon", "coordinates": [...] }
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

### 9.7 `POST /api/v1/units`
- **Purpose**: Create a property unit volumetric prism with floor containment and interior disjointness validation.
- **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `SURVEYOR`)
- **Request Body**:
```json
{
  "floor_id": "7c9b0e12-4d3a-4a11-89b1-0987654321ab",
  "unit_number": "102",
  "unit_name": "Retail Suite 102",
  "unit_type": "COMMERCIAL",
  "ownership_type": "CONDOMINIUM",
  "elevation_min_m": 0.0,
  "elevation_max_m": 4.5,
  "property_id": null,
  "geometry": { "type": "Polygon", "coordinates": [...] }
}
```
- **Response `201 Created`**: Created `UnitDetailResponse`.

### 9.8 `GET /api/v1/units/{id}`
- **Purpose**: Retrieve property unit detail including 3D prism bounds and legal property cross-reference.
- **Auth**: Bearer Token (All authenticated roles)

### 9.9 `PUT /api/v1/units/{id}` & `DELETE /api/v1/units/{id}`
- **Purpose**: Update unit metadata/geometry or delete property unit record.
- **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `SURVEYOR`)

### 9.10 `GET /api/v1/buildings/{building_id}/hierarchy`
- **Purpose**: Retrieve full hierarchical tree for a building: `Building` $\rightarrow$ stacked `Floors` $\rightarrow$ contained `PropertyUnits`.
- **Auth**: Bearer Token (All authenticated roles)
- **Response `200 OK`**:
```json
{
  "building": { "id": "...", "building_reference": "BLD-W101-001", "height": 36.0 },
  "total_floors": 8,
  "total_units": 32,
  "floors": [
    {
      "id": "...",
      "floor_number": 1,
      "floor_name": "Ground Floor",
      "elevation_min_m": 0.0,
      "elevation_max_m": 4.5,
      "units": [
        {
          "id": "...",
          "unit_number": "G-01",
          "unit_type": "COMMERCIAL",
          "gross_area_sqm": 220.0
        }
      ]
    }
  ]
}
```

---

## 10. Surveyor Field Workflow & Data Collection (Phase 5)

### 10.1 Survey Projects
Survey projects organize field campaigns within an administrative jurisdiction.

#### `POST /api/v1/survey-projects`
- **Purpose**: Create a new survey project.
- **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`)
- **Request Body**:
```json
{
  "project_code": "PRJ-2026-CBD-AUDIT",
  "name": "Central Business District Cadastral Audit 2026",
  "description": "Systematic audit of commercial multi-storey building footprints.",
  "jurisdiction_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "organization_id": "7fa85f64-5717-4562-b3fc-2c963f66afa7",
  "priority": "HIGH",
  "start_date": "2026-09-01T00:00:00Z",
  "target_completion_date": "2026-10-31T23:59:59Z"
}
```
- **Response `201 Created`**: `SurveyProjectResponse` object.

#### `GET /api/v1/survey-projects`
- **Purpose**: List survey projects with optional filters (`jurisdiction_id`, `organization_id`, `status`).
- **Auth**: Bearer Token (All authenticated roles)
- **Response `200 OK`**: `PaginatedResponse[SurveyProjectDetailResponse]`.

#### `GET /api/v1/survey-projects/{id}`
- **Purpose**: Retrieve full project details, assignment counts, and assignment rosters.
- **Auth**: Bearer Token (All authenticated roles)

---

### 10.2 Survey Assignments
Field tasks assigned to accredited surveyors for specific parcels or buildings.

#### `POST /api/v1/survey-assignments`
- **Purpose**: Provision and assign a cadastral field survey task.
- **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`)
- **Request Body**:
```json
{
  "assignment_code": "ASG-2026-001",
  "project_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "surveyor_id": "4fa85f64-5717-4562-b3fc-2c963f66afa8",
  "parcel_id": "5fa85f64-5717-4562-b3fc-2c963f66afa9",
  "building_id": "6fa85f64-5717-4562-b3fc-2c963f66afb0",
  "survey_type": "CADASTRAL_BOUNDARY",
  "priority": "HIGH",
  "due_date": "2026-10-15T18:00:00Z",
  "instructions": "Verify ground footprint perimeter and measure vertical height at corners."
}
```
- **Response `201 Created`**: `SurveyAssignmentResponse` (`status: "ASSIGNED"`).

#### `GET /api/v1/survey-assignments`
- **Purpose**: Filter assignments by `surveyor_id`, `status`, `project_id`, `parcel_id`, or `building_id`.
- **Auth**: Bearer Token (Surveyors filtered to own assignments; Officers/Admins access all).
- **Response `200 OK`**: `PaginatedResponse[SurveyAssignmentDetailResponse]`.

#### `GET /api/v1/survey-assignments/{id}`
- **Purpose**: Retrieve detailed assignment record, latest active session, observations, and attached evidence.
- **Auth**: Bearer Token (Assigned Surveyor, Officer, Admin).

---

### 10.3 Field Survey Sessions
Stateful tracking of active on-site work sessions by surveyors.

#### `POST /api/v1/survey-assignments/{assignment_id}/sessions/start`
- **Purpose**: Start or resume a survey session. Transitions assignment from `ASSIGNED` or `REVISION_REQUIRED` to `IN_PROGRESS`.
- **Auth**: Bearer Token (`SURVEYOR`, `ADMIN`)
- **Request Body**:
```json
{
  "device_info": "Samsung Galaxy Tab Active4 Pro / Chrome 128 (Android 14)",
  "app_version": "1.0.0",
  "battery_level_start": 98.5
}
```
- **Response `200 OK`**: `SurveySessionResponse` (`status: "ACTIVE"`).

#### `POST /api/v1/survey-sessions/{id}/end`
- **Purpose**: Close out an active field survey session.
- **Auth**: Bearer Token (`SURVEYOR`, `ADMIN`)
- **Request Body**:
```json
{
  "battery_level_end": 74.0,
  "sync_pending_count": 0,
  "notes": "Completed south-east boundary corner measurements."
}
```
- **Response `200 OK`**: `SurveySessionResponse` (`status: "COMPLETED"`).

---

### 10.4 Observations & Measurements
Spatial measurements and physical characteristics captured in the field.

#### `POST /api/v1/survey-sessions/{id}/observations`
- **Purpose**: Record a field observation with high-accuracy GNSS coordinates.
- **Auth**: Bearer Token (`SURVEYOR`, `ADMIN`)
- **Request Body**:
```json
{
  "observation_type": "HEIGHT_MEASUREMENT",
  "target_type": "BUILDING",
  "target_id": "6fa85f64-5717-4562-b3fc-2c963f66afb0",
  "measured_height_m": 45.2,
  "measured_floors": 12,
  "latitude": 17.448512,
  "longitude": 78.375841,
  "altitude_m": 542.1,
  "horizontal_accuracy_m": 0.85,
  "vertical_accuracy_m": 1.20,
  "gps_quality": "RTK_FIXED",
  "structural_condition": "GOOD",
  "boundary_discrepancy_flag": false,
  "field_notes": "Laser rangefinder measurement to roof parapet."
}
```
- **Response `201 Created`**: `SurveyObservationResponse`.

#### `GET /api/v1/survey-sessions/{id}/observations`
- **Purpose**: List all observations recorded during a survey session.
- **Auth**: Bearer Token (Assigned Surveyor, Officer, Admin).
- **Response `200 OK`**: `List[SurveyObservationResponse]`.

---

### 10.5 Evidence Ingestion & Cryptographic Integrity
Field photo uploads with client-calculated SHA-256 hashes verified on the server before storage in `uploads/evidence/`.

#### `POST /api/v1/survey-sessions/{id}/evidence`
- **Purpose**: Upload field photo or evidence document.
- **Auth**: Bearer Token (`SURVEYOR`, `ADMIN`)
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `file`: Binary file upload (JPEG, PNG, WebP, PDF; max 25MB)
  - `evidence_type`: `BUILDING_FRONT`, `BOUNDARY_MARKER`, `FACADE_DETAIL`, `ROOF_STRUCTURE`, `DISCREPANCY_PROOF`, `FIELD_SKETCH`
  - `target_type`: `BUILDING`, `PARCEL`, `FLOOR`, `UNIT`
  - `target_id`: UUID string of target entity
  - `description`: Optional text caption
  - `latitude`: Optional decimal degree float
  - `longitude`: Optional decimal degree float
  - `accuracy`: Optional accuracy in meters
  - `client_sha256`: Optional client-computed hex SHA-256 (server verifies matches file bytes)
  - `observation_id`: Optional UUID linking evidence to an observation
- **Response `201 Created`**: `SurveyEvidenceResponse`.

#### `GET /api/v1/survey-sessions/{id}/evidence`
- **Purpose**: List all evidence records for a survey session.
- **Auth**: Bearer Token (Assigned Surveyor, Officer, Admin).
- **Response `200 OK`**: `List[SurveyEvidenceResponse]`.

#### `GET /api/v1/survey-evidence/{id}/file`
- **Purpose**: Securely stream evidence image file or document with proper MIME type headers.
- **Auth**: Bearer Token (Assigned Surveyor, Officer, Admin).
- **Response `200 OK`**: Binary stream (`FileResponse`).

---

### 10.6 Cadastral Validation & Pre-Submission Engine

#### `POST /api/v1/survey-sessions/{id}/validate`
- **Purpose**: Run deterministic cadastral discrepancy comparisons (measured vs official height, floors, area) and GPS quality tier classifications.
- **Auth**: Bearer Token (`SURVEYOR`, `ADMIN`)
- **Response `200 OK`**:
```json
{
  "is_valid": true,
  "can_submit": true,
  "warnings": [
    "Observation at 17.4485, 78.3758 has horizontal accuracy of 4.2m (Acceptable tier; RTK recommended)."
  ],
  "errors": [],
  "discrepancies": [
    {
      "field": "height_m",
      "official_value": 42.0,
      "measured_value": 45.2,
      "difference_percent": 7.62,
      "severity": "WARNING",
      "description": "Measured height exceeds recorded height by 3.2m (+7.6%)"
    }
  ],
  "observation_count": 4,
  "evidence_count": 3
}
```

---

### 10.7 Submission & Officer Review Adjudication

#### `POST /api/v1/survey-sessions/{id}/submit`
- **Purpose**: Freeze immutable JSON snapshot of observations, evidence, and validation summary, increment submission version ($V_1, V_2, \dots$), and transition assignment to `SUBMITTED`.
- **Auth**: Bearer Token (`SURVEYOR`, `ADMIN`)
- **Response `201 Created`**: `SurveySubmissionResponse` (`status: "PENDING_REVIEW"`).

#### `GET /api/v1/survey-submissions`
- **Purpose**: Officer review queue listing submissions with optional `assignment_id` or `status` filters.
- **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`)
- **Response `200 OK`**: `PaginatedResponse[SurveySubmissionResponse]`.

#### `GET /api/v1/survey-submissions/{id}`
- **Purpose**: Retrieve submission details with frozen snapshot, official comparisons, and evidence gallery.
- **Auth**: Bearer Token (Assigned Surveyor, Officer, Admin).

#### `POST /api/v1/survey-submissions/{id}/approve`
- **Purpose**: Government Officer approves submission. Assignment transitions to `APPROVED`. Official cadastre remains unaffected (evidence snapshot only).
- **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`)
- **Request Body**: `{"review_notes": "All boundary and height measurements verified against ground survey."}`
- **Response `200 OK`**: `SurveySubmissionResponse` (`status: "APPROVED"`).

#### `POST /api/v1/survey-submissions/{id}/request-revision`
- **Purpose**: Request surveyor revision. Assignment transitions to `REVISION_REQUIRED`.
- **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`)
- **Request Body**: `{"review_notes": "Please re-measure roof parapet with RTK fix; accuracy was too coarse."}` (Mandatory)
- **Response `200 OK`**: `SurveySubmissionResponse` (`status: "REVISION_REQUIRED"`).

#### `POST /api/v1/survey-submissions/{id}/reject`
- **Purpose**: Reject submission. Assignment transitions to `REJECTED`.
- **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`)
- **Request Body**: `{"review_notes": "Survey was conducted on incorrect parcel boundary."}` (Mandatory)
- **Response `200 OK`**: `SurveySubmissionResponse` (`status: "REJECTED"`).

---

### 10.8 Offline Batch Synchronization Queue

#### `POST /api/v1/sync/batch`
- **Purpose**: Synchronize queued mutations performed by offline mobile clients. Operations processed idempotently with duplicate detection and client-provided UUID resolution.
- **Auth**: Bearer Token (`SURVEYOR`, `ADMIN`)
- **Request Body**:
```json
{
  "batch_id": "7fa85f64-5717-4562-b3fc-2c963f66afc1",
  "client_timestamp": "2026-09-23T14:30:00Z",
  "operations": [
    {
      "operation_id": "8fa85f64-5717-4562-b3fc-2c963f66afc2",
      "operation_type": "CREATE_OBSERVATION",
      "entity_type": "OBSERVATION",
      "entity_id": "9fa85f64-5717-4562-b3fc-2c963f66afc3",
      "session_id": "afa85f64-5717-4562-b3fc-2c963f66afc4",
      "client_timestamp": "2026-09-23T14:28:10Z",
      "payload": {
        "observation_type": "FOOTPRINT_CORNER",
        "target_type": "BUILDING",
        "target_id": "6fa85f64-5717-4562-b3fc-2c963f66afb0",
        "latitude": 17.448550,
        "longitude": 78.375810,
        "gps_quality": "RTK_FIXED",
        "horizontal_accuracy_m": 0.45
      }
    }
  ]
}
```
- **Response `200 OK`**:
```json
{
  "batch_id": "7fa85f64-5717-4562-b3fc-2c963f66afc1",
  "processed_at": "2026-09-23T14:30:02Z",
  "total_operations": 1,
  "success_count": 1,
  "failure_count": 0,
  "conflict_count": 0,
  "results": [
    {
      "operation_id": "8fa85f64-5717-4562-b3fc-2c963f66afc2",
      "status": "APPLIED",
      "entity_id": "9fa85f64-5717-4562-b3fc-2c963f66afc3",
      "error_message": null
    }
  ]
}
```

#### `GET /api/v1/sync/status`
- **Purpose**: Get offline sync capability metadata, supported operations, and batch size limits.
- **Auth**: Bearer Token (All authenticated roles)
- **Response `200 OK`**:
```json
{
  "status": "ready",
  "supported_operations": ["CREATE_OBSERVATION", "UPDATE_OBSERVATION", "UPDATE_SESSION"],
  "idempotency_enabled": true,
  "max_batch_size": 100
}
```

---

## 11. Phase 6 AI Building & Floor Extraction Pipeline Endpoints (`/api/v1/ai`)

### 11.1 Processing Jobs
- `POST /api/v1/ai/jobs`: Dispatch async extraction job (`require_editor` or `SURVEYOR`).
- `GET /api/v1/ai/jobs`: List AI jobs with filtering by `job_type`, `status`, `target_id`.
- `GET /api/v1/ai/jobs/{id}`: Detailed job record with stages, duration, and metrics.

### 11.2 Extraction Candidates & Validation
- `GET /api/v1/ai/building-results`: List building extraction candidates with confidence and review status filters.
- `GET /api/v1/ai/building-results/{id}`: Building candidate details with geometry and comparison metrics.
- `GET /api/v1/ai/floor-results`: List floor extraction candidates.
- `POST /api/v1/ai/results/{id}/validate`: Deterministic geometric and topological validation of a candidate.

### 11.3 Human Review & Controlled Cadastral Updates
- `POST /api/v1/ai/results/{id}/approve`: Explicit human approval of candidate (`require_officer_or_admin`). Updates authoritative `BuildingFootprint` and `Building3DRepresentation`.
- `POST /api/v1/ai/results/{id}/reject`: Explicit human rejection with required rationale (`require_officer_or_admin`).
- `POST /api/v1/ai/results/{id}/modify`: Modify candidate geometry prior to approval (`require_officer_or_admin`).

### 11.4 Models, Datasets & Benchmarks
- `GET /api/v1/ai/models`: List registered AI models and versions with device and configuration status.
- `GET /api/v1/ai/datasets`: List evaluation datasets.
- `POST /api/v1/ai/evaluations/run`: Trigger benchmark evaluation run (`require_admin`).

---

## 12. Phase 7 Advanced Topology Validation & Spatial Consistency Endpoints (`/api/v1/validation`)

### 12.1 Validation Runs
- `POST /api/v1/validation/runs`: Trigger async validation run across specified target (`PARCEL`, `BUILDING`, `FLOOR`, `UNIT`, `AI_RESULT`, `SURVEY_SUBMISSION`, `JURISDICTION`, or full system `SYSTEM`). Supports custom tolerance overrides.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `SURVEYOR`, `URBAN_PLANNER`).
  - **Body**: `{ "validation_type": "string", "target_type": "string", "target_id": "uuid", "tolerances": {} }`
  - **Response `201 Created`**: ValidationRun object in `QUEUED` stage.
- `GET /api/v1/validation/runs`: List validation runs with pagination and filtering by `status`, `target_type`, `validation_type`.
  - **Auth**: Bearer Token (All authenticated roles).
- `GET /api/v1/validation/runs/{id}`: Detailed validation run with execution duration, stage progression, and severity summary metrics.
  - **Auth**: Bearer Token (All authenticated roles).
- `GET /api/v1/validation/runs/{id}/issues`: List issues specifically flagged by a validation run.
  - **Auth**: Bearer Token (All authenticated roles).

### 12.2 Validation Issues & Human Review Lifecycle
- `GET /api/v1/validation/issues`: Search and filter validation issues across entities.
  - **Query Params**: `status`, `severity`, `category`, `rule_id`, `entity_type`, `entity_id`.
  - **Auth**: Bearer Token (All authenticated roles).
- `GET /api/v1/validation/issues/{id}`: Detailed issue inspection with technical explanation, measured value, expected value, tolerance threshold, and geometry WKT / GeoJSON.
  - **Auth**: Bearer Token (All authenticated roles).
- `POST /api/v1/validation/issues/{id}/acknowledge`: Mark an open issue as acknowledged under human review.
  - **Auth**: Bearer Token (`SURVEYOR`, `GOVERNMENT_OFFICER`, `ADMIN`).
- `POST /api/v1/validation/issues/{id}/resolve`: Mark an issue as formally resolved with mandatory resolution notes.
  - **Auth**: Bearer Token (`GOVERNMENT_OFFICER`, `ADMIN`).
  - **Body**: `{ "resolution_note": "string" }`
- `POST /api/v1/validation/issues/{id}/waive`: Grant a formal technical waiver for an issue with mandatory legal/technical justification.
  - **Auth**: Bearer Token (`GOVERNMENT_OFFICER`, `ADMIN`).
  - **Body**: `{ "waiver_reason": "string" }`

### 12.3 Entity Summaries & Rule Catalogue
- `GET /api/v1/validation/entities/{target_type}/{target_id}/summary`: Quick topology and quality summary for any spatial entity. Returns issue count by severity, resolution status, and whether entity is clean.
  - **Auth**: Bearer Token (All authenticated roles).
- `GET /api/v1/validation/rules`: Full catalogue of active deterministic rules with rule ID, version, category, default severity, target types, and technical description.
  - **Auth**: Bearer Token (All authenticated roles).

---

## 13. Phase 8 AI Document Intelligence & Property Verification Endpoints (`/api/v1/documents`)

### 13.1 Document Ingestion & Retrieval
- `POST /api/v1/documents/upload`: Upload property document (PDF, TIFF, PNG, JPEG; max 50MB) with multipart form data and metadata.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `SURVEYOR`, `URBAN_PLANNER`).
  - **Multipart Fields**: `file` (binary), `title` (string), `jurisdiction_id` (uuid), `document_type` (string, optional), `document_number` (string, optional), `parcel_id` (uuid, optional), `property_id` (uuid, optional), `building_id` (uuid, optional), `unit_id` (uuid, optional).
  - **Response `201 Created`**: `PropertyDocument` with version and cryptographic SHA-256 hash.
- `GET /api/v1/documents`: List property documents with pagination and filtering by `status`, `document_type`, `jurisdiction_id`, `parcel_id`, `requires_review`.
  - **Auth**: Bearer Token (All authenticated roles).
- `GET /api/v1/documents/{id}`: Detailed document object including pages, OCR results, extracted fields with provenance, and entity links.
  - **Auth**: Bearer Token (All authenticated roles).
- `GET /api/v1/documents/metrics`: Aggregate subsystem metrics: total documents, verified, under review, requires correction, rejected, OCR success rate, and average extraction confidence.
  - **Auth**: Bearer Token (All authenticated roles).
- `GET /api/v1/documents/{id}/pages/{page_number}/image`: Stream rendered page image for high-fidelity frontend preview and bounding-box overlay.
  - **Auth**: Bearer Token (All authenticated roles).
- `GET /api/v1/documents/{id}/download`: Download raw source document binary.
  - **Auth**: Bearer Token (All authenticated roles).

### 13.2 AI Extraction Pipeline Execution
- `POST /api/v1/documents/{id}/process`: Trigger complete AI document intelligence worker pipeline (page extraction, OCR, classification, structured field extraction, deterministic normalization, candidate matching, and Phase 7 validation integration).
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `SURVEYOR`, `URBAN_PLANNER`).
  - **Response `202 Accepted`**: `DocumentProcessingJob` record.

### 13.3 Structured Field Human Review
- `PATCH /api/v1/documents/{id}/fields/{field_id}/review`: Human-in-the-loop review of extracted field.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `SURVEYOR`).
  - **Body**: `{ "review_status": "ACCEPTED" | "CORRECTED" | "REJECTED", "reviewed_value": "string", "review_comment": "string" }`
  - **Response `200 OK`**: Updated `DocumentExtractedField`.

### 13.4 Cadastral Entity Links
- `POST /api/v1/documents/{id}/links`: Associate document with cadastral entity (`PARCEL`, `PROPERTY`, `BUILDING`, `UNIT`).
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `SURVEYOR`).
  - **Body**: `{ "entity_type": "PARCEL", "entity_id": "uuid", "relationship_type": "PRIMARY_TITLE", "match_confidence": 1.0, "match_method": "MANUAL_LINK" }`
  - **Response `201 Created`**: Updated `PropertyDocument`.
- `PATCH /api/v1/documents/{id}/links/{link_id}/confirm`: Confirm candidate cadastral link.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `SURVEYOR`).
  - **Response `200 OK`**: Updated `PropertyDocument`.
- `PATCH /api/v1/documents/{id}/links/{link_id}/reject`: Reject candidate cadastral link.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `SURVEYOR`).
  - **Response `200 OK`**: Updated `PropertyDocument`.

### 13.5 Human Cadastral Verification & Legal Adjudication
- `POST /api/v1/documents/{id}/verify`: Cadastral officer final determination action.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "action": "VERIFY" | "REJECT" | "REQUEST_CORRECTION", "review_notes": "string", "rejection_reason": "string" }`
  - **Response `200 OK`**: Updated `PropertyDocument` with terminal/review status and audit logging.

---

## 14. Phase 9 AI Change Detection & Temporal Property Intelligence Endpoints (`/api/v1/change-detection`)

### 14.1 Temporal Snapshots
- `POST /api/v1/change-detection/snapshots`: Create an immutable temporal snapshot for a parcel, building, floor, or property unit.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `SURVEYOR`).
  - **Body**: `{ "entity_type": "PARCEL" | "BUILDING" | "FLOOR" | "UNIT", "entity_id": "uuid", "snapshot_type": "OFFICIAL_RECORD" | "SURVEY" | "REMOTE_SENSING" | "AI_DERIVED" | "DOCUMENT_DERIVED" | "MANUAL", "effective_from": "datetime", "effective_to": "datetime", "observation_date": "datetime", "date_precision": "EXACT" | "DAY" | "MONTH" | "YEAR", "source_type": "string", "source_id": "string", "geometry_wkt": "string", "attributes_json": {} }`
  - **Response `201 Created`**: `PropertySnapshot` object.
- `GET /api/v1/change-detection/snapshots`: Query snapshots with filtering by `entity_type`, `entity_id`, `is_current`, and pagination.
  - **Auth**: Bearer Token (All authenticated roles).
- `GET /api/v1/change-detection/snapshots/{id}`: Retrieve a specific property snapshot by UUID.
  - **Auth**: Bearer Token (All authenticated roles).

### 14.2 Change Detection Runs
- `POST /api/v1/change-detection/runs`: Dispatch an asynchronous change detection run comparing baseline and comparison states.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `SURVEYOR`, `URBAN_PLANNER`).
  - **Body**: `{ "target_type": "BUILDING" | "PARCEL" | "FLOOR" | "UNIT" | "SYSTEM", "target_id": "string", "baseline_reference": "string", "comparison_reference": "string", "detection_method": "GEOMETRY_DIFF" | "ATTRIBUTE_DIFF" | "IMAGE_AI" | "SURVEY_COMPARISON" | "DOCUMENT_COMPARISON" | "COMPOSITE", "parameters": { "area_threshold_sqm": 1.0, "height_threshold_m": 0.5, "displacement_threshold_m": 0.3 } }`
  - **Response `202 Accepted`**: `ChangeDetectionRunResponse` with execution metadata.
- `GET /api/v1/change-detection/runs`: List change detection runs with status and parameter filters.
  - **Auth**: Bearer Token (All authenticated roles).
- `GET /api/v1/change-detection/runs/{id}`: Get status and summary metrics of a detection run.
  - **Auth**: Bearer Token (All authenticated roles).
- `POST /api/v1/change-detection/runs/{id}/cancel`: Cancel an active or queued run.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
- `GET /api/v1/change-detection/runs/{id}/changes`: Retrieve change candidates generated by a run.
  - **Auth**: Bearer Token (All authenticated roles).

### 14.3 Change Candidates & Human-in-the-Loop Reviews
- `GET /api/v1/change-detection/changes`: Search and list change candidates across runs with filters for `status`, `significance`, `change_type`, `entity_type`, `entity_id`.
  - **Auth**: Bearer Token (All authenticated roles).
- `GET /api/v1/change-detection/changes/{id}`: Detailed candidate inspection including geometry diff, magnitude metrics, topological validation issues, and multi-source evidence references.
  - **Auth**: Bearer Token (All authenticated roles).
- `POST /api/v1/change-detection/changes/{id}/confirm`: Confirm candidate physical change into official temporal snapshot history.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "action": "CONFIRM", "review_reason": "CONFIRMED_FIELD_SURVEY" | "CONFIRMED_PERMIT_APPROVED" | "OTHER", "review_notes": "string" }`
  - **Response `200 OK`**: Updated candidate with status `CONFIRMED`.
- `POST /api/v1/change-detection/changes/{id}/reject`: Reject candidate change (e.g. false positive, sensor noise, temporary structure).
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "action": "REJECT", "review_reason": "FALSE_POSITIVE" | "TEMPORARY_STRUCTURE" | "DATA_ALIGNMENT_ERROR" | "OTHER", "review_notes": "string" }`
  - **Response `200 OK`**: Updated candidate with status `REJECTED`.
- `POST /api/v1/change-detection/changes/{id}/dismiss`: Dismiss candidate as de minimis or administrative non-issue.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "action": "DISMISS", "review_reason": "OTHER", "review_notes": "string" }`
  - **Response `200 OK`**: Updated candidate with status `DISMISSED`.

### 14.4 Temporal Entity Timeline & Subsystem Metrics
- `GET /api/v1/change-detection/entities/{entity_type}/{entity_id}/timeline`: Chronologically reconstruct the full lifecycle of an entity across cadastral snapshots, field surveys, property deeds, and detected changes.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: Array of `TimelineEntry` objects ordered by date.
- `GET /api/v1/change-detection/metrics`: Retrieve KPI dashboard statistics including run counts, candidates by status, significance breakdown, and entity types.
  - **Auth**: Bearer Token (All authenticated roles).

---

## 15. Phase 10 Underground Infrastructure & Subsurface Utility Intelligence Endpoints (`/api/v1/utilities`)

### 15.1 Utility Networks
- `POST /api/v1/utilities/networks`: Register a new underground utility network (water, sewer, gas, electricity, etc.).
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "name": "string", "utility_type": "WATER" | "SEWER" | "STORMWATER" | "GAS" | "ELECTRICITY" | "TELECOM" | "FIBER" | "DRAINAGE" | "OTHER", "jurisdiction_id": "uuid", "owner_organization": "string", "operator_organization": "string", "status": "ACTIVE", "source": "OFFICIAL_RECORD", "metadata_json": {} }`
  - **Response `201 Created`**: `UtilityNetworkResponse`.
- `GET /api/v1/utilities/networks`: Query networks with filters for `jurisdiction_id`, `utility_type`, and `status`.
  - **Auth**: Bearer Token (All authenticated roles).
- `GET /api/v1/utilities/networks/{id}`: Retrieve a specific utility network by ID.
  - **Auth**: Bearer Token (All authenticated roles).
- `GET /api/v1/utilities/networks/{id}/topology`: Analyze network topology graph (connected components, dangling segment endpoints, junction connectivity).
  - **Auth**: Bearer Token (All authenticated roles).

### 15.2 Utility Assets & Official Governance
- `POST /api/v1/utilities/assets`: Create a subsurface utility asset (pipe, cable, duct, manhole, vault).
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `SURVEYOR`).
  - **Body**: `{ "network_id": "uuid", "asset_type": "PIPE" | "CABLE" | "DUCT" | "MANHOLE" | "VAULT", "asset_reference": "string", "geometry_type": "LINESTRING" | "POINT" | "POLYGON", "geometry_wkt": "string", "depth": float, "ground_elevation": float, "centerline_elevation": float, "material": "string", "diameter": float, "source_type": "OFFICIAL_RECORD" | "SURVEY" | "AI_CANDIDATE", "confidence": "HIGH" | "MEDIUM" | "LOW", "parcel_id": "uuid", "building_id": "uuid" }`
  - **Response `201 Created`**: `UtilityAssetResponse`.
- `GET /api/v1/utilities/assets`: Search and filter subsurface assets by `network_id`, `asset_type`, `status`, `review_status`, `parcel_id`, `building_id`, `min_depth`, `max_depth`.
  - **Auth**: Bearer Token (All authenticated roles).
- `GET /api/v1/utilities/assets/{id}`: Full asset detail including network, segments, nodes, 3D structures, parcel intersection metrics, and building proximity.
  - **Auth**: Bearer Token (All authenticated roles).
- `POST /api/v1/utilities/assets/{id}/verify`: Human-in-the-loop cadastral review of candidate utility assets.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "action": "VERIFY" | "REJECT" | "REVISION_REQUIRED", "review_notes": "string" }`
  - **Response `200 OK`**: Updated `UtilityAssetResponse` with audit log.
- `POST /api/v1/utilities/assets/{id}/controlled-update`: Audit-logged controlled modification of verified utility records.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "reason": "string (min 5 chars)", "source_reference": "string (min 3 chars)", "updates": {} }`
  - **Response `200 OK`**: Updated `UtilityAssetResponse` with immutable audit trail.

### 15.3 3D Clash Detection & Separation Rules
- `POST /api/v1/utilities/clashes/detect`: Execute 3D collision and clearance detection across subsurface utilities.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `SURVEYOR`, `URBAN_PLANNER`).
  - **Query Params**: `jurisdiction_id`, `network_id`.
  - **Response `200 OK`**: List of detected `UtilityClashResponse` objects.
- `GET /api/v1/utilities/clashes`: Query clashes with filters for `status`, `severity`, and `asset_id`.
  - **Auth**: Bearer Token (All authenticated roles).
- `POST /api/v1/utilities/clashes/{id}/review`: Review and adjudicate a detected 3D clash.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "action": "ACKNOWLEDGE" | "RESOLVE" | "WAIVE", "resolution_notes": "string" }`
  - **Response `200 OK`**: Updated `UtilityClashResponse`.

### 15.4 2D/3D Geospatial & Subsystem Metrics
- `GET /api/v1/utilities/map`: 2D GeoJSON FeatureCollection of subsurface linear features and junction nodes bounded by bounding box.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Query Params**: `min_lon`, `min_lat`, `max_lon`, `max_lat`, `utility_type`.
  - **Response `200 OK`**: `UtilityGeoJSONCollection`.
- `GET /api/v1/utilities/3d`: 3D volumetric scene features with extruded geometry, centerline elevations, and depth models.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Query Params**: `network_id`, `utility_type`.
  - **Response `200 OK`**: `Utility3DSceneResponse`.
- `GET /api/v1/utilities/metrics`: Executive KPI metrics for subsurface infrastructure (total networks, assets, candidates in review, clashes, unknown depth).
  - **Auth**: Bearer Token (All authenticated roles).

---

## 16. Citizen Portal, Government Workflow & Public-Service Integration (Phase 11)

### 16.1 Service Types & SLA Configuration
- `GET /api/v1/workflows/service-types`: List active service request categories with SLA configurations.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Query Params**: `citizen_visible_only` (bool).
  - **Response `200 OK`**: `List[ServiceTypeResponse]`.
- `GET /api/v1/workflows/service-types/{code}`: Get service type detail by unique code.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: `ServiceTypeResponse`.
- `POST /api/v1/workflows/service-types`: Define or update a cadastral service category.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "code": "string", "name": "string", "description": "string", "response_sla_hours": int, "completion_sla_hours": int, "required_documents": [], "citizen_visible": true }`.
  - **Response `201 Created`**: `ServiceTypeResponse`.

### 16.2 Citizen Property Ownership & Authorization
- `GET /api/v1/workflows/citizen/properties`: List verified authorized property records linked to the authenticated citizen.
  - **Auth**: Bearer Token (`CITIZEN`, `ADMIN`).
  - **Response `200 OK`**: `List[CitizenPropertyResponse]`.
- `POST /api/v1/workflows/citizen/properties`: Officer verification linking a citizen user identity to a cadastral property record.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "citizen_id": "uuid", "property_id": "uuid", "authorization_type": "OWNER" | "AUTHORIZED_REPRESENTATIVE" | "OCCUPANT" | "TENANT", "status": "VERIFIED" }`.
  - **Response `201 Created`**: `CitizenPropertyLinkResponse`.
- `GET /api/v1/workflows/citizen/dashboard`: Real-time database-derived metrics for citizen portal (total properties, active requests, pending actions, unread notifications).
  - **Auth**: Bearer Token (`CITIZEN`, `ADMIN`).
  - **Response `200 OK`**: `CitizenDashboardMetricsResponse`.

### 16.3 Service Request Lifecycle & State Machine
- `POST /api/v1/workflows/service-requests`: Submit a new citizen service request with object-level authorization verification.
  - **Auth**: Bearer Token (`CITIZEN`, `ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "request_type": "string", "title": "string", "description": "string", "jurisdiction_id": "uuid", "property_id": "uuid", "parcel_id": "uuid", "priority": "LOW" | "MEDIUM" | "HIGH" | "URGENT" }`.
  - **Response `201 Created`**: `ServiceRequestResponse`.
- `GET /api/v1/workflows/service-requests`: List and filter service requests with automatic citizen/officer scoping.
  - **Auth**: Bearer Token (Citizens scoped to own requests; Officers scoped to assigned jurisdiction).
  - **Query Params**: `status`, `request_type`, `priority`, `jurisdiction_id`, `search`, `skip`, `limit`.
  - **Response `200 OK`**: `{ "items": List[ServiceRequestResponse], "total": int, "skip": int, "limit": int }`.
- `GET /api/v1/workflows/service-requests/{id}`: Detailed request view including event audit trail, messages, subtasks, and SLA status.
  - **Auth**: Bearer Token (Requester, Assigned Officer, Admin).
  - **Response `200 OK`**: `ServiceRequestDetailResponse`.
- `GET /api/v1/workflows/service-requests/{id}/workspace`: Cross-phase integrated case workspace aggregating 2D/3D GIS geometry, documents, field surveys, topology issues, change candidates, and subsurface utility clashes.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `URBAN_PLANNER`).
  - **Response `200 OK`**: `CrossPhaseCaseWorkspaceResponse`.
- `POST /api/v1/workflows/service-requests/{id}/transition`: State machine transition adjudication.
  - **Auth**: Bearer Token (Permitted roles per transition matrix).
  - **Body**: `{ "new_status": "RequestStatus", "reason": "string (mandatory for rejection/revision)", "comment": "string" }`.
  - **Response `200 OK`**: `ServiceRequestDetailResponse`.
- `POST /api/v1/workflows/service-requests/{id}/assign`: Assign case to officer or departmental team.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "assigned_to": "uuid", "assigned_team": "string", "notes": "string" }`.
  - **Response `200 OK`**: `ServiceRequestDetailResponse`.
- `POST /api/v1/workflows/service-requests/{id}/commission-survey`: Commission Phase 5 field survey project with surveyor assignment.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "surveyor_id": "uuid", "instructions": "string", "due_days": int }`.
  - **Response `200 OK`**: `ServiceRequestDetailResponse`.
- `POST /api/v1/workflows/service-requests/{id}/escalate`: Escalate case for priority review.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "escalation_reason": "string", "assigned_to": "uuid", "escalated_priority": "URGENT" }`.
  - **Response `200 OK`**: `ServiceRequestDetailResponse`.
- `POST /api/v1/workflows/service-requests/{id}/execute-update`: Controlled officer execution of official registry update.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "updates": {}, "audit_reason": "string", "source_reference": "string" }`.
  - **Response `200 OK`**: Result dict with audit event confirmation.

### 16.4 Case Messaging & Confidential Officer Notes
- `GET /api/v1/workflows/service-requests/{id}/messages`: Retrieve case messages (internal notes strictly filtered out for citizen users).
  - **Auth**: Bearer Token.
  - **Response `200 OK`**: `List[CaseMessageResponse]`.
- `POST /api/v1/workflows/service-requests/{id}/messages`: Post a public message or confidential internal note.
  - **Auth**: Bearer Token.
  - **Body**: `{ "message_body": "string", "message_type": "PUBLIC_MESSAGE" | "INTERNAL_NOTE" }`.
  - **Response `201 Created`**: `CaseMessageResponse`.

### 16.5 Operations Dashboard, Queues & Notifications
- `GET /api/v1/workflows/government/dashboard`: Real-time database-derived operations KPIs (active cases, unassigned, overdue, due soon, surveys commissioned, compliance rate).
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`, `URBAN_PLANNER`).
  - **Response `200 OK`**: `GovernmentDashboardMetricsResponse`.
- `GET /api/v1/workflows/government/queues`: List officer review tasks with assignee and status filters.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Query Params**: `task_type`, `status`, `my_tasks_only`.
  - **Response `200 OK`**: `List[WorkflowTaskResponse]`.
- `GET /api/v1/workflows/notifications`: In-app notification center for authenticated user.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Query Params**: `unread_only`, `limit`.
  - **Response `200 OK`**: `List[NotificationResponse]`.
- `POST /api/v1/workflows/notifications/{id}/read`: Mark notification as read.
  - **Auth**: Bearer Token.
  - **Response `200 OK`**: `NotificationResponse`.
- `POST /api/v1/workflows/notifications/read-all`: Mark all notifications as read.
  - **Auth**: Bearer Token.
  - **Response `200 OK`**: `{ "marked_count": int, "message": "string" }`.

---

## 17. Phase 12 Technical 3D Property Identifier Engine (`/api/v1/identifiers`)

### 17.1 Registry & Generation
- `GET /api/v1/identifiers`: Query and filter 3D Technical Identifiers.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Query Params**: `entity_type`, `scheme_code`, `status`, `search`, `skip`, `limit`.
  - **Response `200 OK`**: `{ "items": List[TechnicalIdentifierResponse], "total": int, "skip": int, "limit": int }`.
- `GET /api/v1/identifiers/{id}`: Detailed identifier record including parsed hierarchy components, supersession references, and QR token.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: `TechnicalIdentifierDetailResponse`.
- `POST /api/v1/identifiers/preview`: Deterministic dry-run generation and component preview.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "entity_type": "PARCEL" | "BUILDING" | "FLOOR" | "UNIT", "entity_id": "uuid", "scheme_code": "string (optional)" }`.
  - **Response `200 OK`**: `IdentifierPreviewResponse`.
- `POST /api/v1/identifiers/generate`: Formally issue and persist a new Technical 3D Identifier.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "entity_type": "PARCEL" | "BUILDING" | "FLOOR" | "UNIT", "entity_id": "uuid", "scheme_code": "string (optional)" }`.
  - **Response `201 Created`**: `TechnicalIdentifierResponse`.
- `POST /api/v1/identifiers/bulk-preview`: Pre-computation and validation preview for batch building unit generation.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "building_id": "uuid", "scheme_code": "string (optional)" }`.
  - **Response `200 OK`**: `BulkPreviewResponse`.
- `POST /api/v1/identifiers/bulk-generate`: Batch identifier generation for all eligible building units.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "building_id": "uuid", "scheme_code": "string (optional)", "confirmed": true }`.
  - **Response `200 OK`**: `BulkGenerateResultResponse`.

### 17.2 Verification & Lifecycle Management
- `GET /api/v1/identifiers/verify/token/{token}`: Public verification endpoint validating identifier authenticity and active status via secure verification token.
  - **Auth**: None (Public).
  - **Response `200 OK`**: `PublicVerificationResponse`.
- `POST /api/v1/identifiers/{id}/verify`: Verify identifier integrity, checksum, and status.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: `IdentifierVerificationResponse`.
- `POST /api/v1/identifiers/{id}/supersede`: Supersede identifier due to subdivision, consolidation, or boundary change.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "reason": "string", "new_identifier_id": "uuid" }`.
  - **Response `200 OK`**: `TechnicalIdentifierResponse`.
- `POST /api/v1/identifiers/{id}/retire`: Retire identifier upon demolition or entity cessation.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Body**: `{ "reason": "string" }`.
  - **Response `200 OK`**: `TechnicalIdentifierResponse`.
- `POST /api/v1/identifiers/{id}/revoke`: Administrative revocation of invalid identifier.
  - **Auth**: Bearer Token (`ADMIN`).
  - **Body**: `{ "reason": "string" }`.
  - **Response `200 OK`**: `TechnicalIdentifierResponse`.
- `GET /api/v1/identifiers/{id}/history`: Retrieve complete version history and supersession chain for the target entity.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: `List[TechnicalIdentifierResponse]`.
- `GET /api/v1/identifiers/{id}/qr`: Dynamic SVG/PNG QR code image generation for physical posting or mobile scanning.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: Image stream (`image/svg+xml` or `image/png`).
- `GET /api/v1/identifiers/statistics`: Subsystem KPIs (total, active, superseded, retired, revoked, by entity type).
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: `IdentifierStatisticsResponse`.

### 17.3 Scheme Management
- `GET /api/v1/identifiers/schemes`: List registered identifier schemes.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: `List[IdentifierSchemeResponse]`.
- `POST /api/v1/identifiers/schemes`: Register new identifier formatting scheme.
  - **Auth**: Bearer Token (`ADMIN`).
  - **Body**: `IdentifierSchemeCreate`.
  - **Response `201 Created`**: `IdentifierSchemeResponse`.
- `PATCH /api/v1/identifiers/schemes/{code}`: Update scheme status or metadata.
  - **Auth**: Bearer Token (`ADMIN`).
  - **Response `200 OK`**: `IdentifierSchemeResponse`.

---

## 18. Phase 13 Audit, Versioning, Notifications & System Governance

### 18.1 Authoritative Audit Ledger (`/api/v1/audit`)
- `GET /api/v1/audit`: Advanced multi-criteria search and investigation query across append-only audit records.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Query Params**: `category`, `action`, `actor_id`, `actor_role`, `target_type`, `target_id`, `severity`, `result`, `source_type`, `request_id`, `correlation_id`, `start_date`, `end_date`, `search`, `skip`, `limit`.
  - **Response `200 OK`**: `AuditListResponse` with `{ "items": List[AuditEventResponse], "total": int, "skip": int, "limit": int }`.
- `GET /api/v1/audit/{id}`: Detailed single audit event inspection with before/after state snapshots and changed fields.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Response `200 OK`**: `AuditEventResponse`.
- `GET /api/v1/audit/statistics`: Aggregate statistical summary of audit events grouped by category, severity, result, and top actions.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Response `200 OK`**: `AuditStatisticsResponse`.
- `GET /api/v1/audit/export`: Stream full or filtered audit history as CSV or JSON for compliance and regulatory reporting.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Query Params**: `format` (`csv` | `json`), plus all standard audit filter query parameters.
  - **Response `200 OK`**: File stream (`text/csv` with `Content-Disposition: attachment; filename=audit_export_...csv` or `application/json`).

### 18.2 Entity Versioning & Controlled Restoration (`/api/v1/versions`)
- `GET /api/v1/versions/{entity_type}/{entity_id}`: Retrieve chronological snapshot timeline for a cadastral entity.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: `List[EntityVersionResponse]`.
- `GET /api/v1/versions/{entity_type}/{entity_id}/version/{version_number}`: Retrieve an exact historical snapshot with geometry WKT/GeoJSON, spatial metrics, and attributes.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: `EntityVersionResponse`.
- `GET /api/v1/versions/compare/{version_id_a}/{version_id_b}`: Compute deterministic attribute diffs and 2D/3D geometric variance (area delta, perimeter delta, centroid displacement, bounding-box expansion, IoU overlap).
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: `VersionComparisonResponse`.
- `POST /api/v1/versions/{entity_type}/{entity_id}/restore`: Controlled rollback to a historical snapshot.
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Rule**: Preserves immutability — appends a NEW version $v(N+1)$ with change type `RESTORATION`, updates the live domain entity row, emits a `RESTORATION` audit event, and records a `RESTORED_FROM` lineage relationship. Historical versions are NEVER modified or deleted.
  - **Body**: `{ "target_version_number": int, "restoration_reason": "string (min 10 chars)" }`.
  - **Response `200 OK`**: `RestorationResponse`.
- `GET /api/v1/versions/{entity_type}/{entity_id}/lineage`: Retrieve forward and backward entity lineage transformation graph.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: `List[EntityLineageResponse]`.

### 18.3 Notification Management & Preferences (`/api/v1/notifications`)
- `GET /api/v1/notifications`: List notifications for current user with filtering by `unread_only`, `category`, and pagination.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: `NotificationListResponse`.
- `GET /api/v1/notifications/unread-count`: Real-time unread notification count badge.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: `{ "unread_count": int }`.
- `POST /api/v1/notifications/{id}/read`: Mark notification as read.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: `NotificationResponse`.
- `POST /api/v1/notifications/read-all`: Mark all notifications as read for current user.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: `{ "marked_count": int, "message": "string" }`.
- `GET /api/v1/notifications/preferences`: Get user notification routing preferences across categories.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: `List[NotificationPreferenceResponse]`.
- `PUT /api/v1/notifications/preferences`: Update user notification delivery channel preferences.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Rule**: Mandatory safety categories (`SYSTEM_ALERT`, `SECURITY_INCIDENT`, `CRITICAL_CADASTRAL_CHANGE`) cannot have their delivery channels disabled.
  - **Body**: `List[NotificationPreferenceUpdate]`.
  - **Response `200 OK`**: `List[NotificationPreferenceResponse]`.
- `POST /api/v1/notifications/test`: Dispatch a test notification verifying delivery channels according to user preferences.
  - **Auth**: Bearer Token (All authenticated roles).
  - **Response `200 OK`**: `NotificationResponse`.

### 18.4 Governance & Platform Integrity Console (`/api/v1/governance`)
- `GET /api/v1/governance/dashboard`: System-wide governance metrics (audit event counts, 24h event volume, critical events, version snapshots count, restoration count, notification delivery health).
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Response `200 OK`**: `GovernanceDashboardResponse`.
- `POST /api/v1/governance/integrity`: Execute automated platform data integrity scan (orphaned versions check, version number sequence gaps, geometry hash consistency, audit checksums, and pending notification queue health).
  - **Auth**: Bearer Token (`ADMIN`, `GOVERNMENT_OFFICER`).
  - **Response `200 OK`**: `DataIntegrityReportResponse`.









