from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import shutil
import time
from app.core.logging import logger


@dataclass
class PageOCRData:
    page_number: int
    text: str
    confidence: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    blocks: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DocumentOCRResultData:
    engine: str
    engine_version: Optional[str]
    language: str
    full_text: str
    pages: List[PageOCRData]
    confidence: Optional[float] = None
    processing_time_ms: int = 0
    status: str = "COMPLETED"  # COMPLETED, OCR_ENGINE_NOT_CONFIGURED, FAILED
    error_message: Optional[str] = None


class BaseDocumentOCR(ABC):
    """Abstract base class for Document OCR and Text Extraction providers."""

    @abstractmethod
    def extract_text(self, file_path: Path, mime_type: str) -> DocumentOCRResultData:
        """Extracts text and page-level information from a document file."""
        pass


class PyPDFTextExtractor(BaseDocumentOCR):
    """Deterministic pure-Python text extractor for digital PDF documents."""

    def extract_text(self, file_path: Path, mime_type: str) -> DocumentOCRResultData:
        start_time = time.time()
        try:
            import pypdf
        except ImportError:
            return DocumentOCRResultData(
                engine="PYPDF_TEXT_EXTRACTOR",
                engine_version=None,
                language="en",
                full_text="",
                pages=[],
                status="OCR_ENGINE_NOT_CONFIGURED",
                error_message="pypdf library is not installed in the environment.",
            )

        try:
            reader = pypdf.PdfReader(str(file_path))
            pages_data: List[PageOCRData] = []
            full_text_chunks: List[str] = []

            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                # Attempt to extract dimensions
                width = None
                height = None
                try:
                    if page.mediabox:
                        width = int(page.mediabox.width)
                        height = int(page.mediabox.height)
                except Exception:
                    pass

                pages_data.append(PageOCRData(
                    page_number=idx + 1,
                    text=page_text.strip(),
                    confidence=1.0 if len(page_text.strip()) > 0 else None,
                    width=width,
                    height=height,
                    blocks=[],
                ))
                if page_text.strip():
                    full_text_chunks.append(page_text.strip())

            full_text = "\n\n--- Page Break ---\n\n".join(full_text_chunks)
            duration_ms = int((time.time() - start_time) * 1000)

            return DocumentOCRResultData(
                engine="PYPDF_TEXT_EXTRACTOR",
                engine_version=getattr(pypdf, "__version__", "1.0.0"),
                language="en",
                full_text=full_text,
                pages=pages_data,
                confidence=1.0 if full_text else None,
                processing_time_ms=duration_ms,
                status="COMPLETED",
            )
        except Exception as e:
            logger.exception(f"PyPDF extraction error for {file_path}: {e}")
            return DocumentOCRResultData(
                engine="PYPDF_TEXT_EXTRACTOR",
                engine_version=None,
                language="en",
                full_text="",
                pages=[],
                status="FAILED",
                error_message=f"PDF extraction error: {str(e)}",
            )


class TesseractOCREngine(BaseDocumentOCR):
    """Optical Character Recognition engine using Tesseract binary."""

    def __init__(self, tesseract_cmd: Optional[str] = None):
        self.tesseract_cmd = tesseract_cmd or shutil.which("tesseract")

    def is_available(self) -> bool:
        return self.tesseract_cmd is not None

    def extract_text(self, file_path: Path, mime_type: str) -> DocumentOCRResultData:
        start_time = time.time()
        if not self.is_available():
            return DocumentOCRResultData(
                engine="TESSERACT_OCR",
                engine_version=None,
                language="en",
                full_text="",
                pages=[],
                status="OCR_ENGINE_NOT_CONFIGURED",
                error_message="Tesseract OCR binary is not installed or configured on the system PATH.",
            )

        try:
            import pytesseract
            from PIL import Image

            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

            image = Image.open(str(file_path))
            raw_text = pytesseract.image_to_string(image, lang="eng")
            duration_ms = int((time.time() - start_time) * 1000)

            page = PageOCRData(
                page_number=1,
                text=raw_text.strip(),
                confidence=0.85,
                width=image.width,
                height=image.height,
            )

            return DocumentOCRResultData(
                engine="TESSERACT_OCR",
                engine_version="5.0",
                language="en",
                full_text=raw_text.strip(),
                pages=[page],
                confidence=0.85,
                processing_time_ms=duration_ms,
                status="COMPLETED",
            )
        except Exception as e:
            logger.exception(f"Tesseract OCR execution error: {e}")
            return DocumentOCRResultData(
                engine="TESSERACT_OCR",
                engine_version=None,
                language="en",
                full_text="",
                pages=[],
                status="FAILED",
                error_message=f"OCR execution failed: {str(e)}",
            )


class CompositeDocumentOCR(BaseDocumentOCR):
    """Composite OCR provider that chooses the best available engine without fake output."""

    def __init__(self):
        self.pypdf_extractor = PyPDFTextExtractor()
        self.tesseract_engine = TesseractOCREngine()

    def extract_text(self, file_path: Path, mime_type: str) -> DocumentOCRResultData:
        mime = mime_type.lower()
        if mime == "application/pdf":
            # Extract PDF text
            res = self.pypdf_extractor.extract_text(file_path, mime)
            if res.status == "COMPLETED" and res.full_text.strip():
                return res
            # If PDF has no digital text (scanned image inside PDF), attempt Tesseract if available
            if self.tesseract_engine.is_available():
                return self.tesseract_engine.extract_text(file_path, mime)
            # If Tesseract not available, return PDF pages with clear unconfigured notification
            if res.status == "COMPLETED" and not res.full_text.strip():
                res.status = "OCR_ENGINE_NOT_CONFIGURED"
                res.error_message = "Scanned PDF image contains no digital text layer and OCR engine is not configured."
            return res

        elif mime.startswith("image/"):
            if self.tesseract_engine.is_available():
                return self.tesseract_engine.extract_text(file_path, mime)
            else:
                return DocumentOCRResultData(
                    engine="TESSERACT_OCR",
                    engine_version=None,
                    language="en",
                    full_text="",
                    pages=[PageOCRData(page_number=1, text="", confidence=None)],
                    status="OCR_ENGINE_NOT_CONFIGURED",
                    error_message="Image uploaded but Tesseract OCR binary is not configured. Manual text entry or review required.",
                )

        return DocumentOCRResultData(
            engine="COMPOSITE_OCR",
            engine_version=None,
            language="en",
            full_text="",
            pages=[],
            status="FAILED",
            error_message=f"Unsupported document mime type '{mime_type}'.",
        )


document_ocr_engine = CompositeDocumentOCR()
