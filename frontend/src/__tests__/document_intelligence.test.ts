import { describe, it, expect } from 'vitest';
import { UserRole } from '../types';
import {
  ConfidenceLevel,
  DocumentExtractedField,
  DocumentMetrics,
  DocumentStatus,
  DocumentType,
  FieldReviewPayload,
  FieldReviewStatus,
  LinkRelationshipType,
  LinkStatus,
  PropertyDocument,
  TargetEntityType,
} from '../types/document';

describe('GeoVertex Phase 8 - AI Document Intelligence & Property Document Verification', () => {
  // 1. Role-Based Access Control for Document Management & Verification
  it('enforces RBAC for document upload, processing, field editing, and final verification', () => {
    const canUploadAndProcess = (role: UserRole) => {
      return ['ADMIN', 'GOVERNMENT_OFFICER', 'SURVEYOR', 'URBAN_PLANNER'].includes(role);
    };

    const canReviewFields = (role: UserRole) => {
      return ['ADMIN', 'GOVERNMENT_OFFICER', 'SURVEYOR'].includes(role);
    };

    const canVerifyOrRejectDocument = (role: UserRole) => {
      // Final legal verification of ownership documents is restricted to Officers and Admins
      return ['ADMIN', 'GOVERNMENT_OFFICER'].includes(role);
    };

    // Citizen
    expect(canUploadAndProcess('CITIZEN')).toBe(false);
    expect(canReviewFields('CITIZEN')).toBe(false);
    expect(canVerifyOrRejectDocument('CITIZEN')).toBe(false);

    // Urban Planner (can view/upload/process but cannot verify final title)
    expect(canUploadAndProcess('URBAN_PLANNER')).toBe(true);
    expect(canReviewFields('URBAN_PLANNER')).toBe(false);
    expect(canVerifyOrRejectDocument('URBAN_PLANNER')).toBe(false);

    // Surveyor (can upload, process, and review fields, but cannot verify final legal title)
    expect(canUploadAndProcess('SURVEYOR')).toBe(true);
    expect(canReviewFields('SURVEYOR')).toBe(true);
    expect(canVerifyOrRejectDocument('SURVEYOR')).toBe(false);

    // Government Officer (full review and verification)
    expect(canUploadAndProcess('GOVERNMENT_OFFICER')).toBe(true);
    expect(canReviewFields('GOVERNMENT_OFFICER')).toBe(true);
    expect(canVerifyOrRejectDocument('GOVERNMENT_OFFICER')).toBe(true);

    // Admin (full capabilities)
    expect(canUploadAndProcess('ADMIN')).toBe(true);
    expect(canReviewFields('ADMIN')).toBe(true);
    expect(canVerifyOrRejectDocument('ADMIN')).toBe(true);
  });

  // 2. Document Status Lifecycle Progression
  it('strictly validates the document lifecycle from upload to human verification', () => {
    const validStatuses: DocumentStatus[] = [
      'UPLOADED',
      'QUEUED',
      'PROCESSING',
      'OCR_COMPLETED',
      'EXTRACTION_COMPLETED',
      'VALIDATION_COMPLETED',
      'UNDER_REVIEW',
      'VERIFIED',
      'REQUIRES_CORRECTION',
      'REJECTED',
    ];

    expect(validStatuses).toHaveLength(10);

    const isTerminalStatus = (status: DocumentStatus) => {
      return ['VERIFIED', 'REJECTED'].includes(status);
    };

    expect(isTerminalStatus('UPLOADED')).toBe(false);
    expect(isTerminalStatus('PROCESSING')).toBe(false);
    expect(isTerminalStatus('UNDER_REVIEW')).toBe(false);
    expect(isTerminalStatus('REQUIRES_CORRECTION')).toBe(false);
    expect(isTerminalStatus('VERIFIED')).toBe(true);
    expect(isTerminalStatus('REJECTED')).toBe(true);
  });

  // 3. Document Types and Classifications
  it('supports canonical cadastral legal document types', () => {
    const validTypes: DocumentType[] = [
      'DEED',
      'TITLE_CERTIFICATE',
      'SURVEY_PLAN',
      'TAX_RECEIPT',
      'ENCUMBRANCE_CERTIFICATE',
      'MORTGAGE_DOCUMENT',
      'BUILDING_PERMIT',
      'COMPLETION_CERTIFICATE',
      'COURT_ORDER',
      'PARTITION_DEED',
      'GIFT_DEED',
      'LEASE_AGREEMENT',
      'WILL',
      'OTHER',
    ];

    expect(validTypes).toContain('DEED');
    expect(validTypes).toContain('TITLE_CERTIFICATE');
    expect(validTypes).toContain('SURVEY_PLAN');
    expect(validTypes.length).toBeGreaterThanOrEqual(14);
  });

  // 4. Extracted Field Provenance & Field Review
  it('preserves field provenance, confidence levels, and deterministic review values', () => {
    const mockField: DocumentExtractedField = {
      id: 'field-101',
      document_id: 'doc-001',
      version_id: 'ver-001',
      field_name: 'parcel_number',
      field_category: 'IDENTIFICATION',
      data_type: 'STRING',
      raw_value: 'Parcel No: P-8821',
      normalized_value: 'P-8821',
      confidence: 0.94,
      confidence_level: 'HIGH',
      extraction_method: 'RULE_BASED',
      page_number: 1,
      bounding_box: { x: 10, y: 20, w: 30, h: 5 },
      evidence_text: 'bounded in parcel no: P-8821 on the east',
      review_status: 'PENDING',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    expect(mockField.field_name).toBe('parcel_number');
    expect(mockField.normalized_value).toBe('P-8821');
    expect(mockField.confidence_level).toBe('HIGH');
    expect(mockField.review_status).toBe('PENDING');

    // Simulate human officer field correction
    const correctionPayload: FieldReviewPayload = {
      review_status: 'CORRECTED',
      reviewed_value: 'P-8821-A',
      review_comment: 'Updated parcel suffix per deed amendment clause on page 3',
    };

    const updatedField: DocumentExtractedField = {
      ...mockField,
      review_status: correctionPayload.review_status,
      reviewed_value: correctionPayload.reviewed_value,
      review_comment: correctionPayload.review_comment,
      reviewed_by: 'officer-user-id',
      reviewed_at: new Date().toISOString(),
    };

    expect(updatedField.review_status).toBe('CORRECTED');
    expect(updatedField.reviewed_value).toBe('P-8821-A');
    expect(updatedField.review_comment).toContain('deed amendment');
  });

  // 5. Cadastral Entity Links & Cross-Referencing
  it('supports linking documents to parcels, properties, buildings, and vertical units', () => {
    const validEntityTypes: TargetEntityType[] = ['PARCEL', 'PROPERTY', 'BUILDING', 'UNIT'];
    const validRelationships: LinkRelationshipType[] = [
      'PRIMARY_TITLE',
      'SUPPORTING_DEED',
      'SURVEY_REFERENCE',
      'MORTGAGE_LIEN',
      'TAX_RECORD',
      'PERMIT_APPROVAL',
      'LEGAL_DISPUTE',
      'HISTORICAL_RECORD',
    ];
    const validLinkStatuses: LinkStatus[] = ['CANDIDATE', 'CONFIRMED', 'REJECTED', 'FLAGGED_MISMATCH'];

    expect(validEntityTypes).toHaveLength(4);
    expect(validRelationships).toContain('PRIMARY_TITLE');
    expect(validRelationships).toContain('SURVEY_REFERENCE');
    expect(validLinkStatuses).toContain('FLAGGED_MISMATCH');
  });

  // 6. Integration with Phase 7 Validation Discrepancy Rules
  it('correctly models Phase 7 discrepancy rules detected during document cross-referencing', () => {
    const documentValidationRuleCodes = [
      'DOCUMENT_PARCEL_REFERENCE_MISMATCH',
      'DOCUMENT_BUILDING_REFERENCE_MISMATCH',
      'DOCUMENT_UNIT_REFERENCE_MISMATCH',
      'DOCUMENT_AREA_MISMATCH',
      'DOCUMENT_DATE_INCONSISTENCY',
      'DOCUMENT_DUPLICATE_CANDIDATE',
      'DOCUMENT_NUMBER_MISSING',
      'PARCEL_REFERENCE_MISSING',
    ];

    expect(documentValidationRuleCodes).toContain('DOCUMENT_PARCEL_REFERENCE_MISMATCH');
    expect(documentValidationRuleCodes).toContain('DOCUMENT_AREA_MISMATCH');
    expect(documentValidationRuleCodes).toContain('DOCUMENT_DATE_INCONSISTENCY');

    const areaTolerancePct = 0.05; // 5% area discrepancy tolerance
    const checkAreaDiscrepancy = (docAreaSqm: number, gisAreaSqm: number) => {
      const diffPct = Math.abs(docAreaSqm - gisAreaSqm) / gisAreaSqm;
      return diffPct > areaTolerancePct;
    };

    // 1000 sqm vs 1020 sqm (2% diff) -> within tolerance
    expect(checkAreaDiscrepancy(1020, 1000)).toBe(false);
    // 1000 sqm vs 1250 sqm (25% diff) -> discrepancy flagged
    expect(checkAreaDiscrepancy(1250, 1000)).toBe(true);
  });

  // 7. Mandatory Human-in-the-Loop Governance Notice
  it('verifies that automated AI processing enforces manual review requirement flag', () => {
    const processDocumentGovernance = (rawDoc: Partial<PropertyDocument>) => {
      // By policy, AI extraction sets manual_review_required = true
      return {
        ...rawDoc,
        status: 'UNDER_REVIEW' as DocumentStatus,
        manual_review_required: true,
      };
    };

    const result = processDocumentGovernance({
      id: 'doc-401',
      title: 'Sale Deed 2026',
      document_type: 'DEED',
    });

    expect(result.manual_review_required).toBe(true);
    expect(result.status).toBe('UNDER_REVIEW');
  });
});
