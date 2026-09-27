from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.gis.validation.base import IssueDraft, ValidationContext, ValidationRule


class DocumentParcelReferenceMismatchRule(ValidationRule):
    rule_id = "DOCUMENT_PARCEL_REFERENCE_MISMATCH"
    name = "Document Parcel Reference Discrepancy"
    description = "Checks that the parcel reference extracted from the document matches the official GeoVertex cadastral parcel record."
    category = "CROSS_DATASET"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["DOCUMENT", "PARCEL", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        parcels_by_id = {str(p.id): p for p in context.parcels}

        for doc in context.property_documents:
            if not getattr(doc, "parcel_id", None):
                continue

            target_parcel = parcels_by_id.get(str(doc.parcel_id))
            if not target_parcel:
                continue

            # Look for extracted parcel number in document fields
            extracted_parcel = None
            doc_fields = getattr(doc, "extracted_fields", []) or []
            if not doc_fields and hasattr(context, "document_fields"):
                doc_fields = [f for f in context.document_fields if getattr(f, "document_id", None) == str(doc.id) or getattr(f, "document_version_id", None) == str(getattr(doc, "current_version_id", ""))]

            for f in doc_fields:
                if getattr(f, "field_name", "") in ["parcel_number", "survey_number"]:
                    extracted_parcel = getattr(f, "normalized_value", None) or getattr(f, "field_value", None)
                    break

            if extracted_parcel:
                official_num = getattr(target_parcel, "parcel_number", "")
                official_code = getattr(target_parcel, "parcel_code", "")

                # Check if extracted reference differs from official record
                clean_extracted = extracted_parcel.strip().upper().replace(" ", "")
                clean_num = official_num.strip().upper().replace(" ", "")
                clean_code = official_code.strip().upper().replace(" ", "")

                if clean_extracted != clean_num and clean_extracted != clean_code:
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="DOC-001",
                        category=self.category,
                        severity=self.severity,
                        entity_type="DOCUMENT",
                        entity_id=str(doc.id),
                        related_entity_type="PARCEL",
                        related_entity_id=str(target_parcel.id),
                        message=f"Document parcel reference '{extracted_parcel}' does not match official cadastral parcel '{official_num}'.",
                        technical_explanation=f"Text extracted from document states parcel '{extracted_parcel}', but associated GeoVertex parcel is '{official_num}' ({official_code}).",
                        expected_value=official_num,
                        measured_value=extracted_parcel,
                        metadata_json={
                            "document_reference": getattr(doc, "document_reference", ""),
                            "extracted_value": extracted_parcel,
                            "official_parcel_number": official_num,
                        },
                    ))
        return issues


class DocumentBuildingReferenceMismatchRule(ValidationRule):
    rule_id = "DOCUMENT_BUILDING_REFERENCE_MISMATCH"
    name = "Document Building Reference Discrepancy"
    description = "Checks that the building reference extracted from the document matches the associated building footprint."
    category = "CROSS_DATASET"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["DOCUMENT", "BUILDING", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        buildings_by_id = {str(b.id): b for b in context.buildings}

        for doc in context.property_documents:
            if not getattr(doc, "building_id", None):
                continue
            target_bld = buildings_by_id.get(str(doc.building_id))
            if not target_bld:
                continue

            extracted_bld = None
            doc_fields = getattr(doc, "extracted_fields", []) or []
            for f in doc_fields:
                if getattr(f, "field_name", "") == "building_number":
                    extracted_bld = getattr(f, "normalized_value", None) or getattr(f, "field_value", None)
                    break

            if extracted_bld:
                official_ref = getattr(target_bld, "building_reference", "")
                if extracted_bld.strip().upper() != official_ref.strip().upper():
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="DOC-002",
                        category=self.category,
                        severity=self.severity,
                        entity_type="DOCUMENT",
                        entity_id=str(doc.id),
                        related_entity_type="BUILDING",
                        related_entity_id=str(target_bld.id),
                        message=f"Document building reference '{extracted_bld}' deviates from cadastral building '{official_ref}'.",
                        technical_explanation=f"Extracted building identifier '{extracted_bld}' differs from authoritative registered building reference '{official_ref}'.",
                        expected_value=official_ref,
                        measured_value=extracted_bld,
                    ))
        return issues


