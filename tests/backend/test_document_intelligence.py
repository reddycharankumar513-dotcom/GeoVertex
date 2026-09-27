import io
import os
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.document.classifier import (
    AIModelDocumentClassifier,
    RuleBasedDocumentClassifier,
    document_classifier,
)
from app.ai.document.extractor import RuleBasedFieldExtractor, document_field_extractor
from app.ai.document.matcher import document_cadastral_matcher
from app.ai.document.normalizer import document_normalizer
from app.ai.document.ocr import PyPDFTextExtractor, TesseractOCREngine, document_ocr_engine
from app.gis.validation.base import ValidationContext
from app.gis.validation.document_rules import (
    DocumentAreaMismatchRule,
    DocumentDateInconsistencyRule,
    DocumentParcelReferenceMismatchRule,
    DocumentDuplicateCandidateRule,
)
from app.models.document import (
    ConfidenceLevel,
    DocumentExtractedField,
    DocumentStatus,
    DocumentType,
    FieldReviewStatus,
    PropertyDocument,
)
from app.models.jurisdiction import Jurisdiction
from app.models.organization import Organization
from app.models.parcel import Parcel
from app.models.user import User, UserRole
from app.services.document_storage_service import document_storage_service


@pytest.mark.asyncio
async def test_file_validation_and_storage_hashing():
    """Verify document file validation, directory traversal protection, and SHA-256 hash generation."""
    sample_content = b"%PDF-1.4\n1 0 obj\n<< /Title (Cadastral Deed) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    doc_id = str(uuid.uuid4())

    storage_key, filename, file_size, file_hash, mime_type = document_storage_service.save_raw_bytes(
        document_id=doc_id,
        version_number=1,
        filename="test_deed.pdf",
        content=sample_content,
        content_type="application/pdf",
    )

    assert filename == "test_deed.pdf"
    assert file_size == len(sample_content)
    assert mime_type == "application/pdf"
    assert len(file_hash) == 64  # SHA-256 hex string

    # Verify file can be retrieved safely
    resolved_path = document_storage_service.get_file_path(storage_key)
    assert resolved_path.exists()
    assert resolved_path.read_bytes() == sample_content

    # Clean up test files
    document_storage_service.delete_document_files(doc_id)


@pytest.mark.asyncio
async def test_ocr_and_unconfigured_states_enforce_no_fake_ai():
    """Verify that unconfigured OCR engines return explicit states rather than synthetic output."""
    tesseract = TesseractOCREngine(tesseract_cmd=None)
    assert not tesseract.is_available()

    # Attempting OCR without configured binary must return OCR_ENGINE_NOT_CONFIGURED
    dummy_path = document_storage_service.base_dir / "non_existent.png"
    res = tesseract.extract_text(dummy_path, "image/png")
    assert res.status == "OCR_ENGINE_NOT_CONFIGURED"
    assert res.full_text == ""
    assert "not installed or configured" in (res.error_message or "")


