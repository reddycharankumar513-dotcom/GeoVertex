# GEOVERTEX: AI PIPELINE SPECIFICATION
## Machine Learning Architecture, Model Interfaces & Inference Lifecycle

Version: 2.0  
Status: Authoritative Architecture Specification  
Associated Documents: [MASTER_PRD.md](MASTER_PRD.md), [ARCHITECTURE.md](ARCHITECTURE.md), [API_CONTRACT.md](API_CONTRACT.md)

---

## 1. Guiding Principles & Ethical Cadastral Safeguards

1. **Decision-Support Exclusivity**: AI does not legally establish boundaries or assign final property rights. All AI predictions serve strictly as structured evidence with associated confidence metrics.
2. **Pluggable & Replaceable Models**: The system interface is decoupled from specific deep learning weights. The architecture specifies standard abstract interfaces (`BaseBuildingExtractor`, `BaseFloorExtractor`, `load`, `preprocess`, `predict`, `postprocess`, `evaluate_confidence`).
3. **Strict Truthfulness & Fail-Safe Model Loading**: If model weights or configurations are unavailable, the system strictly returns `MODEL_NOT_CONFIGURED` or `MODEL_WEIGHTS_UNAVAILABLE`. Under no circumstances are mock floor predictions fabricated.
4. **Reproducibility & Provenance**: Every inference run is stored in PostgreSQL with complete model metadata (model family, version, git commit, input dataset hash, inference duration, confidence distribution).
5. **Human-in-the-Loop Review Gate**: All AI outputs remain in `PENDING_REVIEW` state until an authorized officer (`ADMIN` or `GOVERNMENT_OFFICER`) explicitly approves or modifies them. Official cadastral records (`buildings`, `floors`) are **NEVER** mutated automatically.

---

## 2. Common Model Interfaces (`backend/app/ai/base.py`)

All model implementations adhere to standard abstract base classes:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.ai.schemas.ai_schemas import (
    ModelPredictRequest,
    BuildingPredictionResult,
    FloorPredictionResult,
)

class BaseBuildingExtractor(ABC):
    @abstractmethod
    def load(self, model_path: str | None = None) -> None:
        """Initialize weights and hardware device context (CUDA/MPS/CPU)."""
        pass

    @abstractmethod
    def preprocess(self, request: ModelPredictRequest) -> Dict[str, Any]:
        """Normalize imagery, resample resolution, extract AOI context."""
        pass

    @abstractmethod
    def predict(self, preprocessed_data: Dict[str, Any]) -> List[BuildingPredictionResult]:
        """Perform forward inference and produce candidate building footprints."""
        pass

    @abstractmethod
    def evaluate_confidence(self, prediction: BuildingPredictionResult) -> float:
        """Compute statistical or composite confidence rating."""
        pass

class BaseFloorExtractor(ABC):
    @abstractmethod
    def load(self, model_path: str | None = None) -> None:
        """Initialize weights and hardware device context."""
        pass

    @abstractmethod
    def predict(self, preprocessed_data: Dict[str, Any]) -> List[FloorPredictionResult]:
        """Perform forward inference or raise ModelNotConfiguredError."""
        pass
