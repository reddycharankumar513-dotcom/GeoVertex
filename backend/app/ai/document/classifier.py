from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import re
from app.models.document import DocumentType


@dataclass
class ClassificationResult:
    predicted_type: str
    confidence: Optional[float]
    evidence: Optional[str]
    method: str  # AI_MODEL, RULE_BASED_KEYWORD, MANUAL
    model_id: Optional[str] = None
    model_version: Optional[str] = None
    status: str = "COMPLETED"  # COMPLETED, MODEL_NOT_CONFIGURED, MANUAL_CLASSIFICATION_REQUIRED


class BaseDocumentClassifier(ABC):
    @abstractmethod
    def classify(self, text: str, filename: str, title: Optional[str] = None) -> ClassificationResult:
        pass


class RuleBasedDocumentClassifier(BaseDocumentClassifier):
    """Deterministic keyword-based document classifier providing traceable evidence."""

    KEYWORD_PATTERNS = [
        (DocumentType.SALE_DEED.value, [
            r"\b(sale\s+deed|deed\s+of\s+sale|conveyance\s+deed|vendor\s+and\s+purchaser)\b",
        ]),
        (DocumentType.TITLE_DOCUMENT.value, [
            r"\b(title\s+deed|certificate\s+of\s+title|ownership\s+certificate|patta\s+passbook)\b",
        ]),
        (DocumentType.PROPERTY_TAX_RECORD.value, [
            r"\b(property\s+tax|tax\s+receipt|tax\s+assessment|municipal\s+tax|holding\s+tax)\b",
        ]),
        (DocumentType.PROPERTY_REGISTRATION.value, [
            r"\b(registration\s+certificate|sub-registrar|encumbrance\s+certificate|book\s+no\s+\d+)\b",
        ]),
        (DocumentType.BUILDING_PLAN.value, [
            r"\b(building\s+plan|site\s+plan|architectural\s+drawing|sanctioned\s+plan)\b",
        ]),
        (DocumentType.FLOOR_PLAN.value, [
            r"\b(floor\s+plan|typical\s+floor|first\s+floor\s+layout|ground\s+floor\s+layout)\b",
        ]),
        (DocumentType.APPROVAL_DOCUMENT.value, [
            r"\b(commencement\s+certificate|building\s+permit|town\s+planning\s+approval|noc\b)\b",
        ]),
        (DocumentType.OCCUPANCY_DOCUMENT.value, [
            r"\b(occupancy\s+certificate|completion\s+certificate|possession\s+letter)\b",
        ]),
        (DocumentType.SURVEY_DOCUMENT.value, [
            r"\b(cadastral\s+survey|survey\s+report|field\s+measurement\s+book|fmb\s+sketch|traverse\s+sheet)\b",
        ]),
        (DocumentType.LAND_RECORD.value, [
            r"\b(record\s+of\s+rights|ror\b|jamabandi|khata\s+extract|khasra\s+girdawari)\b",
        ]),
        (DocumentType.ENCUMBRANCE_RECORD.value, [
            r"\b(non-encumbrance|nil\s+encumbrance|encumbrance\s+statement)\b",
        ]),
        (DocumentType.UTILITY_DOCUMENT.value, [
            r"\b(electricity\s+bill|water\s+bill|utility\s+connection|sewerage\s+board)\b",
        ]),
    ]

    def classify(self, text: str, filename: str, title: Optional[str] = None) -> ClassificationResult:
        combined_text = f"{title or ''} {filename} {text}".lower()

        for doc_type, patterns in self.KEYWORD_PATTERNS:
            for pat in patterns:
                match = re.search(pat, combined_text, re.IGNORECASE)
                if match:
                    # Extract surrounding snippet as evidence
                    start = max(0, match.start() - 30)
                    end = min(len(combined_text), match.end() + 30)
                    evidence_snippet = combined_text[start:end].strip()

                    return ClassificationResult(
                        predicted_type=doc_type,
                        confidence=0.85,
                        evidence=f"Matched keyword '{match.group(0)}' in document text: '...{evidence_snippet}...'",
                        method="RULE_BASED_KEYWORD",
                        status="COMPLETED",
                    )

        # If no keywords matched, mandate manual classification
        return ClassificationResult(
            predicted_type=DocumentType.OTHER.value,
            confidence=None,
            evidence="No authoritative cadastral classification keywords identified in document.",
            method="RULE_BASED_KEYWORD",
            status="MANUAL_CLASSIFICATION_REQUIRED",
        )


class AIModelDocumentClassifier(BaseDocumentClassifier):
    """Classifier interface for deep learning / zero-shot NLP models."""

    def __init__(self, model_loaded: bool = False):
        self.model_loaded = model_loaded

    def classify(self, text: str, filename: str, title: Optional[str] = None) -> ClassificationResult:
        if not self.model_loaded:
            return ClassificationResult(
                predicted_type=DocumentType.OTHER.value,
                confidence=None,
                evidence=None,
                method="AI_MODEL",
                status="MODEL_NOT_CONFIGURED",
            )
        # Placeholder for trained PyTorch/transformer classifier
        return ClassificationResult(
            predicted_type=DocumentType.SALE_DEED.value,
            confidence=0.92,
            evidence="Transformer classification tensor match",
            method="AI_MODEL",
            model_id="geovertex-doc-classifier-v1",
            model_version="1.0.0",
            status="COMPLETED",
        )


class CompositeDocumentClassifier(BaseDocumentClassifier):
    """Orchestrates AI classification with deterministic keyword fallback."""

    def __init__(self):
        self.ai_classifier = AIModelDocumentClassifier(model_loaded=False)
        self.rule_classifier = RuleBasedDocumentClassifier()

    def classify(self, text: str, filename: str, title: Optional[str] = None) -> ClassificationResult:
        # Try AI classifier first if configured
        ai_res = self.ai_classifier.classify(text, filename, title)
        if ai_res.status == "COMPLETED":
            return ai_res

        # Fallback to rule-based keyword classifier
        return self.rule_classifier.classify(text, filename, title)


document_classifier = CompositeDocumentClassifier()
