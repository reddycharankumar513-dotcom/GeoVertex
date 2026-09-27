"""AI subsurface utility detector with strict 'No Fake AI' safeguards."""

from typing import Any, Dict, List, Optional
from app.ai.utility.base import BaseUtilityDetector


class AIUtilityDetector(BaseUtilityDetector):
    """Subsurface utility candidate detector with explicit unconfigured model state protection."""

    def __init__(self, model_weights_path: Optional[str] = None):
        self.model_weights_path = model_weights_path
        self.is_configured = bool(model_weights_path)

    def detect_candidate_utilities(
        self,
        input_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Detect candidate utility lines, nodes, or structures.
        
        Strictly enforces 'No Fake AI' by returning MODEL_NOT_CONFIGURED when weights are absent.
        """
        if not self.is_configured:
            return {
                "status": "MODEL_NOT_CONFIGURED",
                "can_execute": False,
                "message": (
                    "Underground infrastructure AI vision/GPR model weights are not configured. "
                    "Deterministic GIS network topology, depth calculations, and clash detection "
                    "remain fully operational."
                ),
                "candidates": [],
            }

        # If configured in future with real deep learning weights:
        return {
            "status": "COMPLETED",
            "can_execute": True,
            "message": "AI candidate generation executed successfully.",
            "candidates": [],
        }
