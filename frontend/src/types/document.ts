export type DocumentType =
  | 'DEED'
  | 'TITLE_CERTIFICATE'
  | 'SURVEY_PLAN'
  | 'TAX_RECEIPT'
  | 'ENCUMBRANCE_CERTIFICATE'
  | 'MORTGAGE_DOCUMENT'
  | 'BUILDING_PERMIT'
  | 'COMPLETION_CERTIFICATE'
  | 'COURT_ORDER'
  | 'PARTITION_DEED'
  | 'GIFT_DEED'
  | 'LEASE_AGREEMENT'
  | 'WILL'
  | 'OTHER';

export type DocumentStatus =
  | 'UPLOADED'
  | 'QUEUED'
  | 'PROCESSING'
  | 'OCR_COMPLETED'
  | 'EXTRACTION_COMPLETED'
  | 'VALIDATION_COMPLETED'
  | 'UNDER_REVIEW'
  | 'VERIFIED'
  | 'REQUIRES_CORRECTION'
  | 'REJECTED';

export type JobStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export type FieldReviewStatus = 'PENDING' | 'ACCEPTED' | 'CORRECTED' | 'REJECTED';

export type TargetEntityType = 'PARCEL' | 'PROPERTY' | 'BUILDING' | 'UNIT';

export type LinkRelationshipType =
  | 'PRIMARY_TITLE'
  | 'SUPPORTING_DEED'
  | 'SURVEY_REFERENCE'
  | 'MORTGAGE_LIEN'
  | 'TAX_RECORD'
  | 'PERMIT_APPROVAL'
  | 'LEGAL_DISPUTE'
  | 'HISTORICAL_RECORD';

export type LinkStatus = 'CANDIDATE' | 'CONFIRMED' | 'REJECTED' | 'FLAGGED_MISMATCH';

export type DiscrepancySeverity = 'CRITICAL' | 'WARNING' | 'INFO';

export interface DocumentVersion {
  id: string;
  document_id: string;
  version_number: number;
  file_name: string;
  file_path: string;
  file_size_bytes: number;
  file_hash_sha256: string;
  mime_type: string;
  total_pages: number;
  is_active: boolean;
  change_reason?: string | null;
  created_at: string;
}

export interface DocumentOCRResult {
  id: string;
  page_id: string;
  engine_name: string;
  engine_version?: string | null;
  status: string;
  extracted_text: string;
  character_count: number;
  average_confidence?: number | null;
  bounding_boxes?: any[] | null;
  error_message?: string | null;
  created_at: string;
}

export interface DocumentPage {
  id: string;
  document_id: string;
  version_id: string;
  page_number: number;
  width?: number | null;
  height?: number | null;
  image_path?: string | null;
  ocr_status: string;
  ocr_confidence?: number | null;
  created_at: string;
  ocr_results?: DocumentOCRResult[];
}

export interface DocumentExtractedField {
  id: string;
  document_id: string;
  version_id: string;
  field_name: string;
  field_category: string;
  data_type: string;
  raw_value: string;
  normalized_value?: string | null;
  confidence?: number | null;
  confidence_level: ConfidenceLevel;
  extraction_method: string;
  page_number?: number | null;
  bounding_box?: Record<string, any> | null;
  evidence_text?: string | null;
  model_id?: string | null;
  model_version?: string | null;
  review_status: FieldReviewStatus;
  reviewed_value?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  review_comment?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentEntityLink {
  id: string;
  document_id: string;
  entity_type: TargetEntityType;
  entity_id: string;
  relationship_type: LinkRelationshipType;
  match_confidence?: number | null;
  match_method: string;
  status: LinkStatus;
  validation_issues?: any[] | null;
  confirmed_by?: string | null;
  confirmed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentProcessingJob {
  id: string;
  document_id: string;
  job_type: string;
  status: JobStatus;
  celery_task_id?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  result_summary?: Record<string, any> | null;
  created_at: string;
}

export interface PropertyDocument {
  id: string;
  document_number?: string | null;
  document_type: DocumentType;
  status: DocumentStatus;
  title: string;
  jurisdiction_id: string;
  parcel_id?: string | null;
  property_id?: string | null;
  building_id?: string | null;
  unit_id?: string | null;
  issuing_authority?: string | null;
  document_date?: string | null;
  recording_date?: string | null;
  confidence_score?: number | null;
  classification_confidence?: number | null;
  ocr_engine_used?: string | null;
  manual_review_required: boolean;
  review_notes?: string | null;
  verified_by?: string | null;
  verified_at?: string | null;
  rejection_reason?: string | null;
  metadata_json?: Record<string, any> | null;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
  versions?: DocumentVersion[];
  pages?: DocumentPage[];
  extracted_fields?: DocumentExtractedField[];
  entity_links?: DocumentEntityLink[];
}

export interface DocumentMetrics {
  total_documents: number;
  verified_documents: number;
  under_review: number;
  rejected_documents: number;
  requires_correction: number;
  auto_matched_links: number;
  human_confirmed_links: number;
  ocr_success_rate: number;
  avg_extraction_confidence: number;
}

export interface DocumentUploadPayload {
  file: File;
  title: string;
  jurisdiction_id: string;
  document_type?: DocumentType;
  document_number?: string;
  parcel_id?: string;
  property_id?: string;
  building_id?: string;
  unit_id?: string;
}

export interface FieldReviewPayload {
  review_status: FieldReviewStatus;
  reviewed_value?: string;
  review_comment?: string;
}

export interface DocumentVerificationPayload {
  action: 'VERIFY' | 'REJECT' | 'REQUEST_CORRECTION';
  review_notes?: string;
  rejection_reason?: string;
}

export interface EntityLinkCreatePayload {
  entity_type: TargetEntityType;
  entity_id: string;
  relationship_type?: LinkRelationshipType;
  match_confidence?: number;
  match_method?: string;
}
