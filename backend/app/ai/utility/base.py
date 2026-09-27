"""Base abstractions for underground utility detection models."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseUtilityDetector(ABC):
    """Abstract base class for AI/ML subsurface utility detection models."""

    @abstractmethod
    def detect_candidate_utilities(
        self,
        input_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Detect candidate utility lines, nodes, or structures from sensor, drawing, or remote sensing data.
        
        Outputs MUST be classified as CANDIDATE and strictly require human cadastral review.
        """
        pass
