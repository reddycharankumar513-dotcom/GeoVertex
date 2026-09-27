from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.gis.validation.tolerances import ValidationToleranceConfig, default_tolerances


@dataclass
class IssueDraft:
    """In-memory draft of a validation finding before persistence."""
    rule_id: str
    rule_version: str
    issue_code: str
    category: str
    severity: str
    entity_type: str
    entity_id: str
    message: str
    technical_explanation: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    geometry_wkt: Optional[str] = None
    measured_value: Optional[str] = None
    expected_value: Optional[str] = None
    tolerance: Optional[str] = None
    metadata_json: Dict[str, Any] = field(default_factory=dict)
    repair_candidate_wkt: Optional[str] = None
    repair_method: Optional[str] = None


@dataclass
class ValidationContext:
    """Execution context and data loaded for validation."""
    target_type: str
    target_id: Optional[str]
    tolerances: ValidationToleranceConfig = field(default_factory=lambda: default_tolerances)
    parameters: Dict[str, Any] = field(default_factory=dict)

    # Ingested entities and data layers
    parcels: List[Any] = field(default_factory=list)
    buildings: List[Any] = field(default_factory=list)
    floors: List[Any] = field(default_factory=list)
    units: List[Any] = field(default_factory=list)
    jurisdictions: List[Any] = field(default_factory=list)
    ai_building_candidates: List[Any] = field(default_factory=list)
    ai_floor_candidates: List[Any] = field(default_factory=list)
    survey_submissions: List[Any] = field(default_factory=list)
    survey_observations: List[Any] = field(default_factory=list)
    property_documents: List[Any] = field(default_factory=list)
    document_fields: List[Any] = field(default_factory=list)
    utility_assets: List[Any] = field(default_factory=list)
    utility_segments: List[Any] = field(default_factory=list)

    # Extra ad-hoc payloads (e.g. for validating geometry payload directly)
    raw_geometries: Dict[str, Any] = field(default_factory=dict)


class ValidationRule(ABC):
    """Abstract base class for all deterministic cadastral and spatial validation rules."""

    rule_id: str
    name: str
    description: str
    category: str
    severity: str
    rule_version: str = "1.0.0"

    @abstractmethod
    def applies_to(self, target_type: str) -> bool:
        """Determines if this rule evaluates the given validation scope."""
        pass

    @abstractmethod
    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        """Executes deterministic evaluation against context and returns any discovered issues."""
        pass

    def explain(self) -> Dict[str, Any]:
        """Provides technical documentation of the rule mechanics."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "severity": self.severity,
            "rule_version": self.rule_version,
        }
