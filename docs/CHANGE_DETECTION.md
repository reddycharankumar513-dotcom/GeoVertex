# GeoVertex: Phase 9 AI Change Detection & Temporal Property Intelligence

## 1. Overview & System Purpose

Phase 9 establishes the **AI Change Detection & Temporal Property Intelligence Subsystem** for the GeoVertex platform. It provides the technological foundation to track, analyze, and govern the physical and legal evolution of cadastral parcels, 3D buildings, vertical floors, and property units over time.

The subsystem answers seven core technical questions:
1. **What changed?** (Added footprints, demolished structures, vertical expansions, floor count alterations, area shifts, attribute modifications).
2. **When did it change?** (Temporal interval between baseline and comparison snapshots, observation dates, document effective dates).
3. **Where did it change?** (Exact spatial difference geometries: added polygons, removed polygons, centroid displacement vectors).
4. **What evidence supports the change?** (Multi-source evidence trails linking Phase 5 field surveys, Phase 8 legal deeds and permits, drone imagery, satellite rasters).
5. **How significant is the change?** (Deterministic classification into `MINOR`, `MODERATE`, or `MAJOR` severity based on metric thresholds).
6. **Which datasets disagree?** (Cross-dataset discrepancy resolution between official cadastre, remote sensing observations, and deed descriptions).
7. **What requires human review?** (Candidate review queue surfacing topological warnings, ambiguous entity matches, and significant physical changes).

---

## 2. Fundamental System Invariant & Governance Guarantees

> [!IMPORTANT]
> **AI Detects Candidate Physical Changes; Humans Determine Operational & Legal Significance.**
> The system strictly adheres to the following non-negotiable governance principles:
> 1. The AI change detection subsystem shall **NEVER** automatically declare construction as "illegal" or "unauthorized". It flags physical differences for human adjudication.
> 2. The system shall **NEVER** automatically determine or transfer legal title, revoke property deeds, or reassign ownership based on detected spatial changes.
> 3. AI outputs are classified strictly as **Change Candidates (`ChangeCandidate`)** until authorized cadastral officers review, verify, and confirm them into the official register.
> 4. Automated processes provide evidence, metric magnitudes, and topological consistency checks to empower human decision-makers.

---

## 3. Strict "No Fake AI" Safeguards

In accordance with GeoVertex standards, mock or synthetic AI outputs are strictly forbidden:
- **Missing Model Weights**: When vision/satellite change detection model weights are unconfigured or absent, the system explicitly returns `MODEL_NOT_CONFIGURED` rather than generating simulated change polygons.
- **Missing Evaluation Data**: When benchmark evaluation datasets or ground truth references are unconfigured, model performance evaluators explicitly return `EVALUATION_DATASET_NOT_CONFIGURED`.
- **Deterministic Independence**: Deterministic GIS geometric difference calculation, metric area quantification, and attribute diffing execute independently of AI models and remain 100% operational.

---

## 4. Subsystem Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Temporal Snapshots Engine (PropertySnapshot)                             │
│    - Immutable historical captures of Parcels, Buildings, Floors, Units     │
│    - Versioning & effective intervals: [effective_from, effective_to]       │
│    - Multi-source types: OFFICIAL_RECORD, SURVEY, REMOTE_SENSING, etc.      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 2. Change Detection Pipeline (ChangeDetectionWorker)                        │
│    Stage 1: Job Queued & Initialized (ChangeDetectionRun)                   │
│    Stage 2: Entity & Snapshot Resolution (TemporalEntityMatcher)            │
│    Stage 3: Deterministic Geometry Comparison (DeterministicGeometryComp)   │
│    Stage 4: Attribute & Hierarchy Diffing (AttributeComparator)             │
│    Stage 5: Vision/Image Change Detection (AIChangeDetector / ImageReg)     │
│    Stage 6: Phase 7 Spatial Topology Validation Integration                 │
│    Stage 7: Multi-Source Evidence Enrichment (Phase 5 Surveys, Phase 8 Docs)│
│    Stage 8: Significance Classification & Candidate Generation              │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 3. Cadastral Officer Human-in-the-Loop Review Workspace                     │
│    - Candidate Inspection Modal with metric before/after comparison         │
│    - Phase 7 topological violation indicators (boundary encroachment, etc.) │
│    - Multi-source evidence audit trail view                                 │
│    - Adjudication Actions: CONFIRM, REJECT, DISMISS with mandatory reason   │
│    - Audit Logging: Actor user, timestamp, prior state, terminal state      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Deterministic GIS Temporal Comparators