@pytest.mark.asyncio
async def test_document_classification_and_evidence():
    """Test deterministic document classification and traceable keyword evidence."""
    classifier = RuleBasedDocumentClassifier()

    # 1. Sale deed classification
    sale_text = "This INDENTURE OF SALE DEED made between Vendor and Purchaser for residential plot..."
    res_sale = classifier.classify(sale_text, "document.pdf")
    assert res_sale.status == "COMPLETED"
    assert res_sale.predicted_type == DocumentType.SALE_DEED.value
    assert res_sale.confidence == 0.85
    assert "sale deed" in (res_sale.evidence or "").lower()

    # 2. Tax record classification
    tax_text = "MUNICIPAL CORPORATION PROPERTY TAX RECEIPT holding tax paid for assessment year 2026..."
    res_tax = classifier.classify(tax_text, "receipt.pdf")
    assert res_tax.status == "COMPLETED"
    assert res_tax.predicted_type == DocumentType.PROPERTY_TAX_RECORD.value

    # 3. Unrecognized text mandates manual classification
    gibberish = "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
    res_unknown = classifier.classify(gibberish, "unknown.pdf")
    assert res_unknown.status == "MANUAL_CLASSIFICATION_REQUIRED"
    assert res_unknown.confidence is None

    # 4. Unconfigured AI model returns MODEL_NOT_CONFIGURED
    ai_cls = AIModelDocumentClassifier(model_loaded=False)
    ai_res = ai_cls.classify(sale_text, "doc.pdf")
    assert ai_res.status == "MODEL_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_deterministic_normalization():
    """Test deterministic canonicalization of dates, areas, survey numbers, and addresses."""
    # 1. Survey numbers
    assert document_normalizer.normalize_survey_number(" 123 / 4 B ") == "123/4B"
    assert document_normalizer.normalize_survey_number("78-A / 2") == "78-A/2"

    # 2. Dates
    date_str, dt = document_normalizer.normalize_date("12th May 2026")
    assert date_str == "2026-05-12"
    assert dt is not None and dt.year == 2026 and dt.month == 5 and dt.day == 12

    date_str2, _ = document_normalizer.normalize_date("2026-09-24")
    assert date_str2 == "2026-09-24"

    # 3. Areas (sq.ft -> sq.m, sq.yards -> sq.m, acres -> sq.m)
    sqm, norm_str = document_normalizer.normalize_area("1,250 sq.ft")
    assert round(sqm, 2) == 116.13
    assert "116.13 sq.m" in norm_str

    sqm_yd, _ = document_normalizer.normalize_area("200 sq.yards")
    assert round(sqm_yd, 2) == 167.23

    # 4. Postal Code
    assert document_normalizer.normalize_postal_code("500 081") == "500081"


@pytest.mark.asyncio
async def test_structured_field_extraction_with_provenance():
    """Test structured regex extraction of cadastral identifiers with page number and evidence text."""
    extractor = RuleBasedFieldExtractor()

    sample_doc_text = """
    GOVERNMENT OF TELANGANA - REGISTRATION AND STAMPS DEPARTMENT
    Document No: DOC-7890/2026
    Date of Execution: 15/06/2026
    Office of the Sub-Registrar: Hyderabad Central

    SCHEDULE OF PROPERTY
    All that piece and parcel of land situated at Banjara Hills, Hyderabad - 500034.
    Parcel No: PCL-HYD-042
    Survey No: 120/3A
    Extent of Land: 1,500 sq.ft
    Bounded by:
    North by: 30 Feet Wide Road
    South by: Plot No 43
    East by: Survey No 120/4
    West by: Park Boundary
    """

    class MockPage:
        page_number = 1
        text = sample_doc_text

    fields = extractor.extract_fields(sample_doc_text, [MockPage()])
    field_map = {f.field_name: f for f in fields}

    assert "parcel_number" in field_map
    assert field_map["parcel_number"].field_value == "PCL-HYD-042"
    assert field_map["parcel_number"].normalized_value == "PCL-HYD-042"
    assert field_map["parcel_number"].page_number == 1
    assert "PCL-HYD-042" in (field_map["parcel_number"].evidence_text or "")

    assert "survey_number" in field_map
    assert field_map["survey_number"].normalized_value == "120/3A"

    assert "document_number" in field_map
    assert field_map["document_number"].field_value == "DOC-7890/2026"

    assert "document_date" in field_map
    assert field_map["document_date"].normalized_value == "2026-06-15"

    assert "land_area" in field_map
    assert "sq.m" in (field_map["land_area"].normalized_value or "")

    assert "north_boundary" in field_map
    assert "30 Feet Wide Road" in field_map["north_boundary"].field_value


