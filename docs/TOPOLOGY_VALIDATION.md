# GeoVertex: Phase 7 Advanced Topology Validation & Spatial Consistency

## 1. Overview & System Purpose

Phase 7 establishes the **Deterministic Topology Validation & Spatial Quality Framework** for GeoVertex. It provides multi-layer geometric consistency checks, 3D vertical stack integrity verification, AI candidate topology checks, field survey cross-dataset reconciliation, and human review lifecycle workflows.

### Fundamental System Invariant
> **Topology findings are technical and data-quality observations. They do NOT constitute automated legal determinations or ownership adjudications.**
> All legal parcel rights, ownership disputes, and cadastral boundary modifications remain strictly reserved for human cadastral officers and surveyors through authorized legal administrative processes.

---

## 2. Validation Architecture

```
                  ┌───────────────────────────────────────────────┐
                  │          FastAPI Validation REST API          │
                  │              (/api/v1/validation/*)           │
                  └───────────────────────┬───────────────────────┘
                                          │
                  ┌───────────────────────▼───────────────────────┐
                  │               ValidationService               │
                  │   - Job Dispatching & RBAC Enforcement        │
                  │   - Human Review Lifecycle Management         │
                  └───────────────┬───────────────────────────────┘
                                  │
                  ┌───────────────▼───────────────────────────────┐
                  │                ValidationWorker               │
                  │  Asynchronous Stage Progression:              │
                  │  QUEUED -> PREPARING_DATA -> RUNNING_RULES -> │
                  │  GENERATING_ISSUES -> SUMMARIZING -> COMPLETED│
                  └───────────────┬───────────────────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         │                                                 │
┌────────▼─────────────────────┐         ┌─────────────────▼──────────────┐
│       ValidationEngine       │         │      ValidationRuleRegistry    │
│  - Tolerances Application    │         │  - 30+ Versioned Rules         │
│  - IssueDraft Generation     │         │  - Target Type Indexing        │
│  - Summary Calculation       │         │  - Category Filter Support     │
└──────────────────────────────┘         └────────────────────────────────┘
```

---

## 3. Comprehensive Rule Catalogue

