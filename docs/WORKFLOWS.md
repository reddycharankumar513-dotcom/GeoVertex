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
