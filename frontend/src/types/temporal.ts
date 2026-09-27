export type SnapshotEntityType = 'PARCEL' | 'BUILDING' | 'FLOOR' | 'UNIT' | 'PROPERTY';

export type SnapshotType =
  | 'OFFICIAL_RECORD'
  | 'SURVEY'
  | 'REMOTE_SENSING'
  | 'AI_DERIVED'
  | 'DOCUMENT_DERIVED'
  | 'MANUAL';

export type DatePrecision = 'EXACT' | 'DAY' | 'MONTH' | 'YEAR' | 'UNKNOWN';

export type DetectionMethod =
  | 'GEOMETRY_DIFF'
  | 'ATTRIBUTE_DIFF'
  | 'IMAGE_AI'
  | 'SURVEY_COMPARISON'
  | 'DOCUMENT_COMPARISON'
  | 'COMPOSITE';

export type ChangeRunStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export type ChangeType =
  | 'BUILDING_ADDED'
  | 'BUILDING_REMOVED'
  | 'BUILDING_EXPANDED'
  | 'BUILDING_REDUCED'
  | 'BUILDING_GEOMETRY_CHANGED'
  | 'BUILDING_HEIGHT_CHANGED'
  | 'BUILDING_AREA_CHANGED'
  | 'BUILDING_COUNT_CHANGED'
  | 'FLOOR_ADDED'
  | 'FLOOR_REMOVED'
  | 'FLOOR_GEOMETRY_CHANGED'
  | 'FLOOR_COUNT_CHANGED'
  | 'UNIT_GEOMETRY_CHANGED'
  | 'PARCEL_GEOMETRY_CHANGED'
  | 'PARCEL_ATTRIBUTE_CHANGED'
  | 'PROPERTY_ATTRIBUTE_CHANGED'
  | 'SURVEY_DISCREPANCY'
  | 'DOCUMENT_RECORD_CHANGE'
  | 'UNKNOWN_CHANGE';

export type ChangeSignificance = 'MINOR' | 'MODERATE' | 'MAJOR' | 'UNKNOWN';

export type CandidateStatus = 'NEW' | 'UNDER_REVIEW' | 'CONFIRMED' | 'REJECTED' | 'DISMISSED';

export type ReviewReason =
  | 'CONFIRMED_FIELD_SURVEY'
  | 'CONFIRMED_PERMIT_APPROVED'
  | 'FALSE_POSITIVE'
  | 'TEMPORARY_STRUCTURE'
  | 'DATA_ALIGNMENT_ERROR'
  | 'SURVEY_CORRECTION'
  | 'DUPLICATE_DETECTION'
  | 'INSUFFICIENT_EVIDENCE'
  | 'OTHER';

export interface PropertySnapshot {
  id: string;
  entity_type: SnapshotEntityType;
  entity_id: string;
  snapshot_type: SnapshotType;
  effective_from: string;
  effective_to?: string | null;
  observation_date?: string | null;
  document_date?: string | null;
  date_precision: DatePrecision;
  source_type: string;
  source_id?: string | null;
  geometry_wkt?: string | null;
  attributes_json: Record<string, any>;
  version_number: number;
  is_current: boolean;
  created_at: string;
}

export interface ChangeMagnitude {
  baseline_area_sqm?: number;
  current_area_sqm?: number;
  area_difference_sqm?: number;
  area_change_percentage?: number;
  intersection_area_sqm?: number;
  union_area_sqm?: number;
  iou?: number;
  centroid_displacement_m?: number;
  boundary_displacement_m?: number;
  perimeter_baseline_m?: number;
  perimeter_current_m?: number;
  perimeter_difference_m?: number;
  height_difference_m?: number;
  floor_count_difference?: number;
  baseline_floor_count?: number;
  comparison_floor_count?: number;
  old_value?: any;
  new_value?: any;
  attribute_name?: string;
}

export interface ChangeCandidate {
  id: string;
  detection_run_id: string;
  change_type: ChangeType;
  entity_type: SnapshotEntityType;
  entity_id?: string | null;
  baseline_snapshot_id?: string | null;
  comparison_snapshot_id?: string | null;
  baseline_date?: string | null;
  comparison_date?: string | null;
  geometry_wkt?: string | null;
  baseline_geometry_wkt?: string | null;
  comparison_geometry_wkt?: string | null;
  magnitude: ChangeMagnitude;
  significance: ChangeSignificance;
  confidence?: number | null;
  evidence: Array<{
    source_type: string;
    source_id?: string;
    description?: string;
    date?: string;
    [key: string]: any;
  }>;
  validation_issues: Array<{
    rule_id: string;
    issue_code: string;
    severity: string;
    message: string;
    technical_explanation?: string;
  }>;
  status: CandidateStatus;
  review_reason?: ReviewReason | null;
  review_notes?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  created_at: string;
}

export interface ChangeDetectionRun {
  id: string;
  target_type: string;
  target_id?: string | null;
  jurisdiction_id?: string | null;
  baseline_reference: string;
  comparison_reference: string;
  detection_method: DetectionMethod;
  status: ChangeRunStatus;
  requested_by?: string | null;
  parameters: Record<string, any>;
  started_at?: string | null;
  completed_at?: string | null;
  ruleset_version: string;
  model_id?: string | null;
  summary: Record<string, any>;
  created_at: string;
}

export interface TemporalMetrics {
  total_runs: number;
  total_candidates: number;
  under_review: number;
  confirmed: number;
  rejected: number;
  dismissed: number;
  building_changes: number;
  floor_changes: number;
  parcel_changes: number;
}

export interface TimelineEntry {
  entry_id: string;
  entry_type: 'SNAPSHOT' | 'SURVEY' | 'DOCUMENT' | 'CHANGE_CANDIDATE';
  date?: string | null;
  date_precision: DatePrecision;
  source: string;
  title: string;
  description: string;
  attributes: Record<string, any>;
  geometry_wkt?: string | null;
  status?: string | null;
}

export interface ChangeCandidateReviewPayload {
  action: 'CONFIRM' | 'REJECT' | 'DISMISS';
  review_reason?: ReviewReason;
  review_notes?: string;
}

export interface ChangeRunCreatePayload {
  target_type: string;
  target_id?: string;
  baseline_reference: string;
  comparison_reference: string;
  detection_method?: DetectionMethod;
  parameters?: Record<string, any>;
}