| Rule ID | Version | Issue Code | Category | Default Severity | Target Type | Description |
|---|---|---|---|---|---|---|
| `GEO_001` | 1.0.0 | `GEOM_MISSING` | GEOMETRY | CRITICAL | SYSTEM | Geometry attribute is NULL or undefined |
| `GEO_002` | 1.0.0 | `GEOM_EMPTY` | GEOMETRY | CRITICAL | SYSTEM | Geometry contains zero coordinate vertices |
| `GEO_003` | 1.0.0 | `GEOM_INVALID` | GEOMETRY | ERROR | SYSTEM | Shapely / OGC topological validity failure (self-intersection, ring collapse) with repair suggestion |
| `GEO_004` | 1.0.0 | `GEOM_WRONG_TYPE` | GEOMETRY | ERROR | SYSTEM | Geometry type does not match entity contract (e.g. MultiLineString for Parcel) |
| `GEO_005` | 1.0.0 | `GEOM_INVALID_RING` | GEOMETRY | ERROR | SYSTEM | Exterior or interior ring is unclosed or self-touching |
| `GEO_006` | 1.0.0 | `GEOM_SELF_INTERSECTION` | GEOMETRY | ERROR | SYSTEM | Boundary self-intersects at one or more non-vertex coordinates |
| `GEO_007` | 1.0.0 | `GEOM_INVALID_CRS` | CRS | ERROR | SYSTEM | Coordinate values exceed EPSG:4326 WGS84 geographic bounds |
| `PAR_001` | 1.0.0 | `PARCEL_OVERLAP` | PARCEL | CRITICAL | PARCEL | Parcel shares non-zero overlapping polygon area with another parcel |
| `PAR_002` | 1.0.0 | `PARCEL_DUPLICATE` | PARCEL | CRITICAL | PARCEL | Identical or near-identical duplicate parcel footprint (Hausdorff distance < 0.05m) |
| `PAR_003` | 1.0.0 | `PARCEL_OUTSIDE_JURISDICTION` | PARCEL | ERROR | PARCEL | Parcel centroid or boundary extends outside assigned administrative jurisdiction |
| `PAR_004` | 1.0.0 | `PARCEL_MISSING_PROPERTY` | PARCEL | WARNING | PARCEL | Parcel lacks mandatory property identification code or attributes |
| `BLD_001` | 1.0.0 | `BUILDING_OUTSIDE_PARCEL` | BUILDING | ERROR | BUILDING | Building footprint is completely outside its associated cadastral parcel |
| `BLD_002` | 1.0.0 | `BUILDING_PARTIAL_OUTSIDE_PARCEL` | BUILDING | WARNING | BUILDING | Building extends beyond parcel boundary exceeding overhang tolerance (> 2%) |
| `BLD_003` | 1.0.0 | `BUILDING_OVERLAP` | BUILDING | ERROR | BUILDING | Distinct buildings share overlapping ground footprint on the same parcel |
| `BLD_004` | 1.0.0 | `BUILDING_DUPLICATE` | BUILDING | ERROR | BUILDING | Exact duplicate building footprint registered under identical coordinates |
| `BLD_005` | 1.0.0 | `BUILDING_INVALID_GEOMETRY` | BUILDING | ERROR | BUILDING | Building 2D footprint fails OGC validity checks |
| `BLD_006` | 1.0.0 | `BUILDING_AREA_MISMATCH` | BUILDING | WARNING | BUILDING | Calculated polygon area deviates from metadata reported area (> 5%) |
| `FLR_001` | 1.0.0 | `FLOOR_INVALID_ELEVATION` | FLOOR | ERROR | FLOOR | Elevation `z_min` is equal to or greater than `z_max` |
| `FLR_002` | 1.0.0 | `FLOOR_VERTICAL_OVERLAP` | VERTICAL | ERROR | FLOOR | Consecutive floors vertically intersect by more than vertical tolerance (0.05m) |
| `FLR_003` | 1.0.0 | `FLOOR_VERTICAL_GAP` | VERTICAL | WARNING | FLOOR | Unexplained vertical air gap between contiguous habitable stories (> 0.20m) |
| `FLR_004` | 1.0.0 | `FLOOR_DUPLICATE` | FLOOR | ERROR | FLOOR | Duplicate floor story number within same building |
| `FLR_005` | 1.0.0 | `FLOOR_OUTSIDE_BUILDING` | FLOOR | ERROR | FLOOR | Floor boundary extends outside building master exterior envelope |
| `FLR_006` | 1.0.0 | `FLOOR_AREA_MISMATCH` | FLOOR | WARNING | FLOOR | Floor area differs significantly from building floor plate footprint |
| `UNT_001` | 1.0.0 | `UNIT_OUTSIDE_FLOOR` | UNIT | ERROR | UNIT | Property unit boundary extends outside designated floor boundary |
| `UNT_002` | 1.0.0 | `UNIT_OUTSIDE_BUILDING` | UNIT | ERROR | UNIT | Unit boundary exceeds building envelope |
| `UNT_003` | 1.0.0 | `UNIT_OVERLAP` | UNIT | ERROR | UNIT | Two units on the same floor share overlapping horizontal space (> 0.05m²) |
| `UNT_004` | 1.0.0 | `UNIT_DUPLICATE` | UNIT | ERROR | UNIT | Duplicate unit number registered on the same floor |
| `UNT_005` | 1.0.0 | `UNIT_INVALID_GEOMETRY` | UNIT | ERROR | UNIT | Unit polygon geometry fails OGC validity checks |
| `UNT_006` | 1.0.0 | `UNIT_AREA_MISMATCH` | UNIT | WARNING | UNIT | Unit geometric area deviates from declared deed area |
| `VER_001` | 1.0.0 | `VERTICAL_STACK_CONSISTENCY` | VERTICAL | WARNING | BUILDING | Cumulative floor elevations exceed estimated building height |
| `AIC_001` | 1.0.0 | `AI_CANDIDATE_INVALID_GEOMETRY`| AI | ERROR | AI_RESULT | AI candidate footprint has self-intersections or degenerate rings |
| `AIC_002` | 1.0.0 | `AI_CANDIDATE_DUPLICATE` | AI | WARNING | AI_RESULT | Candidate duplicates an existing confirmed building with high spatial match |
| `AIC_003` | 1.0.0 | `AI_CANDIDATE_LOW_SPATIAL_MATCH`| AI | INFO | AI_RESULT | Candidate IoU relative to official cadastral footprint is below 0.30 |
| `AIC_004` | 1.0.0 | `AI_CANDIDATE_PARCEL_CONFLICT` | AI | WARNING | AI_RESULT | AI candidate straddles parcel boundary lines with significant overhang |
| `SRV_001` | 1.0.0 | `SURVEY_GEOMETRY_INVALID` | SURVEY | ERROR | SURVEY_SUBMISSION | Survey observation geometry is invalid |
| `SRV_002` | 1.0.0 | `SURVEY_OUTSIDE_AOI` | SURVEY | ERROR | SURVEY_SUBMISSION | Survey points fall outside designated task area of interest |
| `SRV_003` | 1.0.0 | `SURVEY_HEIGHT_MISMATCH` | SURVEY | WARNING | SURVEY_SUBMISSION | Field laser/GPS measured height deviates from cadastre record by > 1.0m |
| `SRV_004` | 1.0.0 | `SURVEY_FOOTPRINT_MISMATCH` | SURVEY | WARNING | SURVEY_SUBMISSION | Field survey polygon deviates from cadastral record (Hausdorff distance > 0.5m) |
| `CRS_001` | 1.0.0 | `CRS_MISSING` | CRS | ERROR | SYSTEM | Dataset or entity lacks defined Spatial Reference System (SRID) |
| `CRS_002` | 1.0.0 | `CRS_MISMATCH` | CRS | ERROR | SYSTEM | Entity coordinates cannot be reconciled with administrative jurisdiction CRS |
| `XDS_001` | 1.0.0 | `CROSS_DATASET_DISCREPANCY` | CROSS_DATASET | WARNING | SYSTEM | Significant spatial discrepancy detected between survey and official record |

