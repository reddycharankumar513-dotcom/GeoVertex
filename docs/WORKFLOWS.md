# GEOVERTEX: USER WORKFLOWS SPECIFICATION
## State Machines, Role-Based Lifecycles, and Review Gates

Version: 1.0  
Status: Authoritative Workflow Specification  
Associated Documents: [MASTER_PRD.md](MASTER_PRD.md), [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 1. Property Record Lifecycle & State Machine

Every cadastral property object (Parcel, Building, Floor, Unit) progresses through an immutable state machine:

```
                  ┌──────────────┐
                  │    DRAFT     │
                  └──────┬───────┘
                         │ Surveyor uploads survey / triggers AI
                         ▼
                  ┌──────────────┐
                  │  PROCESSING  │
                  └──────┬───────┘
                         │ AI & GIS processing completes
                         ▼
                  ┌──────────────┐
                  │ AI_COMPLETED │
                  └──────┬───────┘
                         │ Surveyor corrects geometry & validates topology
                         ▼
                  ┌─────────────────┐
                  │ SURVEYOR_REVIEW │
                  └──────┬──────────┘
                         │ Surveyor signs off and submits
                         ▼
                  ┌───────────────┐
                  │   SUBMITTED   │
                  └──────┬────────┘
                         │ Officer reviews 2D, 3D, AI, Topology & Docs
                         ▼
            ┌───────────────────────────┐
            │      OFFICER_REVIEW       │
            └──────┬─────────────┬──────┘
                   │             │
      Officer      │             │ Officer
      Approves     │             │ Rejects / Revisions
                   ▼             ▼
          ┌────────────┐   ┌────────────────────────┐
          │  APPROVED  │   │ REVISION_REQUIRED /    │
          │(New Version│   │ REJECTED               │
          │ Committed) │   └────────────────────────┘
          └────────────┘
```

---

## 2. Role-Specific Workflow Specifications

### 2.1 Citizen Workflow
1. **Public Property Discovery**: Citizen searches by parcel ID, technical 3D ID, or geographic address.
2. **Restricted Inspection**: Citizen views verified public spatial boundaries (2D map and 3D building envelope) without accessing restricted ownership deeds.
3. **Discrepancy Reporting**: Citizen flags inconsistencies between real-world construction and recorded cadastral status (e.g., unauthorized construction, boundary shift).
4. **Document Submission**: Citizen uploads supporting title/deed documentation.
5. **Application Tracking**: System issues tracking reference to monitor status.

### 2.2 Surveyor Workflow
1. **Survey Mission Initialization**: Surveyor creates a new survey project tied to an authorized Jurisdiction.
2. **Raw Spatial Data Upload**: Surveyor uploads GNSS boundary survey points, drone orthomosaics, or LAS/LAZ point cloud files.
3. **Automated AI Extraction Execution**: Surveyor invokes AI building footprint or vertical floor segmentation.
4. **Interactive Geometry Correction**: Surveyor reviews AI confidence scores, manually snips/edits polygon vertices to match ground truth.
5. **Topology Verification**: Surveyor executes the spatial validation engine. If errors (overlaps, gaps) are detected, surveyor resolves them.
6. **Submission**: Surveyor generates technical 3D property identifier proposal and submits package to the Officer Review Queue.

### 2.3 Government Officer Workflow
1. **Review Queue Prioritization**: Officer views pending survey submissions filtered by jurisdiction and severity flags.
2. **Multi-Domain Inspection**:
   - 2D parcel boundary alignment.
   - 3D Digital Twin volumetric inspection.
   - Document-Spatial verification (compares deed square footage against calculated PostGIS polygon area).
   - AI extraction confidence and edge alignment.
   - Topological validation report.
3. **Authoritative Adjudication**:
   - **Approve**: Marks property status as `APPROVED`, increments version counter ($V_n \to V_{n+1}$), and persists authoritative record into PostGIS.
   - **Request Revision**: Sends submission back to Surveyor with spatial feedback notes.
   - **Reject**: Archives submission with documented justification.
4. **Audit Immutability**: Every decision creates a permanent, tamper-evident `audit_logs` entry.

### 2.4 System Administrator Workflow
1. **User Lifecycle Management**: Provision users, assign roles (`CITIZEN`, `SURVEYOR`, `GOVERNMENT_OFFICER`, `ADMIN`, `URBAN_PLANNER`), and handle deactivations.
2. **Administrative Territory Management**: Configure organizations (cadastral departments) and jurisdictions (wards, mandals).
3. **Audit & Compliance**: Search and export audit trails for system and security oversight.
4. **System Health**: Monitor live health endpoints and background queue states.

---

## 3. Surveyor Field Workflow Lifecycle & State Machine (Phase 5)

### 3.1 Assignment State Machine
Survey assignments track the field verification lifecycle for specific parcels and buildings:

```
        ┌─────────────┐
        │  ASSIGNED   │
        └──────┬──────┘
               │ Surveyor clicks "Start Survey" / starts session
               ▼
        ┌─────────────┐
   ┌───►│ IN_PROGRESS │◄───┐
   │    └──────┬──────┘    │
   │           │ Surveyor submits validated survey package
   │           ▼           │
   │    ┌─────────────┐    │
   │    │  SUBMITTED  │    │
   │    └──────┬──────┘    │
   │           │ Officer reviews submission
   │     ┌─────┴───────────────┬────────────────┐
   │     │                     │                │
   │     ▼                     ▼                ▼
   │ ┌──────────┐     ┌─────────────────┐ ┌──────────┐
   │ │ APPROVED │     │REVISION_REQUIRED│ │ REJECTED │
   │ └──────────┘     └────────┬────────┘ └──────────┘
   │                           │
   └───────────────────────────┘ (Surveyor resumes field work)
```

#### Valid Transition Matrix
| Source State | Destination State | Permitted Roles | Trigger Event |
|---|---|---|---|
| `ASSIGNED` | `IN_PROGRESS` | `SURVEYOR`, `ADMIN` | Starting or resuming field session |
| `IN_PROGRESS` | `SUBMITTED` | `SURVEYOR`, `ADMIN` | Submitting validated survey session |
| `SUBMITTED` | `APPROVED` | `GOVERNMENT_OFFICER`, `ADMIN` | Officer approves survey submission |
| `SUBMITTED` | `REVISION_REQUIRED` | `GOVERNMENT_OFFICER`, `ADMIN` | Officer requests revisions with notes |
| `SUBMITTED` | `REJECTED` | `GOVERNMENT_OFFICER`, `ADMIN` | Officer rejects submission with notes |
| `REVISION_REQUIRED` | `IN_PROGRESS` | `SURVEYOR`, `ADMIN` | Surveyor resumes session for revisions |

---

### 3.2 Field Survey Session Lifecycle
Survey sessions represent individual on-site site visits and measurement sessions:

```
┌─────────┐    start_session()    ┌────────┐    pause_session()    ┌────────┐
│ PENDING ├──────────────────────►│ ACTIVE ├──────────────────────►│ PAUSED │
└─────────┘                       └───┬────┘                       └───┬────┘
                                      │                                │
                                      │ end_session()                  │ resume
                                      ▼                                │
                                ┌───────────┐                          │
                                │ COMPLETED │◄─────────────────────────┘
                                └───────────┘
```

1. **Session Initialization**:
   - Captures device client information (User Agent, OS, app version).
   - Records starting battery percentage to monitor field device health.
   - Automatically shifts the parent `SurveyAssignment` status to `IN_PROGRESS`.
2. **Real-time Spatial Tracking**:
   - Geolocation stream via HTML5 Geolocation API (`navigator.geolocation.watchPosition`).
   - Tracks current latitude, longitude, altitude, heading, speed, and horizontal accuracy.
   - Visualizes live surveyor position dot and accuracy halo on 2D GIS canvas against official parcel/building boundaries.
3. **Session Closure**:
   - Records ending battery level and pending offline synchronization items.
   - Transitions session to `COMPLETED`.

---

### 3.3 Observation Capture & GNSS Quality Classification
Field observations represent empirical ground truth measurements:

- **Observation Types**:
  - `HEIGHT_MEASUREMENT`: Parapet / apex altitude, vertical clearance, floor count.
  - `FOOTPRINT_CORNER`: Ground boundary corner coordinate verification.
  - `BOUNDARY_POINT`: Parcel perimeter verification point.
  - `FACADE_OBSERVATION`: Structural inspection, cladding, physical condition.
  - `USE_VERIFICATION`: Land use and building utilization ground truth.
  - `ENCROACHMENT_FLAG`: Real-world boundary transgression or unauthorized setback violation.
- **GNSS Quality Tiers**:
  - **Tier 1 - High Precision (RTK Fixed)**: Accuracy $< 1.0\text{ m}$. Suitable for legal cadastral boundary monuments.
  - **Tier 2 - Differential (DGPS / SBAS)**: Accuracy $1.0\text{ m} - 3.0\text{ m}$. Acceptable for general building corners and heights.
  - **Tier 3 - Standalone GNSS**: Accuracy $3.0\text{ m} - 10.0\text{ m}$. Permitted with validation warning; flagged for review.
  - **Tier 4 - Coarse / Unacceptable**: Accuracy $> 10.0\text{ m}$. Blocked by pre-submission checklist until re-measured.

---

### 3.4 Evidence Hashing & Cryptographic Chain of Custody
To eliminate tampering and ensure legal admissibility in cadastral adjudication:

1. **Client-Side SHA-256 Hashing**:
   - Prior to uploading any photo or document, the browser/mobile client digests the raw file bytes using Web Cryptography API (`window.crypto.subtle.digest('SHA-256', buffer)`).
   - Generates a 64-character lowercase hexadecimal hash.
2. **Server-Side Verification**:
   - The FastAPI backend receives the multipart upload stream and calculates the SHA-256 hash independently.
   - If the client-provided hash does not match the server-calculated hash, the upload is rejected immediately (`400 BAD_REQUEST: Integrity check failed`).
3. **Immutable Storage**:
   - Evidence files are written to secure local object storage in `uploads/evidence/{session_id}/{filename}`.
   - Stored with MIME type validation, file size limit (25MB), timestamp, and geographic coordinates of where the photo was taken.

---

### 3.5 Cadastral Validation & Pre-Submission Engine
Before submitting field data, the deterministic validation engine executes:

1. **Completeness Verification**:
   - Validates that minimum required observations (e.g. height, footprint corners) and evidence photos exist.
2. **Quality Audit**:
   - Evaluates horizontal accuracy of all observations. Warns if any accuracy exceeds 3.0m.
3. **Discrepancy Analysis**:
   - Compares field measured height ($H_{\text{measured}}$) against official building height ($H_{\text{official}}$).
   - Generates discrepancy alert if $|H_{\text{measured}} - H_{\text{official}}| / H_{\text{official}} > 5\%$.
   - Compares field measured floors against official recorded floor count.
   - Compares ground boundary coordinates against parcel polygon vertices to detect encroaching setbacks.
4. **Frozen Snapshot Submission**:
   - Upon surveyor confirmation, the system creates a frozen, immutable `SurveySubmission` entity.
   - Serializes all current session observations, evidence references, and validation outcomes into a JSON snapshot.
   - Assigns a sequential submission version number ($V_1, V_2, \dots$) allowing complete audit trail across revision cycles.

---

## 4. Offline Synchronization Protocol & Conflict Resolution Strategy

### 4.1 Client-Side Offline Storage (IndexedDB)
When surveyors operate in field areas lacking cellular connectivity:
- The PWA leverages IndexedDB (`geovertex_offline_db`) with object stores:
  - `assignments`: Cached assignment cards and parcel context geometries.
  - `sessions`: Active and cached field sessions.
  - `observations`: Local observations recorded while offline.
  - `evidence_meta`: Metadata for offline-captured evidence photos.
  - `sync_queue`: Ordered queue of pending write operations.

### 4.2 Batch Sync Protocol (`/api/v1/sync/batch`)
Once internet connectivity is restored:
1. The client groups pending mutations into a single `SyncOperationBatchRequest`.
2. Each operation carries a client-generated UUID `operation_id`, entity type, and ISO-8601 client timestamp.
3. The server processes operations in a single database transaction:
   - **Idempotency Check**: The server checks `sync_operations` table for existing `operation_id`. Duplicate operations are reported as `APPLIED` without re-execution.
   - **Entity Resolution**: Client-generated entity IDs are respected and persisted into the main database models.
   - **Session Status Verification**: If the target session has already been submitted or completed, the mutation is flagged with a non-destructive conflict warning.
4. The server returns a `SyncOperationBatchResponse` detailing per-operation success, failure, or conflict status.
5. The client purges successfully acknowledged items from its local IndexedDB `sync_queue`.

---

## 5. Government Cadastral Review & Adjudication Lifecycle

### 5.1 Review Queue & Domain Inspection
Government Cadastral Officers access `/admin/survey-review` to inspect pending submissions:
- **Side-by-Side Comparative Inspector**:
  - Official cadastral records (height, floors, building type, land use, area) displayed alongside surveyor field observations.
  - Highlighted severity tags (`WARNING`, `INFO`, `CRITICAL`) for measured discrepancies.
- **Photo Evidence Gallery**:
  - High-resolution photo inspector with zoom, SHA-256 cryptographic verification status, and geolocation coordinates.
- **Session Audit Summary**:
  - Field surveyor identity, device info, battery consumption, session start/end timestamps.

### 5.2 Adjudication Actions & Cadastral Separation
- **Approval (`APPROVED`)**:
  - Officer enters optional sign-off remarks.
  - Submission status transitions to `APPROVED`.
  - Assignment status transitions to `APPROVED`.
  - **Cadastral Separation Principle**: Approving a survey records it as an official legal evidence milestone. In accordance with Phase 5 boundaries, survey approval does **not** directly overwrite official building or parcel geometries in PostGIS (official cadastre mutation remains subject to formal amendment workflows in subsequent phases).
- **Revision Request (`REVISION_REQUIRED`)**:
  - Officer provides mandatory feedback notes detailing required re-measurements.
  - Submission status transitions to `REVISION_REQUIRED`.
  - Assignment reverts to `REVISION_REQUIRED`, allowing the surveyor to resume the field session, add observations, and re-submit a new version ($V_{n+1}$).
- **Rejection (`REJECTED`)**:
  - Officer provides mandatory rejection justification (e.g. incorrect parcel targeted).
  - Submission and assignment transition to `REJECTED`.