class DocumentUnitReferenceMismatchRule(ValidationRule):
    rule_id = "DOCUMENT_UNIT_REFERENCE_MISMATCH"
    name = "Document Unit Reference Discrepancy"
    description = "Checks that unit identifier extracted from document matches associated property unit."
    category = "CROSS_DATASET"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["DOCUMENT", "UNIT", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        units_by_id = {str(u.id): u for u in context.units}

        for doc in context.property_documents:
            if not getattr(doc, "unit_id", None):
                continue
            target_unit = units_by_id.get(str(doc.unit_id))
            if not target_unit:
                continue

            extracted_unit = None
            doc_fields = getattr(doc, "extracted_fields", []) or []
            for f in doc_fields:
                if getattr(f, "field_name", "") == "unit_number":
                    extracted_unit = getattr(f, "normalized_value", None) or getattr(f, "field_value", None)
                    break

            if extracted_unit:
                official_unit = getattr(target_unit, "unit_number", "")
                if extracted_unit.strip().upper() != official_unit.strip().upper():
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="DOC-003",
                        category=self.category,
                        severity=self.severity,
                        entity_type="DOCUMENT",
                        entity_id=str(doc.id),
                        related_entity_type="UNIT",
                        related_entity_id=str(target_unit.id),
                        message=f"Document unit reference '{extracted_unit}' does not match official unit '{official_unit}'.",
                        technical_explanation=f"Extracted deed unit '{extracted_unit}' differs from authoritative unit record '{official_unit}'.",
                        expected_value=official_unit,
                        measured_value=extracted_unit,
                    ))
        return issues


class DocumentAreaMismatchRule(ValidationRule):
    rule_id = "DOCUMENT_AREA_MISMATCH"
    name = "Document Declared Area vs Geometry Area Discrepancy"
    description = "Checks that the area declared in the document matches the geometry-derived area of the linked cadastral parcel or building within tolerance."
    category = "CROSS_DATASET"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["DOCUMENT", "PARCEL", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        parcels_by_id = {str(p.id): p for p in context.parcels}
        max_pct = getattr(context.tolerances, "document_area_diff_pct_tolerance", 5.0)

        for doc in context.property_documents:
            if not getattr(doc, "parcel_id", None):
                continue
            target_parcel = parcels_by_id.get(str(doc.parcel_id))
            if not target_parcel:
                continue

            extracted_area = None
            doc_fields = getattr(doc, "extracted_fields", []) or []
            for f in doc_fields:
                if getattr(f, "field_name", "") in ["land_area", "built_up_area"]:
                    norm = getattr(f, "normalized_value", "") or ""
                    # normalized_value is e.g. "125.00 sq.m"
                    import re
                    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*sq\.m", norm)
                    if m:
                        extracted_area = float(m.group(1))
                        break

            if extracted_area and extracted_area > 0:
                geo_area = getattr(target_parcel, "area_sqm", None) or getattr(target_parcel, "area", None)
                if geo_area and geo_area > 0:
                    diff_pct = abs(extracted_area - geo_area) / geo_area * 100.0
                    if diff_pct > max_pct:
                        issues.append(IssueDraft(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            issue_code="DOC-004",
                            category=self.category,
                            severity=self.severity,
                            entity_type="DOCUMENT",
                            entity_id=str(doc.id),
                            related_entity_type="PARCEL",
                            related_entity_id=str(target_parcel.id),
                            message=f"Document declared area ({extracted_area:.2f} m²) deviates from GIS parcel geometry ({geo_area:.2f} m²) by {diff_pct:.1f}%.",
                            technical_explanation=f"Area discrepancy of {diff_pct:.1f}% exceeds allowable tolerance of {max_pct}%. Requires surveyor field or deed review.",
                            expected_value=f"{geo_area:.2f} m²",
                            measured_value=f"{extracted_area:.2f} m²",
                            tolerance=f"{max_pct}% ({geo_area * max_pct / 100:.2f} m²)",
                            metadata_json={
                                "discrepancy_pct": round(diff_pct, 2),
                                "declared_area_sqm": extracted_area,
                                "geometry_area_sqm": geo_area,
                            },
                        ))
        return issues


class DocumentDateInconsistencyRule(ValidationRule):
    rule_id = "DOCUMENT_DATE_INCONSISTENCY"
    name = "Document Date Logical Inconsistency"
    description = "Checks that document execution or registration dates are plausible and not in the future."
    category = "CROSS_DATASET"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["DOCUMENT", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        now = datetime.now(timezone.utc)

        for doc in context.property_documents:
            doc_date = getattr(doc, "document_date", None)
            if doc_date:
                # Ensure timezone aware comparison
                if doc_date.tzinfo is None:
                    doc_date = doc_date.replace(tzinfo=timezone.utc)
                if doc_date > now:
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="DOC-005",
                        category=self.category,
                        severity=self.severity,
                        entity_type="DOCUMENT",
                        entity_id=str(doc.id),
                        message=f"Document date '{doc_date.strftime('%Y-%m-%d')}' is set in the future.",
                        technical_explanation="A property legal document cannot possess an execution or registration date later than current date.",
                        expected_value=f"<= {now.strftime('%Y-%m-%d')}",
                        measured_value=doc_date.strftime("%Y-%m-%d"),
                    ))
        return issues


