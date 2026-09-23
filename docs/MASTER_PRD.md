# GEOVERTEX
## 3D Cadastral Intelligence & Vertical Property Mapping Platform

Version: 1.0
Status: Master Product Specification
Project Type: Real-World Implementation

---

# 1. PRODUCT OVERVIEW

GeoVertex is a 3D cadastral intelligence platform designed to extend conventional 2D land and property mapping into a structured 3D representation.

The platform integrates:

- GIS parcel data
- GNSS/GPS data
- Drone imagery
- LiDAR / point clouds
- Satellite imagery
- Building plans
- BIM/IFC data
- Property documents
- Survey data

The system represents:

- Land parcels
- Buildings
- Floors
- Individual units
- Underground infrastructure
- Property documents
- Historical versions
- Spatial relationships

GeoVertex is not merely a 3D visualization system.

It is a complete workflow:

REAL-WORLD PROPERTY
        ↓
DATA COLLECTION
        ↓
DATA INGESTION
        ↓
GIS / AI PROCESSING
        ↓
3D DIGITAL TWIN
        ↓
PARCEL / BUILDING / FLOOR / UNIT
        ↓
TOPOLOGY VALIDATION
        ↓
DOCUMENT-SPATIAL ANALYSIS
        ↓
CHANGE DETECTION
        ↓
TECHNICAL 3D PROPERTY IDENTIFIER
        ↓
SURVEYOR REVIEW
        ↓
OFFICER REVIEW
        ↓
VERSIONED CADASTRAL RECORD
        ↓
CITIZEN / SURVEYOR / GOVERNMENT APPLICATIONS

IMPORTANT:

GeoVertex must not claim that it independently determines legal ownership or issues legally recognized government ULPINs.

The initial implementation generates a technical/proposed 3D property identifier.

Authoritative cadastral decisions remain subject to applicable government standards, source records and authorized officials.

---

# 2. PROBLEM STATEMENT

Conventional 2D cadastral systems primarily represent property as a surface polygon.

This creates limitations when dealing with:

- Multi-storey buildings
- Apartment units
- Floor-wise property
- Shared spaces
- Underground structures
- Underground utilities
- Elevated structures
- Complex vertical boundaries
- Construction changes

Example:

                    FLOOR 3
                ┌─────────────┐
                │ UNIT 301    │
                ├─────────────┤
                    FLOOR 2
                ┌─────────────┐
                │ UNIT 201    │
                ├─────────────┤
                    FLOOR 1
                ┌─────────────┐
                │ UNIT 101    │
                ├─────────────┤
                    GROUND
                │ COMMERCIAL  │
────────────────┴─────────────┴──────────────
                    PARCEL
─────────────────────────────────────────────
              UNDERGROUND ASSETS

A 2D parcel polygon cannot adequately represent these vertical relationships.

---

# 3. PRODUCT VISION

Create a trusted 3D digital representation of real-world property that connects:

Spatial Geometry
+
Property Information
+
Documents
+
Infrastructure
+
Historical Changes
+
Verification Workflow

A user should be able to understand:

1. Where is the property?
2. What parcel contains it?
3. What buildings exist?
4. How many floors exist?
5. What units exist?
6. What infrastructure exists underground?
7. Which documents are associated?
8. What changed over time?
9. What inconsistencies exist?
10. What requires human verification?

---

# 4. PRODUCT GOALS

1. Create structured 3D property representations.
2. Support floor-wise property mapping.
3. Support unit-wise property mapping.
4. Generate technical 3D property identifiers.
5. Integrate GIS and survey data.
6. Integrate drone and LiDAR data.
7. Detect building and floor structures using AI.
8. Detect changes between survey versions.
9. Validate spatial topology.
10. Compare property documents with spatial data.
11. Map underground infrastructure.
12. Provide surveyor workflows.
13. Provide government review workflows.
14. Provide citizen-facing property workflows.
15. Maintain complete version history and audit trails.

---

# 5. NON-GOALS

The initial product will NOT:

- Replace government land registries.
- Legally determine ownership.
- Automatically resolve legal disputes.
- Automatically approve property ownership.
- Issue legally recognized ULPIN without authorized integration.
- Process nationwide data in the first release.
- Assume nationwide LiDAR availability.
- Remove human verification from authoritative workflows.

---

# 6. TARGET USERS

## 6.1 Citizen

Capabilities:

- Search permitted property information.
- View 2D property map.
- View 3D property.
- Submit documents.
- Report discrepancies.
- Track requests.

## 6.2 Surveyor

Capabilities:

- Create surveys.
- Capture GNSS coordinates.
- Upload imagery.
- Upload point clouds.
- Capture photographs.
- Review AI results.
- Correct geometry.
- Validate topology.
- Submit surveys.

