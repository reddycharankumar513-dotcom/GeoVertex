export type AIJobType =
  | 'BUILDING_EXTRACTION'
  | 'FLOOR_EXTRACTION'
  | 'HEIGHT_ESTIMATION'
  | 'PREPROCESSING'
  | 'POSTPROCESSING'
  | 'VALIDATION';

export type AIJobStatus =
  | 'QUEUED'
  | 'PREPROCESSING'
  | 'RUNNING'
  | 'POSTPROCESSING'
  | 'VALIDATING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export type AIResultStatus =
  | 'CANDIDATE'
  | 'VALIDATING'
  | 'REVIEW_REQUIRED'
  | 'APPROVED'
  | 'REJECTED';

export type AIValidationStatus = 'VALID' | 'INVALID' | 'WARNING';

export interface ConfidenceComponents {
  model_confidence: number;
  geometry_quality: number;
  source_quality: number;
}

export interface CadastralComparisonMetrics {
  iou: number;
  intersection_area_sqm: number;
  union_area_sqm: number;
  area_diff_sqm: number;
  area_diff_ratio: number;
  boundary_diff_m: number;
  official_area_sqm: number;
  candidate_area_sqm: number;
}

export interface AIJob {
  id: string;
  client_request_id?: string;
  job_type: AIJobType;
  status: AIJobStatus;
  stage: string;
  progress_pct: number;
  requested_by?: string;
  target_type: string;
  target_id: string;
  model_id: string;
  model_version: string;
  parameters: Record<string, any>;
  input_reference: Record<string, any>;
  started_at?: string;
  completed_at?: string;
  error_code?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface BuildingExtractionResult {
  id: string;
  job_id: string;
  source_target_id: string;
  geometry_wkt: string;
  geometry_geojson?: Record<string, any>;
  raw_geometry_wkt?: string;
  estimated_height?: number;
  confidence: number;
  confidence_components: ConfidenceComponents;
  cadastral_comparison: CadastralComparisonMetrics;
  evidence_linkage: Record<string, any>;
  model_id: string;
  model_version: string;
  status: AIResultStatus;
  validation_status: AIValidationStatus;
  validation_details: Record<string, any>;
  review_id?: string;
  created_at: string;
  updated_at: string;
}

export interface FloorExtractionResult {
  id: string;
  job_id: string;
  building_id: string;
  candidate_floor_number: number;
  floor_label: string;
  base_elevation: number;
  top_elevation: number;
  height: number;
  geometry_wkt?: string;
  geometry_geojson?: Record<string, any>;
  confidence: number;
  source: string;
  status: AIResultStatus;
  validation_details: Record<string, any>;
  review_id?: string;
  created_at: string;
  updated_at: string;
}

export interface AIReviewDecision {
  action: 'APPROVE' | 'REJECT' | 'MODIFY_AND_APPROVE' | 'REQUEST_REPROCESSING';
  edited_geometry_wkt?: string;
  notes?: string;
}

export interface AIModelVersion {
  id: string;
  model_id: string;
  version: string;
  weights_reference?: string;
  weights_hash?: string;
  configuration: Record<string, any>;
  metrics: Record<string, any>;
  is_active: boolean;
  created_at: string;
}

export interface AIModel {
  id: string;
  model_id: string;
  name: string;
  model_type: string;
  framework: string;
  description?: string;
  status: string;
  metadata_json: Record<string, any>;
  versions: AIModelVersion[];
  created_at: string;
}

export interface AIDataset {
  id: string;
  dataset_id: string;
  name: string;
  version: string;
  dataset_type: string;
  source: string;
  sample_count: number;
  label_schema: Record<string, any>;
  description?: string;
  created_at: string;
}
