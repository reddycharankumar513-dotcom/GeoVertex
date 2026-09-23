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

