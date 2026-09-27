from typing import Any, Dict, List
from app.gis.validation.base import IssueDraft, ValidationContext, ValidationRule


class CRSMissingRule(ValidationRule):
    rule_id = "CRS_MISSING"
    name = "Missing Coordinate Reference System"
    description = "Checks that geometries have an explicit SRID or CRS definition."
    category = "CRS"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return True

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for p in context.parcels:
            srid = getattr(p, "srid", None)
            if srid is None:
                p_code = getattr(p, "parcel_number", str(p.id))
                issues.append(IssueDraft(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    issue_code="CRS-001",
                    category=self.category,
                    severity=self.severity,
                    entity_type="PARCEL",
                    entity_id=str(p.id),
                    message=f"Parcel {p_code} has no explicit SRID definition.",
                    technical_explanation="Spatial coordinates without an authoritative SRID cannot be safely reprojected or topologically intersected.",
                    expected_value="SRID (e.g. 4326)",
                    measured_value="None",
                ))
        return issues


class CRSMismatchRule(ValidationRule):
    rule_id = "CRS_MISMATCH"
    name = "CRS Incompatibility Across Datasets"
    description = "Detects coordinate system mismatches between local administrative jurisdiction and contained parcels."
    category = "CRS"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["PARCEL", "JURISDICTION", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        jur_map = {str(j.id): j for j in context.jurisdictions}
        for p in context.parcels:
            jur_id = getattr(p, "jurisdiction_id", None)
            p_srid = getattr(p, "srid", 4326)
            if jur_id and str(jur_id) in jur_map:
                jur = jur_map[str(jur_id)]
                j_srid = getattr(jur, "srid", 4326)
                if p_srid and j_srid and p_srid != j_srid:
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="CRS-002",
                        category=self.category,
                        severity=self.severity,
                        entity_type="PARCEL",
                        entity_id=str(p.id),
                        related_entity_type="JURISDICTION",
                        related_entity_id=str(jur.id),
                        message=f"Parcel SRID ({p_srid}) differs from jurisdiction native SRID ({j_srid}).",
                        technical_explanation=f"Reprojection required between parcel EPSG:{p_srid} and administrative boundary EPSG:{j_srid}.",
                        measured_value=f"EPSG:{p_srid}",
                        expected_value=f"EPSG:{j_srid}",
                    ))
        return issues
