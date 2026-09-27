/**
 * Phase 13 — Audit, Versioning, Notifications & Governance Types.
 */

export type VersionStatus = 'CURRENT' | 'SUPERSEDED' | 'RETIRED' | 'REVOKED' | 'ARCHIVED' | 'DRAFT';

export type VersionChangeType =
  | 'CREATE'
  | 'UPDATE'
  | 'GEOMETRY_UPDATE'
  | 'STATUS_CHANGE'
  | 'APPROVAL'
  | 'REJECTION'
  | 'REVISION'
  | 'SUPERSESSION'
  | 'RETIREMENT'
  | 'REVOCATION'
  | 'RESTORATION'
  | 'MERGE'
  | 'SPLIT'
  | 'IMPORT'
  | 'EXPORT'
  | 'AI_PROPOSAL'
  | 'SURVEY_UPDATE'
  | 'DOCUMENT_UPDATE'
  | 'VALIDATION_UPDATE'
  | 'IDENTIFIER_ISSUED'
  | 'IDENTIFIER_REPLACED'
  | 'UTILITY_UPDATE';

export type VersionSourceType =
  | 'MANUAL'
  | 'SURVEY'
  | 'AI'
  | 'DOCUMENT'
  | 'GIS_IMPORT'
  | 'SYSTEM'
  | 'WORKFLOW'
  | 'ADMIN'
  | 'EXTERNAL_INTEGRATION';

export interface EntityVersion {
  id: string;
  entity_type: string;
  entity_id: string;
  version_number: number;
  version_uuid: string;
  version_status: VersionStatus;
  created_by?: string;
  effective_from: string;
  effective_to?: string;
  change_type: VersionChangeType;
  change_reason?: string;
  source_type: VersionSourceType;
  source_id?: string;
  parent_version_id?: string;
  supersedes_version_id?: string;
  superseded_by_version_id?: string;
  snapshot_data: Record<string, any>;
  geometry_wkt?: string;
  geometry_srid?: number;
  geometry_type?: string;
  geometry_hash?: string;
  content_hash?: string;
  geometry_metrics: {
    area?: number;
    length?: number;
    geom_type?: string;
    is_valid?: boolean;
    centroid?: { x: number; y: number };
    bounding_box?: { min_x: number; min_y: number; max_x: number; max_y: number };
    [key: string]: any;
  };
  workflow_id?: string;
  case_id?: string;
  correlation_id?: string;
  created_at: string;
}

export interface VersionComparison {
  version_a: {
    id: string;
    version_number: number;
    version_status: string;
    change_type: string;
    source_type: string;
    created_at?: string;
    created_by?: string;
  };
  version_b: {
    id: string;
    version_number: number;
    version_status: string;
    change_type: string;
    source_type: string;
    created_at?: string;
    created_by?: string;
  };
  modified_fields: Record<string, { before: any; after: any }>;
  added_fields: Record<string, any>;
  removed_fields: Record<string, any>;
  unchanged_fields_count: number;
  geometry_diff: {
    has_geometry_a: boolean;
    has_geometry_b: boolean;
    geometry_hash_a?: string;
    geometry_hash_b?: string;
    geometry_changed: boolean;
    area_before: number;
    area_after: number;
    area_delta: number;
    area_pct_change: number;
    perimeter_before: number;
    perimeter_after: number;
    perimeter_delta: number;
    centroid_movement_units: number;
    iou_overlap?: number;
    bbox_before?: any;
    bbox_after?: any;
  };
  disclaimer: string;
}

export interface RestoreVersionRequest {
  target_version_number: number;
  reason: string;
  workflow_id?: string;
  case_id?: string;
}

export interface EntityLineage {
  id: string;
  source_entity_type: string;
  source_entity_id: string;
  source_version_id?: string;
  target_entity_type: string;
  target_entity_id: string;
  target_version_id?: string;
  relationship_type: string;
  reason?: string;
  actor_user_id?: string;
  workflow_id?: string;
  created_at: string;
  metadata_json: Record<string, any>;
}

export interface AuditEventItem {
  id: string;
  event_id?: string;
  timestamp: string;
  action: string;
  category: string;
  severity: string;
  result: string;
  entity_type: string;
  entity_id: string;
  entity_version_id?: string;
  actor_user_id?: string;
  actor_role?: string;
  organization_id?: string;
  jurisdiction_id?: string;
  request_id?: string;
  correlation_id?: string;
  workflow_id?: string;
  case_id?: string;
  source_type?: string;
  source_id?: string;
  reason?: string;
  before_snapshot: Record<string, any>;
  after_snapshot: Record<string, any>;
  changed_fields: string[];
  geometry_changed: boolean;
  ip_address?: string;
  user_agent?: string;
  details: Record<string, any>;
}

export interface AuditStatistics {
  total_events: number;
  by_category: Record<string, number>;
  by_severity: Record<string, number>;
  by_result: Record<string, number>;
  distinct_actors: number;
}

export interface NotificationItem {
  id: string;
  user_id: string;
  notification_type: string;
  title: string;
  message: string;
  related_entity_type?: string;
  related_entity_id?: string;
  delivery_channel: string;
  status: string;
  severity: string;
  organization_id?: string;
  jurisdiction_id?: string;
  workflow_id?: string;
  case_id?: string;
  correlation_id?: string;
  sent_at?: string;
  read_at?: string;
  failure_reason?: string;
  created_at: string;
}

export interface NotificationPreferenceItem {
  id: string;
  user_id: string;
  notification_type: string;
  channel: string;
  enabled: boolean;
  digest_frequency: string;
}

export interface GovernanceDashboard {
  audit: AuditStatistics;
  versioning: {
    total_versions: number;
    versioned_entities: number;
    by_status: Record<string, number>;
  };
  notifications: {
    by_status: Record<string, number>;
    total: number;
  };
  recent_events: Array<{
    id: string;
    timestamp?: string;
    action: string;
    category: string;
    severity: string;
    entity_type: string;
    entity_id: string;
    actor_user_id?: string;
    result: string;
  }>;
}

export interface DataIntegrityReport {
  status: 'HEALTHY' | 'ISSUES_FOUND';
  issues_count: number;
  issues: string[];
  disclaimer: string;
}
