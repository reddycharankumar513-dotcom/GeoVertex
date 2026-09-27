from typing import Any, Dict, Optional
from app.ai.base import (
    BaseFloorExtractor,
    ModelNotConfiguredError,
    ModelWeightsUnavailableError,
)
from app.ai.schemas.ai_schemas import FloorPredictionResult


class UnconfiguredFloorExtractor(BaseFloorExtractor):
    """Floor extraction interface adapter.
    
    In accordance with Section 24 and Section 63 of Phase 6 specifications:
    "If reliable training/model data is unavailable: return MODEL_NOT_CONFIGURED. Do not fabricate floors."
    
    This model raises ModelNotConfiguredError unless pre-trained floor segmentation weights
    are explicitly configured.
    """

    MODEL_ID = "floor-extraction-v1"
    VERSION = "1.0.0"

    def __init__(self):
        self.weights_path: Optional[str] = None
        self.is_configured = False

    def load_model(self, model_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> None:
        if not model_path:
            self.is_configured = False
            return
        self.weights_path = model_path
        self.is_configured = True

    def preprocess(self, raw_input: Any) -> Any:
        if not self.is_configured:
            raise ModelNotConfiguredError(
                "MODEL_NOT_CONFIGURED: No trained floor extraction model is configured. "
                "Cadastral floors must not be fabricated without authoritative model weights."
            )
        return raw_input

    def predict(self, preprocessed_data: Any) -> Any:
        if not self.is_configured:
            raise ModelNotConfiguredError(
                "MODEL_NOT_CONFIGURED: No trained floor extraction model is configured."
            )
        raise ModelNotConfiguredError("MODEL_NOT_CONFIGURED")

    def postprocess(self, raw_prediction: Any, **kwargs: Any) -> FloorPredictionResult:
        if not self.is_configured:
            raise ModelNotConfiguredError("MODEL_NOT_CONFIGURED")
        raise ModelNotConfiguredError("MODEL_NOT_CONFIGURED")

    def validate_output(self, output: FloorPredictionResult) -> bool:
        return False

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "model_id": self.MODEL_ID,
            "version": self.VERSION,
            "framework": "UNCONFIGURED",
            "model_type": "FLOOR_EXTRACTION",
            "status": "UNCONFIGURED" if not self.is_configured else "ACTIVE",
            "weights_configured": self.is_configured,
        }