## 6.3 Government Officer

Capabilities:

- Review survey submissions.
- Inspect 2D and 3D data.
- Review documents.
- Review AI results.
- Review topology issues.
- Review detected changes.
- Approve.
- Reject.
- Request revision.

## 6.4 Administrator

Capabilities:

- Manage users.
- Manage roles.
- Manage spatial layers.
- Manage models.
- Manage system configuration.
- Monitor jobs.
- View audit logs.

## 6.5 Urban Planner

Capabilities:

- View 3D infrastructure.
- Analyze buildings.
- Analyze underground utilities.
- Inspect spatial relationships.

---

# 7. PROPERTY HIERARCHY

GeoVertex uses the following logical hierarchy:

JURISDICTION
      ↓
PARCEL
      ↓
BUILDING
      ↓
FLOOR
      ↓
UNIT

Additional relationships:

PARCEL
  ├── BUILDINGS
  ├── UTILITIES
  ├── SURVEYS
  ├── DOCUMENTS
  └── VERSIONS

---

# 8. PROPERTY MANAGEMENT

Each property shall contain:

- Property ID
- Parcel ID
- Survey Number
- Technical 3D ID
- Geometry
- Area
- Jurisdiction
- Land Use
- Status
- Verification status
- Current version
- Source
- Created timestamp
- Updated timestamp

---

# 9. 2D GIS

The 2D map shall support:

- Parcel visualization
- Building footprints
- Roads
- Utilities
- Search
- Layer controls
- Spatial selection
- Property inspection
- Coordinate display
- Area measurement
- Distance measurement

The system must preserve coordinate reference system metadata.

It must not assume every dataset is WGS84.

---

# 10. 3D DIGITAL TWIN

Use a 3D GIS engine such as CesiumJS.

The digital twin shall support:

- Terrain
- Parcel
- Building
- Floors
- Units
- Roads
- Utilities
- Underground assets

Users shall be able to:

- Rotate
- Pan
- Zoom
- Select
- Isolate
- Hide/show layers
- Measure
- Inspect properties
- Compare versions

---

# 11. FLOOR MAPPING

A building shall be represented as:

BUILDING
 ├── GROUND
 ├── FLOOR 1
 ├── FLOOR 2
 └── FLOOR 3

Each floor may contain:

- Floor number
- Geometry
- Height
- Area
- Confidence
- Units
- Verification status

---

# 12. UNIT MAPPING

Units shall be spatial objects.

Example:

BUILDING
 ├── FLOOR 1
 │     ├── UNIT 101
 │     └── UNIT 102
 ├── FLOOR 2
 │     ├── UNIT 201
 │     └── UNIT 202
 └── FLOOR 3
       ├── UNIT 301
       └── UNIT 302

Unit fields:

- Unit ID
- Floor ID
- Unit number
- Geometry
- Area
- Status
- Documents
- Verification status

---

# 13. AI BUILDING EXTRACTION

Inputs:

- Drone imagery
- Satellite imagery
- LiDAR

Pipeline:

INPUT
 ↓
PREPROCESSING
 ↓
AI MODEL
 ↓
BUILDING DETECTION
 ↓
GEOMETRY EXTRACTION
 ↓
CONFIDENCE
 ↓
SURVEYOR REVIEW

Candidate technologies:

- U-Net
- Mask R-CNN
- Segmentation models
- Point-cloud segmentation

The model must be replaceable.

Do not hard-code the system around one model.

---

# 14. FLOOR DETECTION

Inputs:

- LiDAR
- Point clouds
- Building geometry
- Floor plans
- BIM/IFC

Output:

- Floor number
- Minimum height
- Maximum height
- Geometry
- Confidence

Surveyor must be able to correct AI output.

---

# 15. TECHNICAL 3D PROPERTY IDENTIFIER

The system shall create technical identifiers.

Example:

GV-P001
GV-P001-B01
GV-P001-B01-F02
GV-P001-B01-F02-U05

The identifier must be:

- Unique
- Collision-safe
- Parent-child aware
- Version-aware
- Configurable

Do not hard-code the identifier format.

---

# 16. TOPOLOGY VALIDATION

Validate:

- Invalid polygons
- Self-intersections
- Parcel overlaps
- Parcel gaps
- Building outside parcel
- Building boundary crossing
- Floor overlap
- Unit overlap
- Utility conflicts
- Duplicate geometries

Output:

VALID

or

REVIEW REQUIRED

with:

- Issue type
- Severity
- Geometry
- Explanation
- Suggested action

---

# 17. AI CHANGE DETECTION

Compare:

HISTORICAL SURVEY
+
CURRENT SURVEY

Detect:

- New floors
- Building extensions
- New structures
- Demolition
- Significant geometry changes
- Possible boundary changes

