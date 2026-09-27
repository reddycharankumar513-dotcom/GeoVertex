export type UserRole =
  | 'CITIZEN'
  | 'SURVEYOR'
  | 'GOVERNMENT_OFFICER'
  | 'ADMIN'
  | 'URBAN_PLANNER';

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  phone?: string | null;
  role: UserRole;
  organization_id?: string | null;
  jurisdiction_id?: string | null;
  is_active: boolean;
  is_verified: boolean;
  last_login_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Organization {
  id: string;
  name: string;
  code: string;
  type: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Jurisdiction {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  level: string;
  srid: number;
  boundary_wkt?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuditEvent {
  id: string;
  actor_user_id?: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  timestamp: string;
  ip_address?: string | null;
  user_agent?: string | null;
  details: Record<string, any>;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  total_pages: number;
}

export interface Parcel {
  id: string;
  jurisdiction_id: string;
  parcel_number: string;
  parcel_code: string;
  survey_number?: string | null;
  subdivision_number?: string | null;
  land_use: string;
  area: number;
  area_unit: string;
  status: string;
  ownership_status: string;
  centroid_lon?: number | null;
  centroid_lat?: number | null;
  geometry_wkt?: string | null;
  source: string;
  source_reference?: string | null;
  created_at: string;
  updated_at: string;
  jurisdiction_name?: string;
  jurisdiction_code?: string;
  properties?: PropertySummary[];
  buildings?: BuildingSummary[];
}

export interface PropertySummary {
  id: string;
  property_reference: string;
  property_type: string;
  status: string;
  address: string;
}

export interface BuildingSummary {
  id: string;
  building_reference: string;
  building_type: string;
  status: string;
  area: number;
  height_estimate?: number | null;
}

export interface Property {
  id: string;
  parcel_id: string;
  property_reference: string;
  property_type: string;
  status: string;
  address: string;
  locality?: string | null;
  postal_code?: string | null;
  description?: string | null;
  parcel_number?: string;
  parcel_code?: string;
  jurisdiction_name?: string;
  jurisdiction_code?: string;
  created_at: string;
  updated_at: string;
}

export interface Building {
  id: string;
  parcel_id?: string | null;
  building_reference: string;
  building_type: string;
  status: string;
  area: number;
  height_estimate?: number | null;
  geometry_wkt?: string | null;
  source: string;
  source_reference?: string | null;
  parcel_number?: string;
  parcel_code?: string;
  created_at: string;
  updated_at: string;
}

export interface GeoJSONFeature {
  type: 'Feature';
  id?: string;
  geometry: {
    type: string;
    coordinates: any;
  };
  properties: Record<string, any>;
}

export interface GeoJSONFeatureCollection {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
  total_features?: number;
}

export interface IdentifiedFeature {
  id: string;
  type: 'PARCEL' | 'BUILDING' | 'JURISDICTION';
  identifier: string;
  title: string;
  status?: string;
  area?: number;
  distance_meters?: number;
  properties: Record<string, any>;
}

export interface SpatialIdentifyResponse {
  point: {
    longitude: number;
    latitude: number;
  };
  parcels: IdentifiedFeature[];
  buildings: IdentifiedFeature[];
  jurisdictions: IdentifiedFeature[];
}

export interface GeometryValidationResponse {
  valid: boolean;
  area_sq_m?: number;
  perimeter_m?: number;
  centroid?: [number, number];
  bbox?: [number, number, number, number];
  errors: { code: string; message: string }[];
  warnings: { code: string; message: string }[];
}

export interface GISImportSummary {
  records_received: number;
  records_accepted: number;
  records_rejected: number;
  entity_type: string;
  errors: { feature_index: number; code: string; message: string }[];
  warnings: string[];
  jurisdiction_id?: string;
}

// ============================================================================
// Phase 5: Survey Domain Interfaces
// ============================================================================

export interface SurveyProject {
  id: string;
  organization_id: string;
  jurisdiction_id: string;
  name: string;
  code: string;
  description?: string | null;
  status: 'DRAFT' | 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'CANCELLED';
  start_date?: string | null;
  end_date?: string | null;
  organization_name?: string;
  jurisdiction_name?: string;
  assignments_count?: number;
  active_assignments_count?: number;
  completed_assignments_count?: number;
  created_at: string;
  updated_at: string;
}

export interface SurveyAssignment {
  id: string;
  survey_project_id: string;
  surveyor_id: string;
  jurisdiction_id: string;
  parcel_id?: string | null;
  property_id?: string | null;
  building_id?: string | null;
  floor_id?: string | null;
  unit_id?: string | null;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  status:
    | 'ASSIGNED'
    | 'ACCEPTED'
    | 'IN_PROGRESS'
    | 'SUBMITTED'
    | 'UNDER_REVIEW'
    | 'REVISION_REQUIRED'
    | 'APPROVED'
    | 'REJECTED'
    | 'CANCELLED';
  assigned_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  due_at?: string | null;
  notes?: string | null;
  project_name?: string;
  project_code?: string;
  surveyor_name?: string;
  surveyor_email?: string;
  jurisdiction_name?: string;
  parcel_code?: string;
  property_reference?: string;
  building_reference?: string;
  floor_code?: string;
  unit_code?: string;
  sessions_count?: number;
  submissions_count?: number;
  created_at: string;
  updated_at: string;
}

export interface SurveySession {
  id: string;
  assignment_id: string;
  surveyor_id: string;
  started_at: string;
  ended_at?: string | null;
  status: 'DRAFT' | 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'SYNC_PENDING' | 'SYNCED' | 'SUBMITTED';
  device_identifier?: string | null;
  app_version?: string | null;
  sync_status: string;
  notes?: string | null;
  assignment?: SurveyAssignment;
  observations_count?: number;
  evidence_count?: number;
  created_at: string;
  updated_at: string;
}

export interface SurveyObservation {
  id: string;
  session_id: string;
  observation_type: string;
  target_type: string;
  target_id: string;
  value: string;
  unit?: string | null;
  notes?: string | null;
  captured_at: string;
  captured_by?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  horizontal_accuracy?: number | null;
  altitude?: number | null;
  vertical_accuracy?: number | null;
  source: string;
  geometry_wkt?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SurveyEvidence {
  id: string;
  session_id: string;
  observation_id?: string | null;
  target_type: string;
  target_id: string;
  filename: string;
  mime_type: string;
  file_size: number;
  evidence_type: string;
  captured_at: string;
  latitude?: number | null;
  longitude?: number | null;
  accuracy?: number | null;
  description?: string | null;
  sha256_hash: string;
  created_at: string;
  updated_at: string;
}

export interface SurveySubmission {
  id: string;
  assignment_id: string;
  survey_session_id: string;
  version_number: number;
  status: 'SUBMITTED' | 'UNDER_REVIEW' | 'APPROVED' | 'REVISION_REQUIRED' | 'REJECTED';
  snapshot_data: string;
  submitted_by: string;
  submitted_at: string;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  review_notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SurveyValidationIssue {
  code: string;
  severity: 'ERROR' | 'WARNING' | 'INFO';
  field?: string | null;
  message: string;
  details?: Record<string, any> | null;
}

export interface SurveyValidationSummary {
  is_valid: boolean;
  can_submit: boolean;
  total_errors: number;
  total_warnings: number;
  issues: SurveyValidationIssue[];
  checklist: Record<string, boolean>;
  comparisons: Array<{
    entity: string;
    property: string;
    official_value: string;
    survey_value: string;
    difference: string;
    status: string;
    message: string;
  }>;
}

export interface SyncOperationItem {
  client_operation_id: string;
  session_id?: string | null;
  operation_type: string;
  entity_type: string;
  entity_id: string;
  payload: Record<string, any>;
}

export interface SyncBatchResponse {
  results: Array<{
    client_operation_id: string;
    status: string;
    entity_id?: string | null;
    server_id?: string | null;
    error?: string | null;
  }>;
  total_processed: number;
  synced_count: number;
  conflict_count: number;
  failed_count: number;
}


