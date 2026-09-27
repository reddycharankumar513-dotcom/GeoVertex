export type ValidationSeverity = 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';

export type ValidationIssueStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED' | 'WAIVED';

export type ValidationRunStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export type ValidationRunStage =
  | 'QUEUED'
  | 'PREPARING_DATA'
  | 'RUNNING_RULES'
  | 'GENERATING_ISSUES'
  | 'SUMMARIZING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export type ValidationCategory =
  | 'GEOMETRY'
  | 'PARCEL'
  | 'BUILDING'
  | 'FLOOR'
  | 'UNIT'
  | 'VERTICAL'
  | 'CROSS_DATASET'
  | 'AI'
  | 'SURVEY'
  | 'CRS';

export type ValidationTargetType =
  | 'PARCEL'
  | 'BUILDING'
  | 'FLOOR'
  | 'UNIT'
  | 'AI_RESULT'
  | 'SURVEY_SUBMISSION'
  | 'SURVEY_OBSERVATION'
  | 'JURISDICTION'
  | 'SYSTEM';

export interface ValidationRunSummary {
  total_issues: number;
  critical: number;
  errors: number;
  warnings: number;
  info: number;
  resolved: number;
  open: number;
  waived: number;
  acknowledged: number;
  rules_executed: number;
  entities_checked: number;
  execution_time_ms: number;
}

export interface ValidationRun {
  id: string;
  validation_type: string;
  target_type: ValidationTargetType;
  target_id?: string;
  status: ValidationRunStatus;
  stage: ValidationRunStage;
  requested_by?: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  ruleset_version: string;
  parameters: Record<string, any>;
  summary: ValidationRunSummary;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface ValidationIssue {
  id: string;
  validation_run_id: string;
  rule_id: string;
  rule_version: string;
  issue_code: string;
  category: ValidationCategory;
  severity: ValidationSeverity;
  status: ValidationIssueStatus;
  entity_type: string;
  entity_id: string;
  related_entity_type?: string;
  related_entity_id?: string;
  message: string;
  technical_explanation: string;
  geometry_wkt?: string;
  geometry_geojson?: any;
  measured_value?: string;
  expected_value?: string;
  tolerance?: string;
  metadata_json: Record<string, any>;
  created_at: string;
  acknowledged_at?: string;
  acknowledged_by?: string;
  resolved_at?: string;
  resolved_by?: string;
  resolution_note?: string;
  waived_at?: string;
  waived_by?: string;
  waiver_reason?: string;
}

export interface ValidationRule {
  rule_id: string;
  name: string;
  description: string;
  category: ValidationCategory;
  severity: ValidationSeverity;
  rule_version: string;
}

export interface EntityValidationSummary {
  entity_type: string;
  entity_id: string;
  latest_run_id?: string;
  status: 'VALID' | 'WARNING_ISSUES' | 'ERROR_ISSUES' | 'CRITICAL_ISSUES' | 'UNVALIDATED';
  total_issues: number;
  critical_issues: number;
  error_issues: number;
  warning_issues: number;
  info_issues: number;
  open_issues: number;
  resolved_issues: number;
  waived_issues: number;
  last_validated_at?: string;
}

export interface ValidationRunCreatePayload {
  target_type: ValidationTargetType;
  target_id?: string;
  validation_type?: string;
  rules_filter?: string[];
  tolerance_overrides?: Record<string, any>;
  geometry_wkt?: string;
}

export interface ValidationIssueActionPayload {
  action: 'ACKNOWLEDGE' | 'RESOLVE' | 'WAIVE';
  note?: string;
  reason?: string;
}
