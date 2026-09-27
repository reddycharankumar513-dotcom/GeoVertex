# GEOVERTEX: DATA MODEL SPECIFICATION
## Relational Schema, Spatial PostGIS Types, Audit & Versioning

Version: 1.0  
Status: Authoritative Data Specification  
Associated Documents: [MASTER_PRD.md](MASTER_PRD.md), [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 1. Data Modeling Principles

1. **UUID Primary Keys**: All entities use RFC 4122 Version 4 UUIDs for collision-safe, distributed identity generation.
2. **PostGIS Spatial Foundation**: Authoritative spatial geometries are stored using PostGIS `geometry` types with explicit Coordinate Reference System (SRID) identifiers.
3. **Temporal Tracking**: Every mutable entity includes `created_at` (TIMESTAMPTZ) and `updated_at` (TIMESTAMPTZ).
4. **Append-Oriented Auditing**: Administrative, security, and spatial modifications trigger immutable `audit_logs` records.
5. **Phase-Gated Evolution**: Phase 1 implements User, Organization, Jurisdiction, AuditLog, and RefreshToken models with spatial capability verified. Later phases extend this baseline via versioned migrations.

---

## 2. Phase 1 Core Relational Entities

### 2.1 `organizations`
Represents the municipal body, state revenue department, or cadastral surveying agency.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier |
| `name` | VARCHAR(255) | NOT NULL, UNIQUE | Official organization name |
| `code` | VARCHAR(64) | NOT NULL, UNIQUE | Administrative code (e.g., `MUNI-HYD-01`) |
| `type` | VARCHAR(64) | NOT NULL | Category: `MUNICIPALITY`, `SURVEY_AGENCY`, `STATE_DEPARTMENT` |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Status flag |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Modification timestamp |

### 2.2 `jurisdictions`
Defines an administrative boundary (ward, tehsil, district) governing parcels.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique identifier |
| `organization_id` | UUID | NOT NULL, REFERENCES organizations(id) | Parent organization |
| `name` | VARCHAR(255) | NOT NULL | Boundary name (e.g., `Ward 101 - Gachibowli`) |
| `code` | VARCHAR(64) | NOT NULL, UNIQUE | Jurisdiction code (e.g., `JUR-W101`) |
| `level` | VARCHAR(64) | NOT NULL | Hierarchy level: `STATE`, `DISTRICT`, `MANDAL`, `WARD` |
| `srid` | INTEGER | NOT NULL, DEFAULT 4326 | Native/preferred spatial reference system |
| `boundary` | GEOMETRY(MultiPolygon, 4326) | NULLABLE | Spatial boundary of the jurisdiction (PostGIS) |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | Active operational state |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Modification timestamp |

*Index*: `CREATE INDEX idx_jurisdictions_boundary ON jurisdictions USING GIST (boundary);`

### 2.3 `users`
System accounts across all administrative and public tiers.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique user identifier |
| `email` | VARCHAR(255) | NOT NULL, UNIQUE | User email address (login credential) |
| `username` | VARCHAR(100) | NOT NULL, UNIQUE | User handle |
| `full_name` | VARCHAR(255) | NOT NULL | Display name |
| `phone` | VARCHAR(32) | NULLABLE | Contact telephone |
| `password_hash` | VARCHAR(255) | NOT NULL | Argon2id or Bcrypt hash |
| `role` | VARCHAR(64) | NOT NULL | `CITIZEN`, `SURVEYOR`, `GOVERNMENT_OFFICER`, `ADMIN`, `URBAN_PLANNER` |
| `organization_id` | UUID | NULLABLE, REFERENCES organizations(id) | Affiliated organization |
| `jurisdiction_id` | UUID | NULLABLE, REFERENCES jurisdictions(id) | Assigned spatial jurisdiction |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT TRUE | User active flag |
| `is_verified` | BOOLEAN | NOT NULL, DEFAULT FALSE | Identity verification status |
| `last_login_at` | TIMESTAMPTZ | NULLABLE | Timestamp of most recent successful authentication |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Account creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Account update timestamp |

### 2.4 `refresh_tokens`
Cryptographically random session tokens for JWT rotation.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Token record ID |
| `user_id` | UUID | NOT NULL, REFERENCES users(id) ON DELETE CASCADE | Target user |
| `token_hash` | VARCHAR(255) | NOT NULL, UNIQUE | SHA-256 hash of refresh token |
| `expires_at` | TIMESTAMPTZ | NOT NULL | Expiry threshold |
| `revoked_at` | TIMESTAMPTZ | NULLABLE | Revocation timestamp |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Issuance timestamp |

### 2.5 `audit_logs`
Immutable record of all operational and security-sensitive occurrences.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Event ID |
| `actor_user_id` | UUID | NULLABLE, REFERENCES users(id) ON DELETE SET NULL | Performing user (null for system events) |
| `action` | VARCHAR(128) | NOT NULL | E.g., `USER_CREATED`, `LOGIN_SUCCESS`, `ROLE_CHANGED` |
| `entity_type` | VARCHAR(64) | NOT NULL | E.g., `USER`, `ORGANIZATION`, `JURISDICTION` |
| `entity_id` | VARCHAR(128) | NOT NULL | Stringified target ID |
| `timestamp` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Timestamp of occurrence |
| `ip_address` | VARCHAR(45) | NULLABLE | IPv4/IPv6 address |
| `user_agent` | VARCHAR(512) | NULLABLE | Client user agent |
| `details` | JSONB | NOT NULL, DEFAULT '{}'::jsonb | Key-value contextual state (diff, reason, old/new values) |

---

## 3. Phase 2 Cadastral Entities

### 3.1 `parcels`
Authoritative 2D cadastral land parcel boundary.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique parcel identifier |
| `jurisdiction_id` | UUID | NOT NULL, REFERENCES jurisdictions(id) ON DELETE CASCADE | Administrative jurisdiction |
| `parcel_number` | VARCHAR(64) | NOT NULL | Local parcel identifier |
| `parcel_code` | VARCHAR(128) | NOT NULL, UNIQUE | Global ULPIN-ready identifier (`GV-{JUR}-P{NUM}`) |
| `survey_number` | VARCHAR(64) | NULLABLE | Historical cadastral survey sheet reference |
| `subdivision_number`| VARCHAR(32) | NULLABLE | Land subdivision reference |
| `land_use` | VARCHAR(64) | NOT NULL, DEFAULT 'RESIDENTIAL' | `RESIDENTIAL`, `COMMERCIAL`, `INDUSTRIAL`, `MIXED`, etc. |
| `area` | FLOAT | NOT NULL | Geodesic ground area in square meters |
| `area_unit` | VARCHAR(32) | NOT NULL, DEFAULT 'SQ_METER' | Area measurement unit |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'ACTIVE' | `ACTIVE`, `PENDING_REVIEW`, `RETIRED`, `DISPUTED` |
| `ownership_status` | VARCHAR(32) | NOT NULL, DEFAULT 'RECORDED' | Legal status |
| `geometry` | TEXT / GEOMETRY(MultiPolygon, 4326) | NOT NULL | Canonical EPSG:4326 polygon geometry |
| `geometry_wkt` | TEXT | NOT NULL | Standard WKT representation |
| `centroid_lon` | FLOAT | NOT NULL | Geodesic centroid longitude |
| `centroid_lat` | FLOAT | NOT NULL | Geodesic centroid latitude |
| `source` | VARCHAR(128) | NOT NULL, DEFAULT 'SURVEY' | Provenance of record |

### 3.2 `properties`
Legal property ownership and municipal registry record associated with a parcel.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique property ID |
| `parcel_id` | UUID | NOT NULL, REFERENCES parcels(id) ON DELETE CASCADE | Parent cadastral parcel |
| `property_reference`| VARCHAR(128)| NOT NULL, UNIQUE | Property register code (`PROP-{JUR}-{NUM}`) |
| `property_type` | VARCHAR(64) | NOT NULL | `FREEHOLD`, `LEASEHOLD`, `COMMERCIAL`, `PUBLIC`, etc. |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'ACTIVE' | `ACTIVE`, `INACTIVE`, `DISPUTED` |
| `address` | TEXT | NOT NULL | Physical street address |
| `locality` | VARCHAR(128) | NULLABLE | Neighborhood or locality |
| `postal_code` | VARCHAR(32) | NULLABLE | Postal pincode |

### 3.3 `buildings` (Building Footprints)
2D building footprint polygon situated within a cadastral parcel.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Building footprint ID |
| `parcel_id` | UUID | NULLABLE, REFERENCES parcels(id) ON DELETE SET NULL | Host cadastral parcel |
| `building_reference`| VARCHAR(128)| NOT NULL, UNIQUE | Building reference code (`BLD-{JUR}-{NUM}`) |
| `building_type` | VARCHAR(64) | NOT NULL, DEFAULT 'RESIDENTIAL' | `RESIDENTIAL`, `COMMERCIAL`, `MIXED_USE`, `INDUSTRIAL` |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'EXISTING' | `EXISTING`, `PROPOSED`, `DEMOLISHED` |
| `area` | FLOAT | NOT NULL | Geodesic footprint ground area ($m^2$) |
| `height_estimate` | FLOAT | NULLABLE | Optional preliminary height in meters |
| `geometry` | TEXT / GEOMETRY(Polygon, 4326) | NOT NULL | Canonical EPSG:4326 footprint boundary |
| `geometry_wkt` | TEXT | NOT NULL | Standard WKT string |

---

## 4. Phase 3 3D Digital Twin & Vertical Spatial Entities

### 4.1 `building_3d_representations`
Authoritative 3D vertical representation and 2.5D extrusion parameters for a building footprint.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique 3D representation ID |
| `building_id` | UUID | NOT NULL, UNIQUE, REFERENCES buildings(id) ON DELETE CASCADE | 1-to-1 link to building footprint |
| `geometry_type` | VARCHAR(64) | NOT NULL, DEFAULT 'EXTRUSION' | Representation geometry (`EXTRUSION`, `LOD1`, `LOD2`) |
| `height` | FLOAT | NOT NULL, DEFAULT 12.0 | Vertical height $H_{roof}$ in meters |
| `height_source` | VARCHAR(64) | NOT NULL, DEFAULT 'ESTIMATED' | `SURVEY`, `GOVERNMENT_DATA`, `MANUAL`, `ESTIMATED` |
| `height_confidence`| FLOAT | NULLABLE | Confidence score (0.0 to 1.0) |
| `height_unit` | VARCHAR(32) | NOT NULL, DEFAULT 'METERS' | Vertical measurement unit |
| `base_elevation` | FLOAT | NOT NULL, DEFAULT 0.0 | Ground elevation $H_{base}$ relative to datum |
| `elevation_source` | VARCHAR(64) | NOT NULL, DEFAULT 'LOCAL_REFERENCE_PLANE' | Source of ground elevation datum |
| `vertical_reference`| VARCHAR(64) | NOT NULL, DEFAULT 'METERS_ABOVE_GROUND' | `METERS_ABOVE_GROUND`, `WGS84_ELLIPSOID`, `ORTHOMETRIC` |
| `model_source` | VARCHAR(64) | NOT NULL, DEFAULT 'EXTRUDED_FOOTPRINT' | Generating pipeline |
| `model_version` | INTEGER | NOT NULL, DEFAULT 1 | Incremental revision version |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'ACTIVE' | `ACTIVE`, `SUPERSEDED`, `ARCHIVED` |

### 4.2 `threed_assets`
3D model assets, glTF/GLB packages, and cached extrusion files.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Asset identifier |
| `building_id` | UUID | NULLABLE, REFERENCES buildings(id) ON DELETE CASCADE | Associated building |
| `representation_id`| UUID | NULLABLE, REFERENCES building_3d_representations(id) ON DELETE CASCADE | Associated 3D representation |
| `asset_type` | VARCHAR(64) | NOT NULL, DEFAULT 'EXTRUSION' | `EXTRUSION`, `GLTF`, `GLB`, `CITYGML` |
| `storage_location` | VARCHAR(512) | NOT NULL | URI or virtual path to 3D asset |
| `format` | VARCHAR(64) | NOT NULL, DEFAULT 'JSON_EXTRUSION' | File/serialization format |
| `version` | INTEGER | NOT NULL, DEFAULT 1 | Asset asset revision |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'ACTIVE' | `ACTIVE`, `PROCESSING`, `DEPRECATED` |
| `source` | VARCHAR(64) | NOT NULL, DEFAULT 'SYSTEM_GENERATED' | Ingestion or compilation source |
| `metadata_json` | TEXT | NULLABLE | Supplementary technical metadata |

---

## 5. Phase 4 Building, Floor & Unit Hierarchy Entities

### 5.1 `floors`
Authoritative vertical floor slab slicing within a building footprint ($Z_{min} \dots Z_{max}$).

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique floor identifier |
| `building_id` | UUID | NOT NULL, REFERENCES buildings(id) ON DELETE CASCADE | Parent host building footprint |
| `floor_number` | INTEGER | NOT NULL | Zero-indexed level designation (e.g. `0`=Ground, `1`=Level 1, `-1`=Basement) |
| `floor_code` | VARCHAR(128) | NOT NULL | Systematic floor code (`{BLD_REF}-F{NUM}`) |
| `floor_name` | VARCHAR(255) | NULLABLE | Human-readable floor name (e.g., "Ground Floor Lobby & Retail") |
| `floor_type` | VARCHAR(64) | NOT NULL, DEFAULT 'COMMERCIAL' | `RESIDENTIAL`, `COMMERCIAL`, `MIXED_USE`, `PARKING`, `BASEMENT` |
| `elevation_min_m` | FLOAT | NOT NULL | Base floor slab elevation $Z_{min}$ relative to building base |
| `elevation_max_m` | FLOAT | NOT NULL | Top floor slab elevation $Z_{max}$ relative to building base |
| `height_m` | FLOAT | NOT NULL | Vertical floor slab thickness: $\Delta H = Z_{max} - Z_{min} > 0$ |
| `area_sqm` | FLOAT | NULLABLE | Floor slab horizontal area ($m^2$) |
| `geometry` | GEOMETRY(Polygon, 4326) | NULLABLE | Floor slab horizontal polygon (defaults to building footprint) |
| `geometry_wkt` | TEXT | NULLABLE | WKT polygon representation |
| `confidence` | FLOAT | NULLABLE | Confidence score (0.0 to 1.0) |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'ACTIVE' | `ACTIVE`, `INACTIVE`, `UNDER_CONSTRUCTION`, `DEMOLISHED` |
| `source` | VARCHAR(64) | NOT NULL, DEFAULT 'SURVEY' | `SURVEY`, `ARCHITECTURAL_PLAN`, `MANUAL`, `ESTIMATED` |

*Table Constraints*:
- `UNIQUE(building_id, floor_number)`: Strict uniqueness constraint per building floor number.
- `CHECK(elevation_max_m > elevation_min_m)`: Guarantees positive elevation thickness.

### 5.2 `property_units`
Spatial subdivisions of a floor slab representing distinct rentable, salable, or privately owned property units.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique property unit identifier |
| `floor_id` | UUID | NOT NULL, REFERENCES floors(id) ON DELETE CASCADE | Parent floor slab |
| `building_id` | UUID | NOT NULL, REFERENCES buildings(id) ON DELETE CASCADE | Parent host building footprint |
| `property_id` | UUID | NULLABLE, REFERENCES properties(id) ON DELETE SET NULL | Optional legal cadastral property attachment |
| `unit_number` | VARCHAR(64) | NOT NULL | Local unit designation (e.g. "101", "Penthouse A") |
| `unit_code` | VARCHAR(128) | NOT NULL, UNIQUE | Systematic unique code (`{BLD_REF}-U{NUM}`) |
| `unit_type` | VARCHAR(64) | NOT NULL, DEFAULT 'APARTMENT' | `APARTMENT`, `OFFICE`, `RETAIL_SHOP`, `WAREHOUSE`, `COMMON_AREA` |
| `use_category` | VARCHAR(64) | NOT NULL, DEFAULT 'OFFICE' | Sub-category of economic or residential usage |
| `gross_area_sqm` | FLOAT | NOT NULL, DEFAULT 0.0 | Gross built-up area ($m^2$) |
| `net_area_sqm` | FLOAT | NOT NULL, DEFAULT 0.0 | Carpet/usable area ($m^2$), strictly $\le gross\_area$ |
| `elevation_min_m` | FLOAT | NOT NULL | Base unit elevation relative to building base |
| `elevation_max_m` | FLOAT | NOT NULL | Top unit elevation relative to building base |
| `height_m` | FLOAT | NOT NULL | Vertical unit prism height ($m$) |
| `geometry` | GEOMETRY(Polygon, 4326) | NOT NULL | Horizontal unit boundary polygon |
| `geometry_wkt` | TEXT | NOT NULL | Standard WKT polygon |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'ACTIVE' | `ACTIVE`, `INACTIVE`, `UNDER_RENOVATION`, `VACANT` |
| `ownership_status`| VARCHAR(64) | NOT NULL, DEFAULT 'PRIVATE' | `OWNED`, `OCCUPIED`, `LEASED`, `VACANT`, `MORTGAGED`, `COMMON` |

*Table Constraints*:
- `UNIQUE(floor_id, unit_number)`: Disallows duplicate unit designations on the same floor slab.
- `CHECK(elevation_max_m > elevation_min_m)`: Guarantees positive unit vertical height.

---

## 6. Spatial Reference Strategy & Vertical Datums

1. **Horizontal Standard (EPSG:4326 - WGS 84)**: All geometries stored in base database columns are standardized to EPSG:4326 in lon/lat coordinates.
2. **Vertical Reference Datums**:
   - `METERS_ABOVE_GROUND`: Standard terrestrial reference plane where ground = $0.0m$ and extruded height = $H_{roof}$.
   - `LOCAL_REFERENCE_PLANE`: Local municipal benchmark datum.
   - `WGS84_ELLIPSOID`: Absolute ellipsoidal height ($h = H + N$).
3. **Geodesic Math**: Area and volume calculations utilize `pyproj.Geod(ellps="WGS84")` for curvature-accurate metrics.

---

## 7. Entity Relationship Architecture (Phases 1-5 Complete)

```
[organizations] 1 ──< [jurisdictions] 1 ──< [parcels]
       │                        │                 │ 1
       │                        │                 ├──────────────┐
       │                        │                 ▼ *            ▼ *
       │                        │           [properties]    [buildings]
       │                        │                ▲               │ 1
       │                        │                │ (optional)    ├─────────────────────────────┐
       │                        │                │               ▼ 1                           ▼ 1
       │                        │                │ [building_3d_representations]            [floors]
       │                        │                │               │ 1                           │ 1
       │                        │                │               ▼ *                           ▼ *
       │                        │                └─────── [property_units] ◄───────────────────┘
       │                        │
       ▼ *                      ▼ *
[survey_projects] 1 ──< [survey_assignments] 1 ──< [survey_sessions] 1 ──< [survey_observations]
                               │                           │                     ▲
                               │ 1                         │ 1                   │ 0..1
                               │                           ├─────────────────────┴──< [survey_evidence]
                               ▼ *                         ▼ *
                      [survey_submissions]       [sync_operations]
```

---

## 8. Phase 5 Surveyor Field Workflow & Cadastral Data Collection Entities

### 8.1 `survey_projects`
Campaign-level grouping of cadastral survey operations within an administrative jurisdiction.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique project identifier |
| `organization_id` | UUID | NOT NULL, REFERENCES organizations(id) | Managing organization |
| `jurisdiction_id` | UUID | NOT NULL, REFERENCES jurisdictions(id) | Administrative boundary scope |
| `name` | VARCHAR(255) | NOT NULL | Project name (e.g., "CBD Cadastral Audit 2026") |
| `code` | VARCHAR(64) | NOT NULL, UNIQUE | Systematic project identifier |
| `description` | TEXT | NULLABLE | Campaign objectives and operational scope |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'DRAFT' | `DRAFT`, `ACTIVE`, `PAUSED`, `COMPLETED`, `CANCELLED` |
| `start_date` | TIMESTAMPTZ | NULLABLE | Planned or actual commencement date |
| `end_date` | TIMESTAMPTZ | NULLABLE | Planned or actual completion date |
| `created_by` | UUID | NULLABLE, REFERENCES users(id) | Officer who created the project |

### 8.2 `survey_assignments`
Actionable field assignments dispatched to licensed surveyors targeting specific cadastre features.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique assignment identifier |
| `survey_project_id` | UUID | NOT NULL, REFERENCES survey_projects(id) ON DELETE CASCADE | Parent survey project |
| `surveyor_id` | UUID | NOT NULL, REFERENCES users(id) ON DELETE RESTRICT | Assigned field surveyor |
| `jurisdiction_id` | UUID | NOT NULL, REFERENCES jurisdictions(id) | Governing jurisdiction |
| `parcel_id` | UUID | NULLABLE, REFERENCES parcels(id) ON DELETE SET NULL | Target cadastral land parcel |
| `property_id` | UUID | NULLABLE, REFERENCES properties(id) ON DELETE SET NULL | Target legal property record |
| `building_id` | UUID | NULLABLE, REFERENCES buildings(id) ON DELETE SET NULL | Target building footprint |
| `floor_id` | UUID | NULLABLE, REFERENCES floors(id) ON DELETE SET NULL | Target vertical floor slab |
| `unit_id` | UUID | NULLABLE, REFERENCES property_units(id) ON DELETE SET NULL | Target property unit |
| `priority` | VARCHAR(16) | NOT NULL, DEFAULT 'MEDIUM' | `LOW`, `MEDIUM`, `HIGH`, `URGENT` |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'ASSIGNED' | `ASSIGNED`, `ACCEPTED`, `IN_PROGRESS`, `SUBMITTED`, `UNDER_REVIEW`, `REVISION_REQUIRED`, `APPROVED`, `REJECTED`, `CANCELLED` |
| `assigned_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Assignment dispatch timestamp |
| `started_at` | TIMESTAMPTZ | NULLABLE | Surveyor commencement timestamp |
| `completed_at` | TIMESTAMPTZ | NULLABLE | Officer approval timestamp |
| `due_at` | TIMESTAMPTZ | NULLABLE | Field survey deadline |
| `notes` | TEXT | NULLABLE | Officer briefing instructions or revision notes |

### 8.3 `survey_sessions`
Active field collection periods conducted by a surveyor on a mobile/PWA device.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique session identifier |
| `assignment_id` | UUID | NOT NULL, REFERENCES survey_assignments(id) ON DELETE CASCADE | Associated survey assignment |
| `surveyor_id` | UUID | NOT NULL, REFERENCES users(id) ON DELETE CASCADE | Field surveyor executing the session |
| `started_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Field session start timestamp |
| `ended_at` | TIMESTAMPTZ | NULLABLE | Session termination timestamp |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'DRAFT' | `DRAFT`, `ACTIVE`, `PAUSED`, `COMPLETED`, `SYNC_PENDING`, `SYNCED`, `SUBMITTED` |
| `device_identifier` | VARCHAR(128) | NULLABLE | Client device UUID / user-agent fingerprint |
| `app_version` | VARCHAR(32) | NULLABLE, DEFAULT '1.0.0' | Client software version |
| `sync_status` | VARCHAR(32) | NOT NULL, DEFAULT 'SYNCED' | `SYNCED`, `PENDING`, `CONFLICT` |
| `notes` | TEXT | NULLABLE | Surveyor operational notes |

### 8.4 `survey_observations`
Atomic field measurements and qualitative observations captured with GPS positioning metrics.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique observation identifier |
| `session_id` | UUID | NOT NULL, REFERENCES survey_sessions(id) ON DELETE CASCADE | Parent collection session |
| `observation_type` | VARCHAR(64) | NOT NULL | `BUILDING_HEIGHT`, `FLOOR_COUNT`, `UNIT_AREA`, `BUILDING_TYPE`, `LAND_USE`, `STRUCTURAL_CONDITION`, `BOUNDARY_VERIFICATION`, `GENERAL_NOTE` |
| `target_type` | VARCHAR(32) | NOT NULL | `BUILDING`, `PARCEL`, `PROPERTY`, `FLOOR`, `UNIT` |
| `target_id` | VARCHAR(36) | NOT NULL | Target feature identifier |
| `value` | TEXT | NOT NULL | Measured observation value |
| `unit` | VARCHAR(32) | NULLABLE | Unit of measurement (`m`, `floors`, `sq_m`, `sq_ft`) |
| `notes` | TEXT | NULLABLE | Qualitative remarks or discrepancy notes |
| `captured_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Exact observation timestamp |
| `captured_by` | UUID | NULLABLE, REFERENCES users(id) ON DELETE SET NULL | Surveyor user ID |
| `latitude` | FLOAT | NULLABLE | WGS84 Latitude coordinate |
| `longitude` | FLOAT | NULLABLE | WGS84 Longitude coordinate |
| `horizontal_accuracy` | FLOAT | NULLABLE | Reported GPS horizontal accuracy in meters (e.g. `3.8`) |
| `altitude` | FLOAT | NULLABLE | Terrestrial altitude in meters |
| `vertical_accuracy` | FLOAT | NULLABLE | Reported vertical positioning accuracy in meters |
| `source` | VARCHAR(64) | NOT NULL, DEFAULT 'FIELD_OBSERVATION' | `FIELD_OBSERVATION`, `DEVICE_GPS`, `GNSS`, `MANUAL_MEASUREMENT` |
| `geometry` | GEOMETRY(Geometry, 4326) | NULLABLE | Point or polyline measurement feature |
| `geometry_wkt` | TEXT | NULLABLE | Geometry WKT representation |

### 8.5 `survey_evidence`
Photographic and documentary evidence stored in protected object storage with SHA-256 cryptographic verification.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique evidence identifier |
| `session_id` | UUID | NOT NULL, REFERENCES survey_sessions(id) ON DELETE CASCADE | Parent survey session |
| `observation_id` | UUID | NULLABLE, REFERENCES survey_observations(id) ON DELETE SET NULL | Optional linked observation |
| `target_type` | VARCHAR(32) | NOT NULL, DEFAULT 'BUILDING' | `BUILDING`, `PARCEL`, `PROPERTY`, `FLOOR`, `UNIT` |
| `target_id` | VARCHAR(36) | NOT NULL | Associated entity identifier |
| `storage_key` | VARCHAR(512) | NOT NULL | Internal relative path in object storage (`uploads/evidence/...`) |
| `filename` | VARCHAR(255) | NOT NULL | Original uploaded filename |
| `mime_type` | VARCHAR(128) | NOT NULL, DEFAULT 'image/jpeg' | Media MIME type |
| `file_size` | INTEGER | NOT NULL, DEFAULT 0 | File size in bytes (max 25MB) |
| `evidence_type` | VARCHAR(64) | NOT NULL, DEFAULT 'BUILDING_FACADE' | `BUILDING_FACADE`, `BOUNDARY_MARKER`, `ACCESS_POINT`, `FLOOR_LAYOUT`, `ROOF_STRUCTURE`, `SURROUNDINGS`, `OTHER` |
| `captured_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Photography timestamp |
| `latitude` | FLOAT | NULLABLE | Geotagged latitude coordinate |
| `longitude` | FLOAT | NULLABLE | Geotagged longitude coordinate |
| `accuracy` | FLOAT | NULLABLE | Positioning accuracy in meters |
| `description` | TEXT | NULLABLE | Caption / photo description |
| `sha256_hash` | VARCHAR(64) | NOT NULL | Cryptographic SHA-256 integrity checksum |
| `uploaded_by` | UUID | NULLABLE, REFERENCES users(id) ON DELETE SET NULL | Uploader user ID |

### 8.6 `survey_submissions`
Official versioned evidence packages submitted for municipal review and adjudication.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique submission identifier |
| `assignment_id` | UUID | NOT NULL, REFERENCES survey_assignments(id) ON DELETE CASCADE | Target survey assignment |
| `survey_session_id` | UUID | NOT NULL, REFERENCES survey_sessions(id) ON DELETE CASCADE | Submitted field session |
| `version_number` | INTEGER | NOT NULL, DEFAULT 1 | Sequential submission version (v1, v2, ...) |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'SUBMITTED' | `SUBMITTED`, `UNDER_REVIEW`, `APPROVED`, `REVISION_REQUIRED`, `REJECTED` |
| `snapshot_data` | TEXT | NOT NULL | JSON snapshot of observations, evidence, and validation summary |
| `submitted_by` | UUID | NOT NULL, REFERENCES users(id) ON DELETE RESTRICT | Surveyor submitting the package |
| `submitted_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Submission timestamp |
| `reviewed_by` | UUID | NULLABLE, REFERENCES users(id) ON DELETE SET NULL | Reviewing cadastral officer |
| `reviewed_at` | TIMESTAMPTZ | NULLABLE | Adjudication timestamp |
| `review_notes` | TEXT | NULLABLE | Official review comments, revision directives, or rejection reasons |

### 8.7 `sync_operations`
Audit log of mobile/offline synchronization queue transactions supporting client idempotency.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique transaction log ID |
| `client_operation_id` | VARCHAR(128) | NOT NULL, UNIQUE | Client-generated idempotency token |
| `session_id` | UUID | NULLABLE, REFERENCES survey_sessions(id) ON DELETE SET NULL | Target session |
| `operation_type` | VARCHAR(64) | NOT NULL | `CREATE_OBSERVATION`, `CREATE_EVIDENCE`, `UPDATE_SESSION` |
| `entity_type` | VARCHAR(64) | NOT NULL | Entity domain |
| `entity_id` | VARCHAR(64) | NOT NULL | Client-side temporary or permanent ID |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'PENDING' | `PENDING`, `SYNCED`, `CONFLICT`, `FAILED` |
| `error_message` | TEXT | NULLABLE | Diagnostic details if synchronization failed |
| `server_entity_id` | VARCHAR(64) | NULLABLE | Resulting server UUID after ingestion |

---

## 9. Phase 13 Audit, Versioning, Lineage & Governance Schema

### 9.1 `audit_logs` (Extended)
Authoritative, append-only, tamper-evident audit ledger capturing all domain actions and administrative modifications.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Primary key |
| `event_id` | VARCHAR(64) | NOT NULL, UNIQUE | Deterministic UUID/string event identifier |
| `timestamp` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Clock timestamp of the audit event |
| `category` | VARCHAR(64) | NOT NULL, DEFAULT 'SYSTEM' | Category: `SECURITY`, `AUTHENTICATION`, `AUTHORIZATION`, `CADASTRAL_MODIFICATION`, `AI_LIFECYCLE`, `FIELD_SURVEY`, `WORKFLOW_STATE`, `DATA_EXPORT`, `RESTORATION`, `SYSTEM` |
| `action` | VARCHAR(128) | NOT NULL | Action identifier (e.g. `VERSION_RESTORED`, `SERVICE_REQUEST_TRANSITIONED`) |
| `actor_id` | UUID | NULLABLE, REFERENCES users(id) ON DELETE SET NULL | User ID who triggered the action |
| `actor_role` | VARCHAR(64) | NULLABLE | User role at time of action |
| `ip_address` | VARCHAR(64) | NULLABLE | Client IP address |
| `user_agent` | VARCHAR(256) | NULLABLE | Client user agent header |
| `request_id` | VARCHAR(64) | NULLABLE | Distributed tracing HTTP request correlation ID |
| `correlation_id` | VARCHAR(64) | NULLABLE | Multi-service workflow correlation ID |
| `target_type` | VARCHAR(64) | NULLABLE | Domain entity type (`PARCEL`, `BUILDING`, `UNIT`, etc.) |
| `target_id` | VARCHAR(64) | NULLABLE | Entity ID |
| `severity` | VARCHAR(32) | NOT NULL, DEFAULT 'INFO' | `DEBUG`, `INFO`, `NOTICE`, `WARNING`, `ERROR`, `CRITICAL`, `ALERT`, `EMERGENCY` |
| `result` | VARCHAR(32) | NOT NULL, DEFAULT 'SUCCESS' | `SUCCESS`, `FAILURE`, `DENIED`, `ERROR`, `PENDING` |
| `reason` | TEXT | NULLABLE | Justification or human rationale |
| `source_type` | VARCHAR(64) | NOT NULL, DEFAULT 'API' | `WEB_UI`, `API`, `BACKGROUND_WORKER`, `SYSTEM_JOB`, `MOBILE_SYNC` |
| `before_snapshot` | JSON / TEXT | NULLABLE | JSON snapshot of entity state prior to modification |
| `after_snapshot` | JSON / TEXT | NULLABLE | JSON snapshot of entity state following modification |
| `changed_fields` | JSON / TEXT | NULLABLE | List of modified attribute/geometry field names |
| `checksum` | VARCHAR(64) | NULLABLE | SHA-256 integrity hash of the audit entry |
| `extra_metadata` | JSON / TEXT | NULLABLE | Additional context and metadata |

### 9.2 `entity_versions`
Immutable temporal version ledger storing geometric and attribute snapshots with deterministic versioning.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique snapshot ID |
| `entity_type` | VARCHAR(64) | NOT NULL | `PARCEL`, `BUILDING`, `FLOOR`, `UNIT`, `UTILITY_ASSET`, `SERVICE_REQUEST` |
| `entity_id` | VARCHAR(64) | NOT NULL | Foreign reference to live domain entity |
| `version_number` | INTEGER | NOT NULL | Monotonically increasing sequential version ($v1, v2, ...$) |
| `status` | VARCHAR(32) | NOT NULL, DEFAULT 'CURRENT' | `SUPERSEDED`, `CURRENT`, `REVERTED`, `ARCHIVED`, `DRAFT` |
| `change_type` | VARCHAR(64) | NOT NULL, DEFAULT 'UPDATE' | `INITIAL_CREATION`, `UPDATE`, `SUBDIVISION`, `CONSOLIDATION`, `BOUNDARY_ADJUSTMENT`, `AI_CORRECTION`, `FIELD_SURVEY_UPDATE`, `RESTORATION`, `ADMINISTRATIVE_CORRECTION` |
| `change_summary` | TEXT | NULLABLE | Human-readable explanation of change |
| `change_reason` | TEXT | NULLABLE | Legal or administrative justification |
| `effective_from` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Valid start timestamp for this snapshot |
| `effective_to` | TIMESTAMPTZ | NULLABLE | Valid end timestamp (NULL for CURRENT) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Creation timestamp |
| `created_by` | UUID | NULLABLE, REFERENCES users(id) ON DELETE SET NULL | Author user ID |
| `created_by_role` | VARCHAR(64) | NULLABLE | Author role at creation |
| `source_type` | VARCHAR(64) | NOT NULL, DEFAULT 'MANUAL' | `MANUAL`, `AI_INFERENCE`, `FIELD_SURVEY`, `DOCUMENT_OCR`, `SYSTEM_MIGRATION`, `CITIZEN_SUBMISSION`, `ROLLBACK` |
| `source_id` | VARCHAR(64) | NULLABLE | Identifier of source record or restored version |
| `geometry_wkt` | TEXT | NULLABLE | Well-Known Text geometry snapshot |
| `geometry_geojson` | JSON / TEXT | NULLABLE | GeoJSON representation of geometry |
| `geometry_hash` | VARCHAR(64) | NULLABLE | SHA-256 cryptographic hash of geometry WKT |
| `area_sqm` | FLOAT | NULLABLE | Spatial metric: planar polygon area in $m^2$ |
| `perimeter_m` | FLOAT | NULLABLE | Spatial metric: boundary perimeter in $m$ |
| `centroid_x` | FLOAT | NULLABLE | Spatial metric: planar centroid longitude / X |
| `centroid_y` | FLOAT | NULLABLE | Spatial metric: planar centroid latitude / Y |
| `bbox_minx`, `bbox_miny`, `bbox_maxx`, `bbox_maxy` | FLOAT | NULLABLE | Spatial metric: 2D bounding envelope |
| `elevation_m` | FLOAT | NULLABLE | 3D base elevation |
| `height_m` | FLOAT | NULLABLE | 3D vertical height |
| `attributes` | JSON / TEXT | NOT NULL, DEFAULT '{}' | Complete dictionary snapshot of entity attributes |
| `content_hash` | VARCHAR(64) | NOT NULL | SHA-256 cryptographic checksum of normalized content |
| `parent_version_id` | UUID | NULLABLE, REFERENCES entity_versions(id) ON DELETE SET NULL | Preceding snapshot version in timeline |

### 9.3 `entity_lineages`
Graph relationship edges capturing entity provenance and lifecycle transformations.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Lineage edge ID |
| `parent_entity_type` | VARCHAR(64) | NOT NULL | Parent entity domain |
| `parent_entity_id` | VARCHAR(64) | NOT NULL | Parent entity identifier |
| `parent_version_id` | UUID | NULLABLE, REFERENCES entity_versions(id) ON DELETE SET NULL | Parent version reference |
| `child_entity_type` | VARCHAR(64) | NOT NULL | Child entity domain |
| `child_entity_id` | VARCHAR(64) | NOT NULL | Child entity identifier |
| `child_version_id` | UUID | NULLABLE, REFERENCES entity_versions(id) ON DELETE SET NULL | Child version reference |
| `relationship` | VARCHAR(64) | NOT NULL | `SPLIT_FROM`, `MERGED_INTO`, `DERIVED_FROM`, `SUPERSEDES`, `REPLACES`, `RESTORED_FROM` |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Edge recording timestamp |
| `created_by` | UUID | NULLABLE, REFERENCES users(id) ON DELETE SET NULL | User who created relationship |
| `reason` | TEXT | NULLABLE | Operational or legal explanation |
| `lineage_metadata` | JSON / TEXT | NULLABLE | Additional transformation parameters |

### 9.4 `notification_preferences`
User-level notification routing configuration governing alert delivery channels with safety protection for mandatory security alerts.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Preference record ID |
| `user_id` | UUID | NOT NULL, REFERENCES users(id) ON DELETE CASCADE | Target user ID |
| `category` | VARCHAR(64) | NOT NULL | Notification category |
| `channel_in_app` | BOOLEAN | NOT NULL, DEFAULT true | In-app notification center routing |
| `channel_email` | BOOLEAN | NOT NULL, DEFAULT true | Email dispatch routing |
| `digest_frequency` | VARCHAR(32) | NOT NULL, DEFAULT 'INSTANT' | `INSTANT`, `DAILY_DIGEST`, `WEEKLY_DIGEST`, `OFF` |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Last update timestamp |