```

### Structured Error Hierarchy
- `ModelNotConfiguredError`: Model has no registered architecture or checkpoint.
- `ModelWeightsUnavailableError`: Model architecture registered but weights file is missing or corrupted.
- `ModelIntegrityError`: SHA-256 checksum mismatch on weights checkpoint.
- `InferenceTimeoutError`: Inference execution exceeded SLA limit.
- `InvalidInferenceInputError`: Input imagery or survey context invalid or unparsable.

---

## 3. Implemented Subsystems (Phase 6)

### 3.1 Subsystem A: Building Footprint Extraction
- **Model Key**: `building-segmentation-v1`
- **Implementation**: `DevelopmentBaselineBuildingExtractor` (`backend/app/ai/models/building_baseline.py`)
- **Status**: `MODEL CONFIGURED: YES` (Development Baseline using field survey observations and buffered parcel boundary AOI context).
- **Pipeline Stages**:
  1. **Preprocessing**: Input evidence normalization, EXIF GPS & timestamp extraction, image resizing, saving non-destructive derived artifacts to `uploads/derived/`.
  2. **Inference**: Predicts candidate footprint polygon bounded by AOI envelope.
  3. **Postprocessing**: Shapely `make_valid` repair, Douglas-Peucker simplification (`tolerance=0.00002`), minimum area threshold filtering ($\ge 10.0\text{ m}^2$).
  4. **Validation**: Deterministic PostGIS/Shapely topological verification (`ST_IsValid`, `ST_IsEmpty`, coordinate boundary checks, parcel containment).
  5. **Comparative Analysis**: Cadastral intersection-over-union (IoU), area discrepancy ($\text{m}^2$), Hausdorff boundary discrepancy (m), and composite confidence scoring.

### 3.2 Subsystem B: Floor & Elevation Detection
- **Model Key**: `floor-elevation-v1`
- **Implementation**: `UnconfiguredFloorExtractor` (`backend/app/ai/models/floor_baseline.py`)
- **Status**: `MODEL CONFIGURED: NO` (`MODEL_NOT_CONFIGURED`)
- **Behavior**:
  - Strictly raises `ModelNotConfiguredError("MODEL_NOT_CONFIGURED: Model weights or point cloud architecture are unconfigured.")`.
  - Dispatched jobs transition to `FAILED` with explicit error code `MODEL_NOT_CONFIGURED`.
  - Frontend prominently alerts users with `MODEL_NOT_CONFIGURED` banner and disables floor candidate submission.

---

## 4. Multi-Factor Confidence Framework

Confidence is deterministically calculated using a 3-factor weighted model:

$$\text{Confidence} = 0.50 \cdot C_{\text{model}} + 0.30 \cdot C_{\text{geometry}} + 0.20 \cdot C_{\text{source}}$$

- **Model Confidence ($C_{\text{model}}$)**: Raw softmax or ensemble score from the extractor ($0.0 - 1.0$).
- **Geometry Quality ($C_{\text{geometry}}$)**:
  - Penalty for invalid geometry (0.0).
  - Penalty for vertex count ($<4 \implies 0.4$, $\ge 4 \implies 1.0$).
  - Penalty for extreme elongation or sliver polygons ($\text{compactness} = \frac{4\pi \cdot \text{Area}}{\text{Perimeter}^2}$).
- **Source Quality ($C_{\text{source}}$)**:
  - GPS RTK Fixed: $1.0$
  - GPS DGPS: $0.85$
  - Handheld GNSS: $0.65$
  - Uncalibrated / Manual: $0.40$

---

## 5. Controlled Cadastral Update Workflow

Candidates are completely isolated from authoritative records until explicitly adjudicated:

```
[Survey Evidence / Imagery]
           │
           ▼
[AI Processing Job] ──(Inference & Validation)──► [BuildingExtractionResult] (PENDING_REVIEW)
                                                              │
                                       ┌──────────────────────┴──────────────────────┐
                                       ▼                                             ▼
                               [Review: REJECT]                             [Review: APPROVE / MODIFY]
                                       │                                             │
                            (Result marked REJECTED)                       (Result marked APPROVED)
                            (Audit Log recorded)                                     │
                                                                                     ▼
                                                                     [Controlled Cadastral Mutation]
                                                                     - BuildingFootprint created/updated
                                                                     - Building3DRepresentation generated
                                                                     - Transactional Audit Log emitted
```

---

## 6. Verification and Testing

Execute the complete test suite:

```bash
# AI Pipeline backend tests
pytest tests/backend/test_ai_pipeline.py -v

# Full backend test suite
pytest tests/backend/ -v

# Frontend test suite
cd frontend && npm test

# Model evaluation CLI runner
python -m app.ai.evaluation.evaluate_building_model --limit 10
```