class DocumentDuplicateCandidateRule(ValidationRule):
    rule_id = "DOCUMENT_DUPLICATE_CANDIDATE"
    name = "Duplicate Property Document Detection"
    description = "Identifies documents with identical cryptographic file hash or identical document number and issuing authority."
    category = "CROSS_DATASET"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["DOCUMENT", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        seen_refs: Dict[str, Any] = {}

        for doc in context.property_documents:
            doc_ref = getattr(doc, "document_reference", "")
            if doc_ref:
                if doc_ref in seen_refs:
                    prev = seen_refs[doc_ref]
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="DOC-006",
                        category=self.category,
                        severity=self.severity,
                        entity_type="DOCUMENT",
                        entity_id=str(doc.id),
                        related_entity_type="DOCUMENT",
                        related_entity_id=str(prev.id),
                        message=f"Duplicate document reference detected: '{doc_ref}'.",
                        technical_explanation=f"Multiple document records share the identical reference '{doc_ref}'.",
                        expected_value="Unique document reference",
                        measured_value=doc_ref,
                    ))
                else:
                    seen_refs[doc_ref] = doc
        return issues


class DocumentNumberMissingRule(ValidationRule):
    rule_id = "DOCUMENT_NUMBER_MISSING"
    name = "Document Registration Number Missing"
    description = "Flags deeds, titles, and tax records lacking an extracted or declared document/registration number."
    category = "CROSS_DATASET"
    severity = "WARNING"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["DOCUMENT", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        MANDATORY_TYPES = ["SALE_DEED", "TITLE_DOCUMENT", "PROPERTY_TAX_RECORD", "PROPERTY_REGISTRATION"]

        for doc in context.property_documents:
            doc_type = getattr(doc, "document_type", "OTHER")
            if doc_type in MANDATORY_TYPES:
                doc_fields = getattr(doc, "extracted_fields", []) or []
                has_doc_num = any(getattr(f, "field_name", "") == "document_number" for f in doc_fields)
                if not has_doc_num and not getattr(doc, "document_reference", None):
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="DOC-007",
                        category=self.category,
                        severity=self.severity,
                        entity_type="DOCUMENT",
                        entity_id=str(doc.id),
                        message=f"Document of type '{doc_type}' is missing a registration or document number.",
                        technical_explanation="Authoritative property deeds and tax receipts require a formal registration or document identification number.",
                        expected_value="Extracted document_number",
                        measured_value="None",
                    ))
        return issues


class DocumentParcelReferenceMissingRule(ValidationRule):
    rule_id = "PARCEL_REFERENCE_MISSING"
    name = "Property Document Lacks Linked Cadastral Parcel"
    description = "Flags property documents that are unlinked to any cadastral parcel."
    category = "CROSS_DATASET"
    severity = "INFO"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["DOCUMENT", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        for doc in context.property_documents:
            if not getattr(doc, "parcel_id", None):
                issues.append(IssueDraft(
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    issue_code="DOC-008",
                    category=self.category,
                    severity=self.severity,
                    entity_type="DOCUMENT",
                    entity_id=str(doc.id),
                    message=f"Document '{getattr(doc, 'document_reference', doc.id)}' is not linked to any cadastral parcel.",
                    technical_explanation="The property document has not been linked to a GeoVertex cadastral parcel.",
                    expected_value="Linked parcel_id",
                    measured_value="None",
                ))
        return issues