---

## 4. Central Tolerance Configuration

Tolerances are centrally governed in `backend/app/gis/validation/tolerances.py` and can be fine-tuned or overridden per validation run:

- `overlap_area_m2 = 0.05`: Zero-tolerance threshold for parcel and unit overlaps (allowing slight numerical roundoff).
- `containment_ratio_min = 0.98`: 98% of building footprint must fall within parcel boundary.
- `duplicate_distance_m = 0.05`: Points closer than 5cm considered identical vertices.
- `vertical_gap_m = 0.20`: Maximum allowed vertical gap between consecutive stories before flagging warning.
- `vertical_overlap_m = 0.05`: Maximum allowed vertical overlap between consecutive stories.
- `area_discrepancy_pct = 5.0`: Maximum allowable area discrepancy percentage between geometric calculation and declared metadata.
- `survey_height_tolerance_m = 1.0`: Maximum permissible delta between field measurement and digital twin height.
- `hausdorff_discrepancy_m = 0.50`: Hausdorff boundary distance limit between field survey and cadastre.

---

## 5. Human Review Lifecycle

Every validation issue follows a deterministic state machine:

```
          ┌────────────────────────────────────────────────────────┐
          │                         OPEN                           │
          │    (Default state upon discovery by ValidationEngine)  │
          └───────────────────────────┬────────────────────────────┘
                                      │
                         [Acknowledge Action]
                         (Surveyor / Officer / Admin)
                                      │
                                      ▼
          ┌────────────────────────────────────────────────────────┐
          │                     ACKNOWLEDGED                       │
          │  (Field surveyor or officer is actively investigating) │
          └───────────────┬────────────────────────┬───────────────┘
                          │                        │
               [Resolve Action]             [Waive Action]
             (Officer / Admin only)       (Officer / Admin only)
             (Mandatory note)             (Mandatory legal reason)
                          │                        │
                          ▼                        ▼
          ┌───────────────────────────┐ ┌───────────────────────────┐
          │         RESOLVED          │ │          WAIVED           │
          │ (Geometry or data fixed;  │ │ (Formal technical waiver  │
          │ verified in future runs)  │ │ granted under legal code) │
          └───────────────────────────┘ └───────────────────────────┘
```

### RBAC Matrix for Validation Workflows

| Capability | CITIZEN | SURVEYOR | URBAN_PLANNER | GOVERNMENT_OFFICER | ADMIN |
|---|:---:|:---:|:---:|:---:|:---:|
| View Validation Runs | Yes | Yes | Yes | Yes | Yes |
| View Validation Issues | Yes | Yes | Yes | Yes | Yes |
| View Entity Quality Summary | Yes | Yes | Yes | Yes | Yes |
| Trigger Validation Run | No | Yes | Yes | Yes | Yes |
| Acknowledge Issue | No | Yes | No | Yes | Yes |
| Resolve Issue (with note) | No | No | No | Yes | Yes |
| Waive Issue (with reason) | No | No | No | Yes | Yes |

---

## 6. Frontend Visual Inspection & Vector Canvas

The GeoVertex frontend features a dedicated **Topology Validation Dashboard** (`/validation`) containing:
1. **Quality Metric Cards**: Quick visibility of Open, Critical, Error, Warning, and Waived issue counts.
2. **Issue Filter Grid**: Fast multi-attribute filtering by Severity (`CRITICAL`, `ERROR`, `WARNING`, `INFO`), Status (`OPEN`, `ACKNOWLEDGED`, `RESOLVED`, `WAIVED`), Category, and full-text keyword search.
3. **Interactive Vector Canvas**: High-precision SVG visualization displaying:
   - Primary entity polygon boundary (emerald / cyan).
   - Related entity boundary (e.g. parcel boundary or neighboring unit).
   - Defect geometry highlight (red dashed hatch / cross-hatch) pinpointing the exact spatial conflict zone.
   - Layer toggles, zoom, and coordinate readouts.
4. **Issue Review Modal**: Comprehensive metadata display with measured vs expected values, tolerance thresholds, technical explanation, and role-gated action buttons (Acknowledge, Resolve with note, Waive with reason).
5. **Run Execution Modal**: Allows surveyors and officers to trigger ad-hoc validation on specific parcels, buildings, or entire jurisdictions with custom tolerance overrides.
6. **Rule Catalogue Viewer**: Detailed reference of all active topological rules with severity ratings and technical details.