@pytest.mark.asyncio
async def test_document_cadastral_candidate_matcher(db_session: AsyncSession):
    """Test matching extracted document identifiers against existing cadastral parcels."""
    org = Organization(name="Test Org", code=f"ORG-{uuid.uuid4().hex[:4]}")
    db_session.add(org)
    await db_session.flush()

    jur = Jurisdiction(
        organization_id=org.id,
        name="Test Ward",
        code=f"W-{uuid.uuid4().hex[:4]}",
        level="WARD",
    )
    db_session.add(jur)
    await db_session.flush()

    geom_wkt = "POLYGON((78.4800 17.3800, 78.4900 17.3800, 78.4900 17.3900, 78.4800 17.3900, 78.4800 17.3800))"
    parcel = Parcel(
        id=uuid.uuid4(),
        jurisdiction_id=jur.id,
        parcel_number="PCL-TEST-999",
        parcel_code="PARCEL-999",
        area=500.0,
        geometry=geom_wkt,
        geometry_wkt=geom_wkt,
    )
    db_session.add(parcel)
    await db_session.commit()

    doc_id = str(uuid.uuid4())
    extracted = {"parcel_number": "PCL-TEST-999"}

    candidates = await document_cadastral_matcher.find_candidate_links(
        db=db_session,
        document_id=doc_id,
        extracted_fields=extracted,
    )

    assert len(candidates) >= 1
    assert candidates[0].entity_type == "PARCEL"
    assert candidates[0].entity_id == str(parcel.id)
    assert candidates[0].match_score == 1.0
    assert candidates[0].status == "CANDIDATE"


@pytest.mark.asyncio
async def test_document_validation_rules_integration():
    """Verify Phase 8 document validation rules detecting area mismatches and reference discrepancies."""
    doc_id = str(uuid.uuid4())
    parcel_id = str(uuid.uuid4())

    geom_wkt = "POLYGON((78.4800 17.3800, 78.4900 17.3800, 78.4900 17.3900, 78.4800 17.3900, 78.4800 17.3800))"
    mock_parcel = Parcel(
        id=uuid.UUID(parcel_id),
        jurisdiction_id=uuid.uuid4(),
        parcel_number="PCL-OFFICIAL-100",
        parcel_code="OFFICIAL-100",
        area=100.0,
        geometry=geom_wkt,
        geometry_wkt=geom_wkt,
    )

    # Document declares 180 sq.m (deviation = 80% > tolerance 5%)
    mock_field_area = DocumentExtractedField(
        id=str(uuid.uuid4()),
        document_version_id="v1",
        field_name="land_area",
        field_value="180 sq.m",
        normalized_value="180.00 sq.m",
    )

    # Document declares parcel number PCL-DIFFERENT-999
    mock_field_parcel = DocumentExtractedField(
        id=str(uuid.uuid4()),
        document_version_id="v1",
        field_name="parcel_number",
        field_value="PCL-DIFFERENT-999",
        normalized_value="PCL-DIFFERENT-999",
    )

    mock_doc = PropertyDocument(
        id=doc_id,
        document_reference="DOC-TEST-001",
        document_type=DocumentType.SALE_DEED.value,
        title="Test Deed",
        parcel_id=parcel_id,
        current_version_id="v1",
        document_date=datetime.now(timezone.utc) + timedelta(days=30),  # Future date!
    )
    mock_doc.extracted_fields = [mock_field_area, mock_field_parcel]

    context = ValidationContext(
        target_type="DOCUMENT",
        target_id=doc_id,
        parcels=[mock_parcel],
        property_documents=[mock_doc],
    )

    # 1. Area mismatch rule
    area_rule = DocumentAreaMismatchRule()
    area_issues = area_rule.validate(context)
    assert len(area_issues) == 1
    assert area_issues[0].issue_code == "DOC-004"
    assert "deviates from GIS parcel geometry" in area_issues[0].message

    # 2. Parcel reference discrepancy rule
    parcel_rule = DocumentParcelReferenceMismatchRule()
    parcel_issues = parcel_rule.validate(context)
    assert len(parcel_issues) == 1
    assert parcel_issues[0].issue_code == "DOC-001"
    assert "PCL-DIFFERENT-999" in parcel_issues[0].message

    # 3. Future date inconsistency rule
    date_rule = DocumentDateInconsistencyRule()
    date_issues = date_rule.validate(context)
    assert len(date_issues) == 1
    assert date_issues[0].issue_code == "DOC-005"
    assert "future" in date_issues[0].message


