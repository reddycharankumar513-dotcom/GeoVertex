# GeoVertex: Phase 10 Underground Infrastructure & Subsurface Utility Intelligence

## 1. Overview & System Purpose

Phase 10 establishes the **Underground Infrastructure & Subsurface Utility Intelligence Subsystem** for the GeoVertex platform. It provides the technological foundation to model, analyze, and govern subsurface linear networks, junction nodes, 3D vertical structures (vaults, manholes, duct banks), and multi-utility corridors in full alignment with surface cadastral parcels and 3D building twins.

The subsystem answers core geospatial and engineering questions:
1. **What is underground?** (Pipelines, conduits, cables, duct banks, manholes, vaults, chambers across Water, Sewer, Stormwater, Gas, Electricity, Telecom, Fiber, Drainage, and Other domains).
2. **Where is it vertically located?** (Explicit depth and vertical reference model: $z_{\text{ground}} - z_{\text{centerline}} = \text{depth}$, avoiding fabrication of unmeasured elevations).
3. **What is its positional reliability?** (ASCE 38 Quality Levels QL-A, QL-B, QL-C, and QL-D).
4. **Where are spatial conflicts and hazards?** (Deterministic 3D spatial clash detection calculating 3D clearance and enforcing configurable municipal separation rules).
5. **How does it interact with surface property?** (Technical parcel crossing metric lengths and 3D building basement / foundation proximity).
6. **What evidence supports the subsurface records?** (Cross-phase linkages to Phase 5 field surveys, Phase 8 as-built engineering drawings, and Phase 9 temporal snapshots).
7. **Who verifies and updates utility records?** (Mandatory human-in-the-loop review workflow for candidate features and audit-logged controlled updates).

---

## 2. Fundamental System Invariants & Governance Guarantees

> [!IMPORTANT]
> **Technical Spatial Geometry Only; No Automatic Legal Easements.**
> The system strictly adheres to the following non-negotiable governance principles:
> 1. **Cadastral Spatial Relationship Restriction**: Intersections between subsurface utilities and surface parcels are reported strictly as technical geometry (e.g., crossing length in meters, boundary crossing points). The system shall **NEVER** automatically declare legal easements, rights-of-way, or cadastral servitudes without official administrative/legal instrument recording.
> 2. **Explicit Vertical Reference & No Fake Depths**: If depth or vertical elevation is unmeasured, the system records `depth = null` and classifies it as `UNKNOWN_DEPTH`. It never fabricates synthetic depths or interpolates elevations without verified survey benchmarks.
> 3. **Separation Rule Governance**: When evaluating separation between two utilities where no municipal separation rule is configured, the system explicitly reports `rule_code = 'SEPARATION_RULE_NOT_CONFIGURED'` rather than silently passing or inventing rules. Direct physical intersections are flagged as `CRITICAL` regardless of rule configuration.
> 4. **Candidate Review Workflow**: AI-detected or unverified as-built features enter the system as `CANDIDATE` and require formal review (`VERIFIED`, `REJECTED`, `REVISION_REQUIRED`) by authorized cadastral officers or admins.
> 5. **Controlled Update Audit Trail**: Any manual alteration of verified utility geometry, depth, or network connectivity requires an explicit reason, source reference, and produces an immutable audit log record.

---

## 3. Strict "No Fake AI" Safeguards

In accordance with GeoVertex standards:
- **Missing Model Weights**: When computer vision or ground-penetrating radar (GPR) AI detector weights are unconfigured or absent, `AIUtilityDetector` explicitly returns `MODEL_NOT_CONFIGURED` with zero candidate fabrications.
- **Deterministic Independence**: All 3D clash calculations, network graph topology evaluations, depth/elevation sanity verifications, and parcel spatial intersection metrics execute via deterministic computational geometry and remain 100% operational regardless of AI model availability.

---

## 4. Subsystem Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Subsurface Networks & Assets Data Model                                  │
│    - UtilityNetwork (domain, owner, operator, CRS, vertical datum)          │
│    - UtilityAsset (pipes, cables, ducts, vaults, manholes, QL-A to QL-D)    │
│    - UtilitySegment (linear 3D edges, slope %, flow direction)              │
│    - UtilityNode (point junctions, valves, fittings)                        │
│    - UtilityStructure (3D vaults, chambers, duct banks)                    │
│    - UtilityCorridor (multi-utility subterranean rights-of-way)             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 2. Deterministic GIS Subsurface Engines                                     │
│    - DepthElevationCalculator (z_ground - z_centerline, slope %)            │
│    - UtilitySpatialRelationshipAnalyzer (metric parcel crossings, basements)│
│    - UtilityNetworkTopologyEngine (junction graph, dangling edges, BFS)     │
│    - UtilityClashDetector (3D bounding boxes, clearances, separation rules) │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 3. Phase 7 Spatial Topology Validation Integration                          │
│    - UTL-001: Missing Subsurface Depth                                      │
│    - UTL-002: Subsurface Depth Below Allowable Threshold                    │
│    - UTL-003: Subsurface Inverted Elevation (centerline > ground)           │
│    - UTL-004: Subsurface Dangling Segment Endpoint                          │
│    - UTL-005: 3D Subsurface Utility Clearance Violation                     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 4. Cross-Phase Integrations & Governance                                    │
│    - Phase 5: Field Survey observation linkages                             │
│    - Phase 8: Document intelligence as-built plan extractions               │
│    - Phase 9: Temporal intelligence snapshot captures                       │
│    - Human-in-the-Loop: Official review, controlled updates, audit trails   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Depth and Vertical Reference Standards

