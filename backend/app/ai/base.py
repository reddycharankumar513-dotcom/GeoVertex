from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from app.ai.schemas.ai_schemas import BuildingPredictionResult, FloorPredictionResult


# -------------------------------------------------------------
# Structured AI Exceptions (Section 52 & 3)
# -------------------------------------------------------------

class AIException(Exception):
    """Base exception for all AI/ML pipeline failures."""
    error_code: str = "AI_ERROR"

    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        if error_code:
            self.error_code = error_code


class ModelNotConfiguredError(AIException):
    error_code = "MODEL_NOT_CONFIGURED"

    def __init__(self, message: str = "Requested AI model is not configured or registered in system"):
        super().__init__(message, self.error_code)


class ModelWeightsUnavailableError(AIException):
    error_code = "MODEL_WEIGHTS_UNAVAILABLE"

    def __init__(self, message: str = "Model weights file is not available in object storage or local path"):
        super().__init__(message, self.error_code)


class ModelIntegrityError(AIException):
    error_code = "MODEL_INTEGRITY_ERROR"

    def __init__(self, message: str = "Model weights checksum does not match registered cryptographic hash"):
        super().__init__(message, self.error_code)


class InputInvalidError(AIException):
    error_code = "INPUT_INVALID"

    def __init__(self, message: str = "Provided evidence input or geometry is invalid or unreadable"):
        super().__init__(message, self.error_code)


class InferenceFailedError(AIException):
    error_code = "INFERENCE_FAILED"

    def __init__(self, message: str = "Forward model inference failed during execution"):
        super().__init__(message, self.error_code)


class OutputGeometryInvalidError(AIException):
    error_code = "OUTPUT_GEOMETRY_INVALID"

    def __init__(self, message: str = "Model inference output produced topologically invalid or empty geometry"):
        super().__init__(message, self.error_code)


# -------------------------------------------------------------
# Abstract Model Interfaces (Section 8)
# -------------------------------------------------------------

class BaseBuildingExtractor(ABC):
    """Abstract model interface for candidate building footprint extraction."""

    @abstractmethod
    def load_model(self, model_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize weights, device context (CPU/CUDA), and hyperparameters."""
        pass

    @abstractmethod
    def preprocess(self, raw_input: Any) -> Any:
        """Preprocess evidence images, orthomosaics, or bounding context."""
        pass

    @abstractmethod
    def predict(self, preprocessed_data: Any) -> Any:
        """Execute forward inference and return raw segmentation mask/predictions."""
        pass

    @abstractmethod
    def postprocess(self, raw_prediction: Any, **kwargs: Any) -> BuildingPredictionResult:
        """Polygonize, simplify, and format candidate building footprint."""
        pass

    @abstractmethod
    def validate_output(self, output: BuildingPredictionResult) -> bool:
        """Sanity check on predicted geometry before GIS persistence."""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Return model metadata, architecture name, version, and device info."""
        pass


class BaseFloorExtractor(ABC):
    """Abstract model interface for candidate floor stack and elevation extraction."""

    @abstractmethod
    def load_model(self, model_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize weights, device context, and parameters."""
        pass

    @abstractmethod
    def preprocess(self, raw_input: Any) -> Any:
        """Preprocess observations, façade imagery, or elevation data."""
        pass

    @abstractmethod
    def predict(self, preprocessed_data: Any) -> Any:
        """Execute forward floor estimation."""
        pass

    @abstractmethod
    def postprocess(self, raw_prediction: Any, **kwargs: Any) -> FloorPredictionResult:
        """Format candidate floor slices and elevations."""
        pass

    @abstractmethod
    def validate_output(self, output: FloorPredictionResult) -> bool:
        """Verify non-clashing vertical intervals and positive thickness."""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Return model metadata."""
        pass
