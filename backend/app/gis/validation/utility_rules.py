"""Utility and underground infrastructure validation rules for GeoVertex Phase 10."""

from typing import Any, Dict, List, Optional
from app.gis.validation.base import IssueDraft, ValidationContext, ValidationRule


class UtilityDepthMissingRule(ValidationRule):
    rule_id = "UTILITY_DEPTH_MISSING"
    name = "Utility Depth Missing"
    description = "Checks that underground infrastructure records have explicit depth of cover recorded."
    category = "UTILITY"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["UTILITY", "UTILITY_ASSET", "UTILITY_SEGMENT", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        utility_assets = getattr(context, "utility_assets", []) or []

        for asset in utility_assets:
            depth = getattr(asset, "depth", None)
            if depth is None:
                asset_ref = getattr(asset, "asset_reference", str(asset.id))
                issues.append(IssueDraft(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    issue_code="UTL-001",
                    category=self.category,
                    severity=self.severity,
                    entity_type="UTILITY_ASSET",
                    entity_id=str(asset.id),
                    message=f"Utility asset '{asset_ref}' has no depth recorded (depth is UNKNOWN).",
                    technical_explanation="Subsurface infrastructure assets must document depth below ground level for excavation safety and clash analysis.",
                    expected_value="> 0.0 m",
                    measured_value="UNKNOWN",
                    metadata_json={
                        "asset_reference": asset_ref,
                        "asset_type": getattr(asset, "asset_type", "PIPE"),
                        "repair_suggestion": "Attach field survey depth observation or engineering plan measurement.",
                    },
                ))
        return issues


class UtilityDepthInvalidRule(ValidationRule):
    rule_id = "UTILITY_DEPTH_INVALID"
    name = "Utility Depth Negative or Physically Infeasible"
    description = "Checks that underground infrastructure depth values are physically plausible and non-negative."
    category = "UTILITY"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["UTILITY", "UTILITY_ASSET", "UTILITY_SEGMENT", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        utility_assets = getattr(context, "utility_assets", []) or []

        for asset in utility_assets:
            depth = getattr(asset, "depth", None)
            if depth is not None:
                if depth < 0.0:
                    asset_ref = getattr(asset, "asset_reference", str(asset.id))
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="UTL-002",
                        category=self.category,
                        severity=self.severity,
                        entity_type="UTILITY_ASSET",
                        entity_id=str(asset.id),
                        message=f"Utility asset '{asset_ref}' has negative depth ({depth} m).",
                        technical_explanation=f"Negative depth ({depth} m) violates subsurface topological constraints. Ground relative depth must be >= 0.",
                        expected_value=">= 0.0 m",
                        measured_value=f"{depth} m",
                        metadata_json={
                            "repair_suggestion": "Invert sign or verify whether asset is elevated above-ground structure."
                        },
                    ))
                elif depth > 50.0:
                    asset_ref = getattr(asset, "asset_reference", str(asset.id))
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="UTL-003",
                        category=self.category,
                        severity="WARNING",
                        entity_type="UTILITY_ASSET",
                        entity_id=str(asset.id),
                        message=f"Utility asset '{asset_ref}' has exceptional depth ({depth} m > 50m).",
                        technical_explanation="Depth exceeds standard municipal trench threshold (50m). Verification required.",
                        expected_value="<= 50.0 m",
                        measured_value=f"{depth} m",
                    ))
        return issues


class UtilityElevationInversionRule(ValidationRule):
    rule_id = "UTILITY_ELEVATION_INVERSION"
    name = "Utility Centerline Higher than Ground"
    description = "Checks that underground asset centerline elevation does not exceed ground elevation."
    category = "UTILITY"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["UTILITY", "UTILITY_ASSET", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        utility_assets = getattr(context, "utility_assets", []) or []

        for asset in utility_assets:
            g_elev = getattr(asset, "ground_elevation", None)
            c_elev = getattr(asset, "centerline_elevation", None)
            if g_elev is not None and c_elev is not None:
                if c_elev > g_elev + 0.01:
                    asset_ref = getattr(asset, "asset_reference", str(asset.id))
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="UTL-004",
                        category=self.category,
                        severity=self.severity,
                        entity_type="UTILITY_ASSET",
                        entity_id=str(asset.id),
                        message=f"Utility asset '{asset_ref}' centerline elevation ({c_elev}m) exceeds ground elevation ({g_elev}m).",
                        technical_explanation=f"Subsurface centerline elevation ({c_elev}m) is above ground elevation ({g_elev}m), representing an impossible underground geometry.",
                        expected_value=f"<= {g_elev} m",
                        measured_value=f"{c_elev} m",
                    ))
        return issues


class UtilityDanglingEndpointRule(ValidationRule):
    rule_id = "UTILITY_DANGLING_ENDPOINT"
    name = "Utility Dangling Segment Endpoint"
    description = "Checks if linear utility segments terminate without an associated node or connection."
    category = "UTILITY"
    severity = "INFO"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["UTILITY", "UTILITY_NETWORK", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        segments = getattr(context, "utility_segments", []) or []
        for seg in segments:
            s_node = getattr(seg, "start_node_id", None)
            e_node = getattr(seg, "end_node_id", None)
            if not s_node or not e_node:
                issues.append(IssueDraft(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    issue_code="UTL-005",
                    category=self.category,
                    severity=self.severity,
                    entity_type="UTILITY_SEGMENT",
                    entity_id=str(seg.id),
                    message=f"Utility segment '{seg.id}' has unanchored endpoint (missing start or end node).",
                    technical_explanation="Linear pipeline/duct segment terminates at an unmapped endpoint. May be normal service connection or unmapped junction.",
                ))
        return issues
