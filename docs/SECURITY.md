# GeoVertex Security Architecture & Hardening Guide

## 1. Security Overview & Threat Model

GeoVertex operates as an authoritative cadastral and spatial boundary intelligence platform. Because property boundaries, vertical unit rights, ownership deeds, and underground utility alignments carry legal and financial significance, the platform enforces defense-in-depth principles across all architectural tiers.

### Threat Model & Mitigations

| Threat Vector | Potential Impact | GeoVertex Security Controls |
| :--- | :--- | :--- |
| **Cadastral Boundary Tampering** | Unauthorized shifting of parcel/unit boundaries | Immutable audit ledger (Phase 13), cryptographic SHA-256 snapshots, approval workflows requiring CADASTRAL_OFFICER role |
| **Deed Document Forgery / Replacement** | Fraudulent ownership claims | SHA-256 cryptographic digest verified at ingestion and stored in database; path-traversal resistant storage abstraction |
| **Authentication & Token Hijacking** | Impersonation of surveyors/officers | Short-lived JWTs (60 min), refresh token rotation, token revocation blacklist via Redis, bcrypt password hashing |
| **Spatial Injection / Malformed WKT/GeoJSON** | Buffer overflows in spatial engines, DoS | Deterministic Shapely/GEOS validation, strict GeoJSON schema checks, coordinate bounds clamping |
| **Denial of Service (DoS) & Brute Force** | System exhaustion | In-memory token bucket rate limiting on `/api/v1/auth/*` (10 req/s) and general API (50 req/s), Nginx connection limits |

---

## 2. Authentication & Authorization Architecture

### 2.1 Role-Based Access Control (RBAC) Matrix

| Cadastral Resource / Action | Citizen | Surveyor | Cadastral Officer | System Admin |
| :--- | :---: | :---: | :---: | :---: |
| View Public Cadastral Map & 3D Twins | Read-only | Read-only | Read-only | Full |
| Submit Citizen Title Search / Dispute | Create | None | Review/Approve | Full |
| Create Field Survey & Capture Points | None | Create/Edit | Review | Full |
| Run AI Building Extraction Pipeline | None | Read-only | Execute/Approve | Full |
| Run Topology Validation & Resolve Violations | None | Read-only | Resolve/Approve | Full |
| Issue / Revoke Technical 3D Property Identifiers | None | None | Generate/Supersede | Full |
| Manage System Governance, Roles & Schemas | None | None | None | Full |
| View Cryptographic Audit Logs | None | None | Read-only | Full |

### 2.2 Token Lifecycle & Session Management
- **Access Tokens**: JWT encoded with HMAC-SHA256 (`HS256`). Standard expiration is 60 minutes.
- **Refresh Tokens**: Cryptographically random UUID4 tokens stored in Redis with 7-day TTL. Every refresh event invalidates the previous token (single-use rotation).
- **Revocation**: Logout immediately blacklists the active token in Redis with a TTL equal to remaining lifetime.

---

## 3. Cryptographic Data Protection

### 3.1 Data in Transit
- TLS 1.3 is enforced with forward secrecy. TLS 1.0 and 1.1 are explicitly disabled.
- HTTP Strict Transport Security (`HSTS`) header: `max-age=31536000; includeSubDomains; preload`.

### 3.2 Document Integrity & Tamper Proofing
- When a cadastral deed, survey diagram, or floor plan is uploaded:
  1. The SHA-256 cryptographic hash is computed over the raw byte stream.
  2. The hash is saved immutably in the `documents` table alongside the document metadata.
  3. Every subsequent download verifies that the stored file hash matches the metadata record. Any tampering triggers immediate alert logging and an HTTP 409 conflict.

### 3.3 Directory Traversal Protection
- Document storage operations reject paths containing `..`, null bytes, or absolute path traversal sequences.
- Paths are resolved against a strictly bounded base directory:
  ```python
  target_path = (self.base_dir / storage_key).resolve()
  if not str(target_path).startswith(str(self.base_dir.resolve())):
      raise BadRequestException("Invalid storage key path: directory traversal attempt detected")
  ```

---

## 4. Hardened Security Headers

The production Nginx reverse proxy injects the following security headers:

```nginx
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(self)" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline' blob:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: blob: https:; connect-src 'self' https: http: ws: wss: data: blob:; worker-src 'self' blob:; child-src 'self' blob:; frame-ancestors 'none'; object-src 'none'; base-uri 'self';" always;
```

---

## 5. Security Incident Reporting & Vulnerability Disclosure

Vulnerabilities should be reported responsibly to the GeoVertex Security Team:
- **Email**: `security@geovertex.gov`
- **Response SLA**: Initial triage within 24 hours; remediation patch within 7 business days for critical findings.