@pytest.mark.asyncio
async def test_document_api_upload_review_and_verification_lifecycle(
    client: AsyncClient,
    auth_tokens: dict,
):
    """End-to-End API test: Upload document, review extracted fields, and verify document."""
    officer_headers = auth_tokens["officer"]
    citizen_headers = auth_tokens["citizen"]

    # 1. Upload a property document
    sample_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Title (Official Sale Deed) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    upload_files = {
        "file": ("official_deed.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")
    }
    upload_data = {
        "title": "Banjara Hills Deed 2026",
        "document_type": "SALE_DEED",
        "description": "Property deed registered with Sub-Registrar",
        "document_date": "2026-05-10",
        "issuing_authority": "Sub-Registrar Hyderabad Central",
    }

    resp = await client.post(
        "/api/v1/documents",
        data=upload_data,
        files=upload_files,
        headers=officer_headers,
    )
    assert resp.status_code == 201
    doc_res = resp.json()
    doc_id = doc_res["id"]
    assert doc_res["title"] == "Banjara Hills Deed 2026"
    assert doc_res["document_reference"].startswith("DOC-")

    # 2. List documents
    list_resp = await client.get("/api/v1/documents", headers=officer_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # 3. Get metrics
    metric_resp = await client.get("/api/v1/documents/metrics", headers=officer_headers)
    assert metric_resp.status_code == 200
    assert metric_resp.json()["total_documents"] >= 1

    # 4. Secure authenticated file download
    file_resp = await client.get(f"/api/v1/documents/{doc_id}/file", headers=officer_headers)
    assert file_resp.status_code == 200
    assert file_resp.content == sample_pdf_bytes

    # 5. Unauthorized verification test: Citizen cannot verify
    citizen_verify = await client.post(
        f"/api/v1/documents/{doc_id}/verify",
        json={"notes": "Illegal citizen approval attempt"},
        headers=citizen_headers,
    )
    assert citizen_verify.status_code == 403

    # 6. Officer verification: Succeeds and updates status to VERIFIED
    officer_verify = await client.post(
        f"/api/v1/documents/{doc_id}/verify",
        json={"notes": "Surveyor cross-checked boundary and deed matches cadastre."},
        headers=officer_headers,
    )
    assert officer_verify.status_code == 200
    assert officer_verify.json()["status"] == "VERIFIED"


@pytest.mark.asyncio
async def test_document_entity_link_api_lifecycle(
    client: AsyncClient,
    auth_tokens: dict,
):
    """Test manual and candidate entity linking between documents and cadastral parcels."""
    officer_headers = auth_tokens["officer"]

    # Create document
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload_files = {"file": ("title.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_data = {"title": "Title Link Test", "document_type": "TITLE_DOCUMENT"}

    doc_resp = await client.post(
        "/api/v1/documents",
        data=upload_data,
        files=upload_files,
        headers=officer_headers,
    )
    doc_id = doc_resp.json()["id"]

    # Link to parcel
    target_parcel_id = str(uuid.uuid4())
    link_resp = await client.post(
        f"/api/v1/documents/{doc_id}/links",
        json={"entity_type": "PARCEL", "entity_id": target_parcel_id, "link_method": "MANUAL"},
        headers=officer_headers,
    )
    assert link_resp.status_code == 201
    link_data = link_resp.json()
    assert link_data["entity_type"] == "PARCEL"
    assert link_data["entity_id"] == target_parcel_id

    # List links
    get_links = await client.get(f"/api/v1/documents/{doc_id}/links", headers=officer_headers)
    assert get_links.status_code == 200
    assert len(get_links.json()) == 1