The vertical model requires consistent reference surfaces:
- **Ground Surface Reference**: $z_{\text{ground}}$ from digital elevation models (DEM) or survey ground shots.
- **Centerline Elevation**: $z_{\text{centerline}}$ (or invert elevation for gravity pipes).
- **Depth Calculation**: $\text{depth} = z_{\text{ground}} - z_{\text{centerline}}$.
- **Elevation Inversion Check**: If $z_{\text{centerline}} > z_{\text{ground}}$, the geometry is flagged as an invalid above-ground anomaly (`UTL-003`).

### Quality Levels (ASCE 38 Standards)
- **QL-A (Precise 3D Exposure)**: Vacuum excavation / test hole physical exposure; sub-centimeter vertical and horizontal precision.
- **QL-B (Geophysical Detection)**: Surface geophysics (GPR, electromagnetic locator); high confidence horizontal, approximate depth.
- **QL-C (Surface Feature Survey)**: Survey of visible appurtenances (valve covers, manholes) with interpolation.
- **QL-D (Record Drawings)**: Historical utility maps, unverified as-builts, schematic records.

---

## 6. 3D Spatial Clash Detection Engine

Clashes are evaluated between pairs of utility assets:
1. **Broad-Phase Spatial Index**: 3D bounding box intersection filter in projected coordinate space.
2. **Narrow-Phase 3D Distance**: Minimum 3D Euclidean clearance between centerline 3D line strings.
3. **Separation Rule Matrix**: Look up active `UtilitySeparationRule` matching `(utility_type_a, utility_type_b)`.
   - If horizontal separation < `required_horizontal_separation_m` or vertical separation < `required_vertical_separation_m`, a `UtilityClash` is emitted with `CRITICAL` or `MAJOR` severity.
   - If no municipal rule exists, report `rule_code = 'SEPARATION_RULE_NOT_CONFIGURED'` and check for physical intersection (< 0.1m clearance).

---

## 7. REST API Endpoints

All endpoints are mounted under `/api/v1/utilities`:

| Method | Endpoint | Description | Access Control |
|---|---|---|---|
| `POST` | `/utilities/networks` | Create a utility network | Admin, Government Officer |
| `GET` | `/utilities/networks` | List utility networks | Authenticated |
| `GET` | `/utilities/networks/{id}` | Get network details | Authenticated |
| `GET` | `/utilities/networks/{id}/topology` | Graph topology analysis | Authenticated |
| `POST` | `/utilities/assets` | Create a utility asset | Admin, Officer, Surveyor |
| `GET` | `/utilities/assets` | Filter and list utility assets | Authenticated |
| `GET` | `/utilities/assets/{id}` | Get comprehensive asset details | Authenticated |
| `POST` | `/utilities/assets/{id}/verify` | Official review (VERIFY/REJECT/REVISION) | Admin, Government Officer |
| `POST` | `/utilities/assets/{id}/controlled-update` | Controlled update with audit trail | Admin, Government Officer |
| `POST` | `/utilities/clashes/detect` | Run 3D clash detection | Admin, Officer, Surveyor, Planner |
| `GET` | `/utilities/clashes` | List detected 3D clashes | Authenticated |
| `POST` | `/utilities/clashes/{id}/review` | Review clash (ACKNOWLEDGE/RESOLVE/WAIVE) | Admin, Government Officer |
| `GET` | `/utilities/map` | Subsurface GeoJSON map layer | Authenticated |
| `GET` | `/utilities/3d` | 3D volumetric subsurface scene | Authenticated |
| `GET` | `/utilities/metrics` | Subsurface intelligence KPI metrics | Authenticated |

---

## 8. Verification & Test Suite Coverage

- **Backend Pytest Tests (`tests/backend/test_underground_infrastructure.py`)**:
  - Test 1: Depth and vertical elevation calculation sanity.
  - Test 2: Inverted elevation detection ($z_{\text{centerline}} > z_{\text{ground}}$).
  - Test 3: Cadastral parcel spatial crossing (geometry only, no legal easements).
  - Test 4: Building basement proximity and clearance detection.
  - Test 5: Network topology graph (dangling endpoints, BFS components).
  - Test 6: 3D clash detection with separation rules & `SEPARATION_RULE_NOT_CONFIGURED` fallback.
  - Test 7: Strict "No Fake AI" (`MODEL_NOT_CONFIGURED` status).
  - Test 8: Phase 7 spatial topology validation rules (`UTL-001` through `UTL-005`).
  - Test 9: End-to-end API lifecycle, controlled updates, review workflow, and RBAC enforcement.
- **Frontend Vitest Tests (`frontend/src/__tests__/underground_infrastructure.test.ts`)**:
  - 8 comprehensive test cases covering RBAC, depth model, quality levels, parcel crossings, basement interactions, separation rules, No Fake AI, and controlled update validation.
