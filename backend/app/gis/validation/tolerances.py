from typing import Any, Dict
from pydantic import BaseModel, Field


class ValidationToleranceConfig(BaseModel):
    """Configurable numerical tolerances for deterministic spatial and vertical validation."""

    # 2D Geometry & Boundary Tolerances
    min_polygon_area_sqm: float = Field(
        default=1.0,
        description="Minimum valid polygon area in square meters below which it is flagged as sliver/degenerate.",
    )
    max_polygon_area_sqm: float = Field(
        default=500000.0,
        description="Maximum valid polygon area in square meters.",
    )
    simplification_tolerance: float = Field(
        default=0.00002,
        description="Douglas-Peucker simplification tolerance in geographic degrees (~2m).",
    )
    boundary_tolerance_m: float = Field(
        default=0.15,
        description="Allowed spatial buffer margin in meters for boundary alignment and vertex snap checks.",
    )
    centroid_tolerance_m: float = Field(
        default=1.0,
        description="Allowed shift in meters between centroids of corresponding footprints.",
    )

    # Overlap & Containment Tolerances
    area_overlap_tolerance_sqm: float = Field(
        default=0.05,
        description="Tolerable intersection area in square meters before flagging as a true cadastral area overlap.",
    )
    outside_parcel_tolerance_ratio: float = Field(
        default=0.02,
        description="Allowed proportion (2%) of a building footprint outside its parent parcel before flagging.",
    )
    unit_outside_floor_tolerance_ratio: float = Field(
        default=0.01,
        description="Allowed proportion (1%) of a unit footprint outside its parent floor footprint.",
    )
    unit_overlap_tolerance_sqm: float = Field(
        default=0.02,
        description="Tolerable area in square meters for co-planar unit overlaps.",
    )

    # Vertical & Elevation Tolerances
    vertical_elevation_tolerance_m: float = Field(
        default=0.05,
        description="Allowed vertical discrepancy in meters between adjacent floor slabs (5cm).",
    )
    min_floor_height_m: float = Field(
        default=1.8,
        description="Minimum permissible clearance height for a habitable or service floor in meters.",
    )
    max_floor_height_m: float = Field(
        default=15.0,
        description="Maximum permissible height for a single floor story in meters.",
    )
    vertical_gap_tolerance_m: float = Field(
        default=0.15,
        description="Maximum permissible vertical gap between consecutive floor slabs in meters.",
    )

    # Cross-Dataset & Comparative Tolerances
    min_congruent_iou: float = Field(
        default=0.85,
        description="Minimum IoU threshold to consider candidate and official footprints congruent.",
    )
    min_acceptable_candidate_iou: float = Field(
        default=0.50,
        description="Minimum IoU threshold for AI candidate to be considered a spatial match.",
    )
    survey_height_tolerance_m: float = Field(
        default=0.50,
        description="Permissible difference in meters between surveyed height and official record.",
    )
    survey_area_diff_pct_tolerance: float = Field(
        default=5.0,
        description="Permissible percentage difference between surveyed area and official footprint area.",
    )
    document_area_diff_pct_tolerance: float = Field(
        default=5.0,
        description="Permissible percentage difference between document declared area and official geometry area.",
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_overrides(cls, overrides: Dict[str, Any] | None = None) -> "ValidationToleranceConfig":
        if not overrides:
            return cls()
        filtered = {k: v for k, v in overrides.items() if k in cls.model_fields and v is not None}
        return cls(**filtered)


# Default global tolerance configuration instance
default_tolerances = ValidationToleranceConfig()
