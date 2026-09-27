from app.ai.models.building_baseline import DevelopmentBaselineBuildingExtractor
from app.ai.models.floor_baseline import UnconfiguredFloorExtractor
from app.ai.registry.model_registry import model_registry

# Register standard models into global registry
model_registry.register_model_class(
    model_id="building-segmentation-v1",
    model_class=DevelopmentBaselineBuildingExtractor,
    metadata={
        "name": "Building Baseline Extractor",
        "model_type": "BUILDING_EXTRACTION",
        "framework": "BASELINE_HEURISTIC",
        "version": "1.0.0",
        "status": "ACTIVE",
    },
)

model_registry.register_model_class(
    model_id="floor-extraction-v1",
    model_class=UnconfiguredFloorExtractor,
    metadata={
        "name": "Floor Extraction Neural Model",
        "model_type": "FLOOR_EXTRACTION",
        "framework": "UNCONFIGURED",
        "version": "1.0.0",
        "status": "UNCONFIGURED",
    },
)

__all__ = [
    "DevelopmentBaselineBuildingExtractor",
    "UnconfiguredFloorExtractor",
]
