from app.gis.validation.base import IssueDraft, ValidationContext, ValidationRule
from app.gis.validation.tolerances import ValidationToleranceConfig, default_tolerances
from app.gis.validation.registry import rule_registry, ValidationRuleRegistry

# Import all concrete rule implementations
from app.gis.validation.geometry_rules import (
    GeomMissingRule,
    GeomEmptyRule,
    GeomInvalidRule,
    GeomWrongTypeRule,
    GeomInvalidRingRule,
    GeomSelfIntersectionRule,
    GeomInvalidCRSRule,
)
from app.gis.validation.parcel_rules import (
    ParcelOverlapRule,
    ParcelDuplicateRule,
    ParcelOutsideJurisdictionRule,
    ParcelMissingPropertyRule,
)
from app.gis.validation.building_rules import (
    BuildingOutsideParcelRule,
    BuildingPartialOutsideParcelRule,
    BuildingOverlapRule,
    BuildingDuplicateRule,
    BuildingInvalidGeometryRule,
    BuildingAreaMismatchRule,
)
from app.gis.validation.floor_rules import (
    FloorInvalidElevationRule,
    FloorVerticalOverlapRule,
    FloorVerticalGapRule,
    FloorDuplicateRule,
    FloorOutsideBuildingRule,
    FloorAreaMismatchRule,
)
from app.gis.validation.unit_rules import (
    UnitOutsideFloorRule,
    UnitOutsideBuildingRule,
    UnitOverlapRule,
    UnitDuplicateRule,
    UnitInvalidGeometryRule,
    UnitAreaMismatchRule,
)
from app.gis.validation.vertical_rules import (
    VerticalStackingRule,
)
from app.gis.validation.candidate_rules import (
    AICandidateInvalidGeometryRule,
    AICandidateDuplicateRule,
    AICandidateLowSpatialMatchRule,
    AICandidateParcelConflictRule,
)
from app.gis.validation.survey_rules import (
    SurveyGeometryInvalidRule,
    SurveyOutsideAOIRule,
    SurveyHeightMismatchRule,
    SurveyFootprintMismatchRule,
)
from app.gis.validation.crs_rules import (
    CRSMissingRule,
    CRSMismatchRule,
)
from app.gis.validation.cross_dataset_rules import (
    CrossDatasetDiscrepancyRule,
)
from app.gis.validation.document_rules import (
    DocumentParcelReferenceMismatchRule,
    DocumentBuildingReferenceMismatchRule,
    DocumentUnitReferenceMismatchRule,
    DocumentAreaMismatchRule,
    DocumentDateInconsistencyRule,
    DocumentDuplicateCandidateRule,
    DocumentNumberMissingRule,
    DocumentParcelReferenceMissingRule,
)
from app.gis.validation.utility_rules import (
    UtilityDepthMissingRule,
    UtilityDepthInvalidRule,
    UtilityElevationInversionRule,
    UtilityDanglingEndpointRule,
)

# Populate the singleton registry with all authoritative validation rules
ALL_RULES = [
    # Geometry
    GeomMissingRule(),
    GeomEmptyRule(),
    GeomInvalidRule(),
    GeomWrongTypeRule(),
    GeomInvalidRingRule(),
    GeomSelfIntersectionRule(),
    GeomInvalidCRSRule(),
    # Parcel
    ParcelOverlapRule(),
    ParcelDuplicateRule(),
    ParcelOutsideJurisdictionRule(),
    ParcelMissingPropertyRule(),
    # Building
    BuildingOutsideParcelRule(),
    BuildingPartialOutsideParcelRule(),
    BuildingOverlapRule(),
    BuildingDuplicateRule(),
    BuildingInvalidGeometryRule(),
    BuildingAreaMismatchRule(),
    # Floor
    FloorInvalidElevationRule(),
    FloorVerticalOverlapRule(),
    FloorVerticalGapRule(),
    FloorDuplicateRule(),
    FloorOutsideBuildingRule(),
    FloorAreaMismatchRule(),
    # Unit
    UnitOutsideFloorRule(),
    UnitOutsideBuildingRule(),
    UnitOverlapRule(),
    UnitDuplicateRule(),
    UnitInvalidGeometryRule(),
    UnitAreaMismatchRule(),
    # Vertical
    VerticalStackingRule(),
    # AI Candidate
    AICandidateInvalidGeometryRule(),
    AICandidateDuplicateRule(),
    AICandidateLowSpatialMatchRule(),
    AICandidateParcelConflictRule(),
    # Survey
    SurveyGeometryInvalidRule(),
    SurveyOutsideAOIRule(),
    SurveyHeightMismatchRule(),
    SurveyFootprintMismatchRule(),
    # CRS
    CRSMissingRule(),
    CRSMismatchRule(),
    # Cross-dataset
    CrossDatasetDiscrepancyRule(),
    # Document Intelligence & Property Verification (Phase 8)
    DocumentParcelReferenceMismatchRule(),
    DocumentBuildingReferenceMismatchRule(),
    DocumentUnitReferenceMismatchRule(),
    DocumentAreaMismatchRule(),
    DocumentDateInconsistencyRule(),
    DocumentDuplicateCandidateRule(),
    DocumentNumberMissingRule(),
    DocumentParcelReferenceMissingRule(),
    # Underground Infrastructure & Subsurface Utility Intelligence (Phase 10)
    UtilityDepthMissingRule(),
    UtilityDepthInvalidRule(),
    UtilityElevationInversionRule(),
    UtilityDanglingEndpointRule(),
]

for r in ALL_RULES:
    rule_registry.register(r)

__all__ = [
    "IssueDraft",
    "ValidationContext",
    "ValidationRule",
    "ValidationToleranceConfig",
    "default_tolerances",
    "rule_registry",
    "ALL_RULES",
]
