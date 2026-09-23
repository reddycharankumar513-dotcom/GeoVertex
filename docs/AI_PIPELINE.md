# GEOVERTEX: AI PIPELINE SPECIFICATION
## Machine Learning Architecture, Model Interfaces & Inference Lifecycle

Version: 1.0  
Status: Authoritative Architecture Specification  
Associated Documents: [MASTER_PRD.md](MASTER_PRD.md), [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 1. Guiding Principles & Ethical Cadastral Safeguards

1. **Decision-Support Exclusivity**: AI does not legally establish boundaries or assign final property rights. All AI predictions serve strictly as structured evidence with associated confidence metrics.
2. **Pluggable & Replaceable Models**: The system interface is decoupled from specific deep learning weights. Architecture specifies standard abstract interfaces (`load`, `preprocess`, `predict`, `postprocess`, `evaluate_confidence`).
3. **Reproducibility & Provenance**: Every inference run is stored in PostgreSQL with complete model metadata (model family, version, git commit, input dataset hash, inference duration, confidence distribution).
4. **Human-in-the-Loop Gate**: All AI outputs must transition through `SURVEYOR_REVIEW` before entering authoritative topological checks.

---

## 2. Common Model Interface (`ai/base.py`)

All future model implementations must implement the standard contract:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel

class PredictionResult(BaseModel):
    model_name: str
    model_version: str
    input_provenance: Dict[str, Any]
    confidence_score: float  # Normalized 0.0 - 1.0
    geometry_geojson: Dict[str, Any]
    metadata: Dict[str, Any]

class BaseSpatialModel(ABC):
    @abstractmethod
    def load(self, model_path: str) -> None:
        """Initialize weights and hardware device context (CUDA/CPU)."""
        pass

    @abstractmethod
    def preprocess(self, raw_input: Any) -> Any:
        """Normalize imagery, resample resolution, or clean point clouds."""
        pass

    @abstractmethod
    def predict(self, preprocessed_data: Any) -> PredictionResult:
        """Perform forward inference and produce vectorized predictions."""
        pass

    @abstractmethod
    def evaluate_confidence(self, prediction: Any) -> float:
        """Compute statistical or ensemble confidence rating."""
        pass
```

---

## 3. The Three AI Subsystems (Roadmap Phases 6 & 9)

### 3.1 Subsystem A: Building Footprint Extraction
- **Input Modalities**: High-resolution drone orthomosaics (GeoTIFF), satellite multispectral imagery, or rasterized LiDAR intensity maps.
- **Candidate Architectures**: ResNet/EfficientNet backboned U-Net, Mask R-CNN, or Segment Anything Model (SAM) fine-tuned on cadastral datasets.
- **Pipeline**:
  1. Tiling orthomosaic into overlapping 512x512 patches with georeferenced bounding boxes.
  2. Semantic segmentation mask prediction (probabilities per pixel).
  3. Contour extraction and polygonization via GDAL/Rasterio.
  4. Douglas-Peucker geometric simplification and orthogonal regularization.
  5. Calculation of overlap intersection-over-union (IoU) confidence.

### 3.2 Subsystem B: Floor & Elevation Detection
- **Input Modalities**: Normalized Point Clouds (LAS/LAZ format), Building Geometry, Digital Surface Models (DSM).
- **Technique**:
  1. Point cloud filtering and ground elevation classification (CANUPO / CSF algorithm).
  2. Bounding volume clipping to approved 2D building footprint.
  3. Vertical Z-histogram binning (kernel density estimation of horizontal planar surfaces).
  4. Identification of floor slab height peaks and ceiling thresholds.
  5. Generation of multi-level `PolygonZ` floor envelopes.

### 3.3 Subsystem C: Bi-Temporal Change Detection
- **Input Modalities**: Multi-temporal survey geometries and imagery ($T_0$ historical survey vs $T_1$ latest field survey).
- **Technique**:
  1. Georeferencing alignment and CRS homogenization.
  2. Topological symmetric difference calculation (`ST_SymDifference`).
  3. Change classification: `NEW_STRUCTURE`, `FLOOR_ADDITION`, `DEMOLITION`, `BOUNDARY_ENCROACHMENT`.
  4. Flagging changes with confidence score into the Officer Inspection Queue.

---

## 4. Asynchronous Worker Architecture

AI workloads are strictly decoupled from synchronous FastAPI request-response cycles:
1. Client dispatches `POST /api/v1/ai/jobs` to API.
2. API validates schema, inserts `ai_jobs` record with status `QUEUED`, and enqueues task ID into Redis.
3. Celery / background worker claims task, fetches input from Object Storage (MinIO / S3), and executes inference.
4. Result geometries, confidence values, and execution logs persist into PostgreSQL.
5. Task status transitions to `COMPLETED` and emits notification event.