Output:

Change type
Confidence
Affected geometry
Old version
New version
Review status

---

# 18. DOCUMENT INTELLIGENCE

Supported documents:

- PDF
- JPG
- PNG

Pipeline:

UPLOAD
 ↓
VALIDATION
 ↓
OCR
 ↓
TEXT EXTRACTION
 ↓
FIELD EXTRACTION
 ↓
STRUCTURED DATA
 ↓
SPATIAL COMPARISON
 ↓
REVIEW

Possible fields:

- Survey number
- Property number
- Area
- Floor count
- Unit number
- Address
- Building number
- Date

---

# 19. DOCUMENT-SPATIAL VERIFICATION

Example:

DOCUMENT:

Area = 2400 sq.ft
Floors = G+3

GIS:

Area = 2387 sq.ft
Floors = G+3

Result:

AREA MISMATCH
Difference = 13 sq.ft
Status = REVIEW REQUIRED

This is an inconsistency alert, not a legal determination.

---

# 20. UNDERGROUND INFRASTRUCTURE

Supported layers:

- Water
- Sewer
- Electricity
- Gas
- Telecom
- Drainage
- Other authorized infrastructure

Attributes:

- Asset ID
- Type
- Geometry
- Depth
- Diameter
- Authority
- Status
- Source
- Installation date

---

# 21. SURVEYOR WORKFLOW

DRAFT
 ↓
CREATE SURVEY
 ↓
SELECT PROPERTY
 ↓
UPLOAD DATA
 ↓
PROCESSING
 ↓
AI RESULT
 ↓
SURVEYOR REVIEW
 ↓
GEOMETRY CORRECTION
 ↓
TOPOLOGY VALIDATION
 ↓
SUBMIT
 ↓
OFFICER REVIEW

Support offline field capture in a later phase.

---

# 22. CITIZEN WORKFLOW

SEARCH PROPERTY
 ↓
VIEW PERMITTED INFORMATION
 ↓
VIEW 3D PROPERTY
 ↓
SUBMIT DOCUMENT
 ↓
REPORT DISCREPANCY
 ↓
TRACK REQUEST

Citizens cannot directly modify authoritative spatial records.

---

# 23. GOVERNMENT WORKFLOW

REVIEW QUEUE
 ↓
SELECT PROPERTY
 ↓
2D INSPECTION
 ↓
3D INSPECTION
 ↓
DOCUMENT REVIEW
 ↓
AI REVIEW
 ↓
TOPOLOGY REVIEW
 ↓
CHANGE HISTORY
 ↓
APPROVE / REJECT / REVISION

Every decision must create an audit event.

---

# 24. AUDIT AND VERSIONING

Important records must never be silently overwritten.

Version example:

V1
 ↓
V2
 ↓
V3

Audit information:

- User
- Timestamp
- Entity
- Action
- Old value
- New value
- Reason
- Source
- Version

---

# 25. FUNCTIONAL REQUIREMENTS

FR-01 Authentication
FR-02 Role-based access
FR-03 Property creation
FR-04 Parcel management
FR-05 GIS ingestion
FR-06 2D GIS
FR-07 3D visualization
FR-08 Building management
FR-09 Floor management
FR-10 Unit management
FR-11 Survey management
FR-12 AI processing
FR-13 Manual geometry correction
FR-14 Topology validation
FR-15 Document upload
FR-16 Document extraction
FR-17 Document-spatial comparison
FR-18 Change detection
FR-19 Underground infrastructure
FR-20 Technical 3D ID generation
FR-21 Review workflow
FR-22 Approval workflow
FR-23 Audit logging
FR-24 Version management
FR-25 Notifications
FR-26 Search
FR-27 Import/export
FR-28 Dashboard analytics

---

# 26. NON-FUNCTIONAL REQUIREMENTS

Performance:
- Property search target ≤2 seconds under pilot load.
- Normal API target ≤500 ms where practical.
- Heavy processing must be asynchronous.

Scalability:
- Pilot ward → city → district → state.

Security:
- HTTPS
- RBAC
- Input validation
- Secure file handling
- Audit logging
- Secret management

Reliability:
- Database backups
- Job retry
- Versioning
- Transaction integrity

Privacy:
- Role-specific data access.

---

# 27. DATABASE REQUIREMENTS

Use:

PostgreSQL
+
PostGIS

Core tables:

users
roles
permissions
properties
parcels
buildings
floors
units
utilities
surveys
survey_assets
documents
document_extractions
ai_jobs
ai_predictions
change_detections
validation_results
reviews
approvals
notifications
audit_logs
property_versions

Spatial columns must use PostGIS.

Create GIST spatial indexes.

---

# 28. API REQUIREMENTS

Base:

/api/v1

Authentication:

