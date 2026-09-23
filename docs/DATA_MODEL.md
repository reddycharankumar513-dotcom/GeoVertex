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

## 3. Spatial Reference Strategy & PostGIS Integration

GeoVertex maintains high cartographic and surveying accuracy by adopting a dual CRS standard:
1. **Global Storage & Interchange (EPSG:4326 - WGS 84)**: All geometries stored in base database columns are standardized to EPSG:4326 in lon/lat or lon/lat/height coordinates for maximum web compatibility (GeoJSON, CesiumJS, MapLibre).
2. **Local Metric Calculation (Projected CRS - UTM or Local State Planes)**: Geodetic distance, 3D volume, and 2D area calculations are evaluated dynamically using `ST_Transform(geom, target_epsg)` or PostGIS geography types to guarantee metric fidelity down to millimeter precision.

### Spatial Types by Cadastral Entity (Phases 2-10 Roadmap)
- **Parcels**: `GEOMETRY(MultiPolygon, 4326)`
- **Buildings**: `GEOMETRY(MultiPolygonZ, 4326)` (Footprint extruded with Base and Roof heights)
- **Floors**: `GEOMETRY(PolygonZ, 4326)` (Height-delimited vertical slice)
- **Units**: `GEOMETRY(PolyhedralSurfaceZ, 4326)` or `MultiPolygonZ` (Volumetric spatial object)
- **Utilities**: `GEOMETRY(LineStringZ, 4326)` (Subsurface coordinates with depth attribute)

---

## 4. Forward Entity Schemas (Phases 2-15 Preview)

```
[organizations] 1 ──< [jurisdictions] 1 ──< [parcels]
                                                │
                                    ┌───────────┴───────────┐
                                    ▼                       ▼
                              [buildings]             [utilities]
                                    │
                                    ▼
                                 [floors]
                                    │
                                    ▼
                                 [units]
```

All future entities map directly to the technical property identifier schema:
- Parcel: `GV-{JURISDICTION}-{PARCEL_SERIAL}`
- Building: `GV-{JURISDICTION}-{PARCEL_SERIAL}-B{NUM}`
- Floor: `GV-{JURISDICTION}-{PARCEL_SERIAL}-B{NUM}-F{NUM}`
- Unit: `GV-{JURISDICTION}-{PARCEL_SERIAL}-B{NUM}-F{NUM}-U{NUM}`
