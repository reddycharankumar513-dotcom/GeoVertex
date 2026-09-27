# GeoVertex Phase 11: Citizen Portal, Government Workflow & Public-Service Integration

## 1. Overview & Architecture

GeoVertex Phase 11 introduces a high-integrity, multi-stakeholder operational platform connecting citizens, registered surveyors, government cadastral officers, and municipal administrators into a unified, audited public-service lifecycle.

```
+-----------------------------------------------------------------------------------+
|                                STAKEHOLDERS                                       |
+-----------------------------------------------------------------------------------+
|  [Citizen Portal]      [Field Surveyors]    [Government Officers]  [Administrators]|
|  - Verified Properties - Survey Execution   - Case Workspace       - Jurisdictions |
|  - Service Requests    - Benchmark Pins     - GIS Context (2D/3D)  - Service Types |
|  - Real-time Timeline  - Monument Measures  - Cross-Phase Intel    - Role Access   |
|  - Public Messaging    - Direct Uploads     - Review Decisions     - Audit Logs    |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                                CORE ENGINES                                       |
+-----------------------------------------------------------------------------------+
|  1. WorkflowStateMachine: Deterministic role-based transition validator           |
|  2. SLAEngine: Working-day deadline and compliance status calculator             |
|  3. NotificationService: In-App notification center & SMTP configuration guard     |
|  4. Object-Level ABAC: Verifies citizen ownership link before allowing filing     |
|  5. Controlled Update Engine: Audited property mutation with legal citations       |
+-----------------------------------------------------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                     CROSS-PHASE CASE WORKSPACE AGGREGATION                        |
+-----------------------------------------------------------------------------------+
|  Phase 2: Cadastral Parcels & Properties                                          |
|  Phase 3/4: 3D Digital Twins, Building Footprints & Vertical Units                |
|  Phase 5: Field Survey Projects & Assignments                                     |
|  Phase 7: Spatial Topology Validation Rules & Violations                          |
|  Phase 8: Verified Legal Deeds & OCR Structured Field Extraction                  |
|  Phase 9: Temporal Satellite / Drone Change Detection Candidates                  |
|  Phase 10: Subsurface Underground Infrastructure & Utility Clashes                |
+-----------------------------------------------------------------------------------+
```

---

## 2. Object-Level Authorization (ABAC & RBAC)

### 2.1 Citizen Property Linking (`CitizenPropertyLink`)
Citizens cannot file ungrounded requests against arbitrary properties. A service request targeting a property requires an active, verified `CitizenPropertyLink`:
- **Authorization Types**: `OWNER`, `AUTHORIZED_REPRESENTATIVE`, `OCCUPANT`, `TENANT`.
- **Status States**: `ACTIVE`, `VERIFIED`, `PENDING_VERIFICATION`, `REVOKED`.
- **Enforcement**: Submitting a request without a verified link results in `403 Forbidden` (`Citizen is not authorized to submit requests for this property`).

### 2.2 Officer Jurisdiction Scoping
- Officers are assigned to specific administrative jurisdictions (`jurisdiction_id`).
- When querying service requests, officer queries are automatically filtered to their assigned jurisdiction unless escalated to municipal administrators.

### 2.3 Internal Officer Notes Secrecy
- The system supports two messaging types in case files:
  1. `PUBLIC_MESSAGE`: Visible to both citizen requester and reviewing officers.
  2. `INTERNAL_NOTE`: Marked with `is_internal = True`. Strictly protected on the server side: citizens querying `/workflows/service-requests/{id}/messages` or case timelines never receive internal notes.

---

## 3. Deterministic Workflow State Machine

The workflow state machine (`WorkflowStateMachine`) enforces legal transitions according to actor role:

| State | Allowed Target States | Permitted Roles | Notes / Preconditions |
|---|---|---|---|
| `DRAFT` | `SUBMITTED`, `CANCELLED` | Citizen, Officer, Admin | Citizen initiates or discards draft |
| `SUBMITTED` | `UNDER_REVIEW`, `CANCELLED` | Officer, Admin (Citizen can cancel) | Officer acknowledges and claims case |
| `UNDER_REVIEW` | `MORE_INFO_REQUESTED` | Officer, Admin | Requires explanation of missing info |
| `UNDER_REVIEW` | `SURVEY_COMMISSIONED` | Officer, Admin | Triggers Phase 5 field survey project |
| `UNDER_REVIEW` | `FIELD_VERIFIED` | Officer, Admin | Post-survey verification check |
| `UNDER_REVIEW` | `APPROVED` | Officer, Admin | Requires all validation checks pass |
| `UNDER_REVIEW` | `REJECTED` | Officer, Admin | Mandatory legal rejection reason |
| `MORE_INFO_REQUESTED` | `UNDER_REVIEW`, `CANCELLED` | Citizen (Resubmit), Citizen (Cancel) | Citizen provides clarification |
| `SURVEY_COMMISSIONED` | `SURVEY_COMPLETED`, `UNDER_REVIEW` | Surveyor, Officer | Field survey results submitted |
| `SURVEY_COMPLETED` | `FIELD_VERIFIED`, `UNDER_REVIEW` | Officer, Admin | Officer inspects survey boundary data |
| `FIELD_VERIFIED` | `APPROVED`, `REJECTED`, `UNDER_REVIEW` | Officer, Admin | Final review before registry mutation |
| `APPROVED` | `COMPLETED` | System, Officer, Admin | Registry updated; mutation finalized |
| `REJECTED` | *(Terminal)* | None | Cannot be reopened |
| `CANCELLED` | *(Terminal)* | None | Cannot be reopened |
| `COMPLETED` | *(Terminal)* | None | Official record permanent record |

---

## 4. SLA & Performance Engine

`SLAEngine` provides real-time, working-day SLA tracking without synthetic mocks:
- **Response SLA**: Configurable per service type (e.g. 24 hours for mutations, 12 hours for boundary disputes).
- **Completion SLA**: Target calendar/working hours for case resolution (e.g. 120 hours / 5 business days).
- **Compliance Status**:
  - `ON_TRACK`: Remaining hours > 24 hours.
  - `DUE_SOON`: Remaining hours <= 24 hours and >= 0.
  - `OVERDUE`: Remaining hours < 0.
- **Escalation Rules**: Cases exceeding SLA or flagged by officers can be escalated (`/escalate`) with priority increase (`URGENT`) and re-assignment.

---

## 5. Notification System & Integrity Rules

- **In-App Notifications**: Stored in `notifications` table, tracked with read timestamps, delivered via dropdown bell icon in navbar.
- **No Fake Email Delivery**: If SMTP credentials are not configured in system settings, email delivery is recorded as `EMAIL_NOT_CONFIGURED`. The platform never falsely claims that an email has been sent.

---

## 6. Controlled Official Record Updates

Automated algorithms and AI modules never modify legal cadastral ownership directly:
- Updates to official property records (address, locality, property type, status, geometry) require a government officer invoking `/execute-update`.
- **Mandatory Requirements**:
  1. `updates`: Key-value map of approved changes.
  2. `audit_reason`: Factual and legal justification.
  3. `source_reference`: Legal citation (Registered Partition Deed, Gazette Notification, Court Order).
- Every update generates an indelible entry in `audit_events`.