POST /auth/login
POST /auth/refresh

Properties:

GET /properties
POST /properties
GET /properties/{id}
PUT /properties/{id}

GIS:

GET /properties/{id}/geometry
GET /properties/{id}/3d

Buildings:

GET /buildings/{id}
GET /buildings/{id}/floors

Survey:

POST /surveys
POST /surveys/{id}/upload
GET /surveys/{id}

AI:

POST /ai/building-extraction
POST /ai/floor-detection
POST /ai/change-detection

Documents:

POST /documents/upload
POST /documents/verify

Validation:

POST /validation/topology

Review:

POST /reviews/{id}/approve
POST /reviews/{id}/reject

Audit:

GET /audit/{entity_id}

Dashboard:

GET /dashboard/statistics

---

# 29. BACKGROUND PROCESSING

Heavy processing must use workers.

API
 ↓
JOB CREATED
 ↓
REDIS QUEUE
 ↓
WORKER
 ↓
PROCESS
 ↓
STORE RESULT
 ↓
UPDATE JOB
 ↓
NOTIFY USER

Job states:

QUEUED
PROCESSING
COMPLETED
FAILED
CANCELLED

---

# 30. FILE STORAGE

Development:

Local storage / MinIO.

Production:

S3-compatible object storage.

Large files such as:

- LiDAR
- Drone imagery
- Orthophotos
- Documents

must not be stored directly inside normal relational columns.

Store metadata in PostgreSQL.

---

# 31. FRONTEND REQUIREMENTS

Main navigation:

Dashboard
Properties
Parcels
2D Map
3D Map
Surveys
AI Processing
Documents
Changes
Utilities
Review Queue
Audit
Administration

Property page:

Overview
2D Map
3D Twin
Buildings
Floors
Units
Documents
Utilities
AI Analysis
Changes
Validation
Review
Audit

---

# 32. NOTIFICATION SYSTEM

Notifications:

- AI completed
- AI failed
- Survey submitted
- Review assigned
- Revision required
- Property approved
- Property rejected
- Change detected
- Document mismatch
- Topology conflict

---

# 33. IMPORT / EXPORT

Import:

- GeoJSON
- CSV
- KML/KMZ
- Shapefile
- GeoTIFF
- LAS/LAZ

Export:

- GeoJSON
- CSV
- PDF reports
- Supported 3D formats

---

# 34. TESTING

Required:

- Unit tests
- API tests
- Database tests
- GIS tests
- Authentication tests
- RBAC tests
- AI pipeline tests
- Document tests
- Change detection tests
- Frontend tests
- End-to-end tests

Critical workflow:

LOGIN
→ CREATE PARCEL
→ CREATE BUILDING
→ CREATE FLOOR
→ CREATE UNIT
→ GENERATE ID
→ SURVEY
→ AI
→ VALIDATION
→ REVIEW
→ APPROVAL
→ AUDIT

---

# 35. SUCCESS CRITERIA

The MVP is successful when:

✓ User authentication works.
✓ RBAC works.
✓ A parcel can be created.
✓ Parcel appears in 2D GIS.
✓ Building can be attached to parcel.
✓ Building appears in 3D.
✓ Floors can be created.
✓ Units can be created.
✓ Technical ID can be generated.
✓ Survey can be created.
✓ Survey data can be uploaded.
✓ AI pipeline can be executed.
✓ AI output can be reviewed.
✓ Geometry can be corrected.
✓ Topology can be validated.
✓ Documents can be uploaded.
✓ Document fields can be extracted.
✓ Changes can be detected.
✓ Officer can approve/reject.
✓ Audit history is maintained.
✓ The complete workflow works without manual database editing.

---

# 36. MVP PHASE

Phase 1:

- Authentication
- RBAC
- Database
- Property
- Parcel
- 2D GIS
- Basic APIs
- Docker
- Testing

Phase 2:

- Building
- Floor
- Unit
- 3D Digital Twin

Phase 3:

- Survey workflow
- File ingestion
- Background processing

Phase 4:

- AI building extraction
- Floor detection

Phase 5:

- Topology validation
- Change detection

Phase 6:

- Document intelligence

Phase 7:

- Underground infrastructure

Phase 8:

- Citizen and government workflows

Phase 9:

- Audit/versioning/notifications

Phase 10:

- Production hardening

---

# 37. PRODUCT PRINCIPLE

GeoVertex is a decision-support and spatial intelligence platform.

AI provides:

Detection
Analysis
Comparison
Confidence
Alerts

Humans provide:

Verification
Review
Approval
Authoritative decision

Therefore:

AI
 ↓
EVIDENCE
 ↓
CONFIDENCE
 ↓
SURVEYOR
 ↓
OFFICER
 ↓
VERIFIED RECORD
