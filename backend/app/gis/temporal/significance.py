from typing import Any, Dict, Optional
from app.models.temporal import ChangeSignificance, ChangeType


class SignificanceConfig:
    """Configurable thresholds for classifying change significance."""

    def __init__(
        self,
        minor_area_threshold_sqm: float = 10.0,
        major_area_threshold_sqm: float = 100.0,
        minor_pct_threshold: float = 5.0,
        major_pct_threshold: float = 20.0,
        minor_height_threshold_m: float = 1.0,
        major_height_threshold_m: float = 4.0,
        minor_boundary_disp_m: float = 0.5,
        major_boundary_disp_m: float = 2.0,
    ):
        self.minor_area_threshold_sqm = minor_area_threshold_sqm
        self.major_area_threshold_sqm = major_area_threshold_sqm
        self.minor_pct_threshold = minor_pct_threshold
        self.major_pct_threshold = major_pct_threshold
        self.minor_height_threshold_m = minor_height_threshold_m
        self.major_height_threshold_m = major_height_threshold_m
        self.minor_boundary_disp_m = minor_boundary_disp_m
        self.major_boundary_disp_m = major_boundary_disp_m


class SignificanceEvaluator:
    """Evaluates change significance deterministically based on magnitude metrics and change type."""

    @classmethod
    def evaluate(
        cls,
        change_type: str,
        magnitude: Dict[str, Any],
        config: Optional[SignificanceConfig] = None,
    ) -> ChangeSignificance:
        cfg = config or SignificanceConfig()

        # Structural changes like adding or removing a building or floor are inherently MAJOR
        if change_type in [
            ChangeType.BUILDING_ADDED.value,
            ChangeType.BUILDING_REMOVED.value,
            ChangeType.BUILDING_COUNT_CHANGED.value,
            ChangeType.FLOOR_ADDED.value,
            ChangeType.FLOOR_REMOVED.value,
            ChangeType.FLOOR_COUNT_CHANGED.value,
        ]:
            return ChangeSignificance.MAJOR

        # Check height difference
        height_diff = abs(magnitude.get("height_difference_m", 0.0))
        if height_diff >= cfg.major_height_threshold_m:
            return ChangeSignificance.MAJOR

        # Check area difference and percentage
        area_diff = abs(magnitude.get("area_difference_sqm", 0.0))
        pct_diff = abs(magnitude.get("area_change_percentage", 0.0))
        boundary_disp = abs(magnitude.get("boundary_displacement_m", 0.0))

        if (
            area_diff >= cfg.major_area_threshold_sqm
            or pct_diff >= cfg.major_pct_threshold
            or boundary_disp >= cfg.major_boundary_disp_m
        ):
            return ChangeSignificance.MAJOR

        if (
            area_diff > cfg.minor_area_threshold_sqm
            or pct_diff > cfg.minor_pct_threshold
            or boundary_disp > cfg.minor_boundary_disp_m
            or height_diff > cfg.minor_height_threshold_m
        ):
            return ChangeSignificance.MODERATE

        if area_diff > 0 or boundary_disp > 0 or height_diff > 0:
            return ChangeSignificance.MINOR

        # For attribute changes
        if change_type in [
            ChangeType.PARCEL_ATTRIBUTE_CHANGED.value,
            ChangeType.PROPERTY_ATTRIBUTE_CHANGED.value,
            ChangeType.DOCUMENT_RECORD_CHANGE.value,
        ]:
            return ChangeSignificance.MODERATE

        return ChangeSignificance.MINOR
