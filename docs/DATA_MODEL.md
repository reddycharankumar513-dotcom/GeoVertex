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

## 7. Entity Relationship Architecture (Phases 1-4 Complete)

```
[organizations] 1 ──< [jurisdictions] 1 ──< [parcels]
                                                │ 1
                                                ├──────────────┐
                                                ▼ *            ▼ *
                                          [properties]    [buildings]
                                               ▲               │ 1
                                               │ (optional)    ├─────────────────────────────┐
                                               │               ▼ 1                           ▼ 1
                                               │ [building_3d_representations]            [floors]
                                               │               │ 1                           │ 1
                                               │               ▼ *                           ▼ *
                                               └─────── [property_units] ◄───────────────────┘
```


