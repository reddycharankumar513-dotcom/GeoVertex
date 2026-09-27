from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseChangeDetector(ABC):
    """Abstract base class for change detection algorithms."""

    def __init__(self, model_id: str = "DEFAULT_DETECTOR", version: str = "1.0.0"):
        self.model_id = model_id
        self.version = version

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the required model weights or algorithms are fully configured."""
        pass

    @abstractmethod
    def detect_changes(
        self,
        baseline_data: Dict[str, Any],
        comparison_data: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Executes change detection returning a list of raw change candidate records."""
        pass


class BaseImageChangeDetector(ABC):
    """Abstract base class for remote sensing raster and imagery change detection."""

    @abstractmethod
    def register_images(
        self,
        baseline_image_ref: str,
        comparison_image_ref: str,
        crs: str = "EPSG:4326",
    ) -> Dict[str, Any]:
        """Validates alignment, CRS, and spatial extent between two temporal raster observations."""
        pass

    @abstractmethod
    def compute_change_mask(
        self,
        baseline_image_ref: str,
        comparison_image_ref: str,
        alignment_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generates difference mask and polygonized change areas."""
        pass
