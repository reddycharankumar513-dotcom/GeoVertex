from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import re
from app.ai.document.normalizer import document_normalizer
from app.models.document import ConfidenceLevel


@dataclass
class ExtractedFieldDraft:
    field_name: str
    field_value: str
    normalized_value: Optional[str]
    data_type: str
    page_number: Optional[int] = None
    bounding_box: Optional[Dict[str, Any]] = None
    extraction_method: str = "RULE_BASED"
    confidence: Optional[float] = 0.90
    confidence_level: str = ConfidenceLevel.HIGH.value
    evidence_text: Optional[str] = None
    model_id: Optional[str] = None
    model_version: Optional[str] = None


class BaseDocumentFieldExtractor(ABC):
    @abstractmethod
    def extract_fields(self, full_text: str, pages: List[Any]) -> List[ExtractedFieldDraft]:
        pass


class RuleBasedFieldExtractor(BaseDocumentFieldExtractor):
    """Deterministic regex-based field extractor extracting property cadastre identifiers with evidence."""

    FIELD_PATTERNS = [
        # Property Identification
        ("parcel_number", r"\b(?:parcel\s*(?:no|number|id|#|code)|plot\s*(?:no|number|#|code)|parcel\s*[:#\-])\s*[:.\-]?\s*([A-Z0-9\-\/]+)\b", "STRING"),
        ("survey_number", r"\b(?:survey\s*(?:no|number|#|nos)?|sy\.?\s*no)\s*[:.\-]?\s*([A-Z0-9\-\/\s]+?)(?=[,\n;]|and|\s+situated|\s+measuring|$)", "STRING"),
        ("property_reference", r"\b(?:property\s*(?:id|number|reference|code|no)|holding\s*no)\s*[:.\-]?\s*([A-Z0-9\-\/]+)\b", "STRING"),
        ("building_number", r"\b(?:building\s*(?:no|number|#|name)|house\s*(?:no|number|#)|door\s*(?:no|number|#))\s*[:.\-]?\s*([A-Z0-9\-\/\s]+?)(?=[,\n;]|$)", "STRING"),
        ("floor_number", r"\b(?:floor\s*(?:no|number|#|level)|story\s*(?:no|number|#)|floor\s*[:#])\s*[:.\-]?\s*([A-Za-z0-9\-\/\s]+?)(?=[,\n;]|$)", "STRING"),
        ("unit_number", r"\b(?:unit\s*(?:no|number|#)|flat\s*(?:no|number|#)|apartment\s*(?:no|number|#)|suite\s*(?:no|number|#)|(?:unit|flat)\s*[:#])\s*[:.\-]?\s*([A-Z0-9\-\/]+)\b", "STRING"),

        # Document Details
        ("document_number", r"\b(?:document\s*(?:no|number|id|#)|doc\s*(?:no|number|id|#)|registration\s*(?:no|number|id|#)|deed\s*(?:no|number|id|#)|document\s*[:#])\s*[:.\-]?\s*([A-Z0-9\-\/]+)\b", "STRING"),
        ("document_date", r"\b(?:date\s*of\s*(?:execution|registration|deed)|document\s*date|dated)\s*[:.\-]?\s*([0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4}|[0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+[0-9]{4}|[A-Za-z]+\s+[0-9]{1,2}(?:st|nd|rd|th)?,\s*[0-9]{4})\b", "DATE"),
        ("issuing_authority", r"\b(?:sub-registrar|registration\s*office|office\s*of\s*the\s*sub-registrar|issuing\s*authority)\s*[:.\-]?\s*([A-Za-z0-9\s,\-]+?)(?=[,\n;]|$)", "STRING"),

        # Measurements
        ("land_area", r"\b(?:land\s*area|extent\s*of\s*land|plot\s*area|total\s*extent|site\s*area)\s*[:.\-]?\s*([0-9,]+(?:\.[0-9]+)?\s*(?:sq\.?\s*ft|sq\.?\s*feet|sq\.?\s*yards|sq\.?\s*m|acres|hectares|guntas|square\s*feet|square\s*meters))\b", "AREA"),
        ("built_up_area", r"\b(?:built[\s\-]*up\s*area|carpet\s*area|plinth\s*area|super\s*built[\s\-]*up\s*area)\s*[:.\-]?\s*([0-9,]+(?:\.[0-9]+)?\s*(?:sq\.?\s*ft|sq\.?\s*feet|sq\.?\s*yards|sq\.?\s*m|square\s*feet|square\s*meters))\b", "AREA"),

        # Geographic Details
        ("postal_code", r"\b(?:pin(?:\s*code)?|postal\s*code|zip(?:\s*code)?)\s*[:.\-]?\s*([0-9]{5,6})\b", "STRING"),
        ("address", r"\b(?:situated\s*at|property\s*address|location)\s*[:.\-]?\s*([A-Za-z0-9\s,\-\.\/]+?)(?=\.\s+|\n\n|bounded\s+by|$)", "ADDRESS"),

        # Cadastral Boundaries
        ("north_boundary", r"\b(?:north\s*by|north\s*boundary|on\s*the\s*north)\s*[:.\-]?\s*([A-Za-z0-9\s,\-\.\/]+?)(?=[,;\n]|south|$)", "STRING"),
        ("south_boundary", r"\b(?:south\s*by|south\s*boundary|on\s*the\s*south)\s*[:.\-]?\s*([A-Za-z0-9\s,\-\.\/]+?)(?=[,;\n]|east|$)", "STRING"),
        ("east_boundary", r"\b(?:east\s*by|east\s*boundary|on\s*the\s*east)\s*[:.\-]?\s*([A-Za-z0-9\s,\-\.\/]+?)(?=[,;\n]|west|$)", "STRING"),
        ("west_boundary", r"\b(?:west\s*by|west\s*boundary|on\s*the\s*west)\s*[:.\-]?\s*([A-Za-z0-9\s,\-\.\/]+?)(?=[,;\n]|\.|$)", "STRING"),
    ]

    def extract_fields(self, full_text: str, pages: List[Any]) -> List[ExtractedFieldDraft]:
        extracted: List[ExtractedFieldDraft] = []
        seen_field_names = set()

        for field_name, pattern, data_type in self.FIELD_PATTERNS:
            if field_name in seen_field_names:
                continue

            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                raw_val = match.group(1).strip()
                if not raw_val or len(raw_val) < 2:
                    continue

                # Find which page it occurred on
                page_num = 1
                evidence_snippet = None
                for p in pages:
                    p_text = getattr(p, "text", "") or ""
                    if raw_val in p_text or match.group(0) in p_text:
                        page_num = getattr(p, "page_number", 1)
                        # Extract surrounding snippet
                        pos = p_text.find(raw_val)
                        if pos != -1:
                            start = max(0, pos - 40)
                            end = min(len(p_text), pos + len(raw_val) + 40)
                            evidence_snippet = f"...{p_text[start:end].strip()}..."
                        break

                if not evidence_snippet:
                    start = max(0, match.start() - 30)
                    end = min(len(full_text), match.end() + 30)
                    evidence_snippet = f"...{full_text[start:end].strip()}..."

                # Compute normalized value
                normalized_val = None
                if data_type == "DATE":
                    norm_date, _ = document_normalizer.normalize_date(raw_val)
                    normalized_val = norm_date
                elif data_type == "AREA":
                    _, norm_area = document_normalizer.normalize_area(raw_val)
                    normalized_val = norm_area
                elif field_name == "survey_number":
                    normalized_val = document_normalizer.normalize_survey_number(raw_val)
                elif field_name == "parcel_number":
                    normalized_val = document_normalizer.normalize_parcel_code(raw_val)
                elif field_name == "postal_code":
                    normalized_val = document_normalizer.normalize_postal_code(raw_val)
                elif data_type == "ADDRESS":
                    normalized_val = document_normalizer.normalize_address(raw_val)
                else:
                    normalized_val = raw_val.strip()

                extracted.append(ExtractedFieldDraft(
                    field_name=field_name,
                    field_value=raw_val,
                    normalized_value=normalized_val,
                    data_type=data_type,
                    page_number=page_num,
                    extraction_method="RULE_BASED_REGEX",
                    confidence=0.92,
                    confidence_level=ConfidenceLevel.HIGH.value,
                    evidence_text=evidence_snippet,
                    model_id="rule-regex-cadastre-v1",
                    model_version="1.0.0",
                ))
                seen_field_names.add(field_name)

        return extracted


class DocumentExtractionProvider(BaseDocumentFieldExtractor):
    """Abstraction for LLM-based structured document extraction."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def extract_fields(self, full_text: str, pages: List[Any]) -> List[ExtractedFieldDraft]:
        if not self.is_configured():
            # Mandatory rule: Do NOT invent LLM output when unconfigured
            return []

        # Real LLM call would execute schema-validated completion here
        return []


class CompositeDocumentFieldExtractor(BaseDocumentFieldExtractor):
    """Combines rule-based extraction with configured LLM extraction without fake data."""

    def __init__(self):
        self.rule_extractor = RuleBasedFieldExtractor()
        self.llm_extractor = DocumentExtractionProvider()

    def extract_fields(self, full_text: str, pages: List[Any]) -> List[ExtractedFieldDraft]:
        rule_fields = self.rule_extractor.extract_fields(full_text, pages)
        llm_fields = self.llm_extractor.extract_fields(full_text, pages)

        # Merge, prioritizing high-confidence rule extractions
        field_map = {f.field_name: f for f in llm_fields}
        for f in rule_fields:
            field_map[f.field_name] = f

        return list(field_map.values())


document_field_extractor = CompositeDocumentFieldExtractor()