The GIS temporal engine (`backend/app/gis/temporal/`) computes metric spatial differences by dynamically projecting WGS84 coordinates into local Universal Transverse Mercator (UTM) projections:

1. **Metric Area Delta & Relative Ratio**:
   $$\Delta \text{Area} = \text{Area}_{\text{comp}} - \text{Area}_{\text{base}}$$
   $$\text{Change Ratio (\%)} = \frac{|\Delta \text{Area}|}{\max(\text{Area}_{\text{base}}, 0.001)} \times 100$$
2. **Spatial Overlap & Intersection over Union (IoU)**:
   $$\text{IoU} = \frac{\text{Area}(\text{Base} \cap \text{Comp})}{\text{Area}(\text{Base} \cup \text{Comp})}$$
3. **Centroid & Boundary Hausdorff Displacement**:
   - Geodesic centroid Euclidean displacement in meters.
   - Maximum Hausdorff distance measuring localized boundary divergence.
4. **Symmetric Geometric Differences**:
   - $\text{Added Area} = \text{Comp} \setminus \text{Base}$
   - $\text{Removed Area} = \text{Base} \setminus \text{Comp}$
   - $\text{Symmetric Difference} = (\text{Comp} \setminus \text{Base}) \cup (\text{Base} \setminus \text{Comp})$
5. **Micro-Sliver Pruning**:
   - Numerical projection artifacts and sliver polygons $< 0.05\text{ m}^2$ are pruned to prevent false positive notifications.

---

## 6. Significance Classification Matrix

The `SignificanceEvaluator` assigns an operational severity level to each candidate:

| Severity | Footprint Area Delta ($\Delta A$) | Height Delta ($\Delta H$) | Centroid Displacement ($d$) | Typical Cadastral Context |
|---|---|---|---|---|
| **`MAJOR`** | $\Delta A > 50\text{ m}^2$ | $\Delta H > 4.0\text{ m}$ | $d > 5.0\text{ m}$ | Substantial structural addition, vertical story construction, demolition, major parcel subdivision. |
| **`MODERATE`** | $10\text{ m}^2 < \Delta A \le 50\text{ m}^2$ | $1.5\text{ m} < \Delta H \le 4.0\text{ m}$ | $1.0\text{ m} < d \le 5.0\text{ m}$ | Floor plan expansion, single-story modification, boundary alignment shift. |
| **`MINOR`** | $0.5\text{ m}^2 < \Delta A \le 10\text{ m}^2$ | $0.2\text{ m} < \Delta H \le 1.5\text{ m}$ | $0.2\text{ m} < d \le 1.0\text{ m}$ | Small porch addition, balcony extension, localized boundary re-survey adjustment. |

---

## 7. Multi-Source Evidence & Topology Integration

When a candidate change is generated, it links contextual evidence across previous phases:
- **Phase 5 Field Surveys**: Ground truth measurements, photos, and surveyor observations.
- **Phase 8 Property Documents**: Registered deeds, building permits, completion certificates, and court orders.
- **Phase 7 Topology Engine**: Checks whether the candidate footprint violates setbacks, encroaches beyond parcel boundaries, or causes co-planar overlaps.

---

## 8. Role-Based Access Control (RBAC)

| User Role | View Candidates & Timeline | Dispatch Detection Run | Review & Confirm Changes | Cancel Active Run |
|---|:---:|:---:|:---:|:---:|
| **`ADMIN`** | Yes | Yes | Yes | Yes |
| **`GOVERNMENT_OFFICER`** | Yes | Yes | Yes | Yes |
| **`SURVEYOR`** | Yes | Yes | No | No |
| **`URBAN_PLANNER`** | Yes | Yes | No | No |
| **`CITIZEN`** | Restricted | No | No | No |

---

## 9. Verification & Test Coverage

- **Backend Pytest Suite**: 100 tests passing across all 9 phases (`tests/backend/test_change_detection.py` and regression suite).
- **Frontend Vitest Suite**: 47 unit tests passing across all modules (`frontend/src/__tests__/change_detection.test.ts`).
- **Production Build**: Verified clean TypeScript compilation and Vite packaging (`npm run build` exits 0 with 0 errors).
