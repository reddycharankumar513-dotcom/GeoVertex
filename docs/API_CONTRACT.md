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
- **Purpose**: Query security, administrative, and operational events.
- **Auth**: Bearer Token (`ADMIN` only)
- **Query Params**: `entity_type`, `action`, `actor_user_id`, `page`, `size`
- **Response `200 OK`**: Paginated list of AuditLog items.
