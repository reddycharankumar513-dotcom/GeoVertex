// Phase 12 — Technical 3D Property Identifier Engine: TypeScript types
// DISCLAIMER: GeoVertex Technical 3D Identifiers are NOT official ULPINs or legal ownership identifiers.

export type IdentifierEntityType = 'JURISDICTION' | 'PARCEL' | 'BUILDING' | 'FLOOR' | 'UNIT';
export type IdentifierType = 'JURISDICTION_ID' | 'PARCEL_ID' | 'BUILDING_ID' | 'FLOOR_ID' | 'UNIT_ID' | 'PROPERTY_3D_ID';
export type IdentifierStatus = 'DRAFT' | 'ACTIVE' | 'SUSPENDED' | 'SUPERSEDED' | 'RETIRED' | 'REVOKED';
export type LineageRelationship = 'SPLIT' | 'MERGE' | 'CORRECTION' | 'MIGRATION' | 'REPLACEMENT';
export type JobStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export interface IdentifierScheme {
  id: string;
  scheme_code: string;
  name: string;
  version: number;
  description?: string;
  prefix: string;
  separator: string;
  jurisdiction_component: string;
  parcel_component: string;
  building_component: string;
  floor_component: string;
  unit_component: string;
  padding_rules: Record<string, unknown>;
  checksum_enabled: boolean;
  active: boolean;
  effective_from?: string;
  effective_to?: string;
  created_at: string;
  updated_at: string;
}

export interface IdentifierHierarchy {
  jurisdiction_id?: string;
  jurisdiction_component?: string;
  parcel_id?: string;
  parcel_component?: string;
  building_id?: string;
  building_component?: string;
  floor_id?: string;
  floor_component?: string;
  unit_id?: string;
  unit_component?: string;
}

export interface PropertyIdentifier {
  id: string;
  identifier_value: string;
  identifier_type: IdentifierType;
  scheme_id: string;
  scheme_code?: string;
  entity_type: IdentifierEntityType;
  entity_id: string;
  status: IdentifierStatus;
  version: number;
  issued_at?: string;
  issued_by?: string;
  supersedes_identifier_id?: string;
  superseded_by_identifier_id?: string;
  verification_token?: string;
  hierarchy?: IdentifierHierarchy;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface PreviewResult {
  eligible: boolean;
  already_assigned: boolean;
  collision: boolean;
  preview_identifier?: string;
  scheme_code?: string;
  components: Record<string, string | null>;
  hierarchy: Record<string, string | null>;
  errors: string[];
}

export interface VerificationResult {
  valid: boolean;
  identifier_value?: string;
  identifier_type?: string;
  status?: string;
  entity_type?: string;
  scheme_code?: string;
  issued_at?: string;
  hierarchy?: IdentifierHierarchy;
  verification_message: string;
  disclaimer: string;
}

export interface IdentifierLineage {
  id: string;
  source_identifier_id: string;
  target_identifier_id: string;
  relationship_type: LineageRelationship;
  reason?: string;
  effective_date?: string;
  created_by?: string;
  created_at: string;
}

export interface IdentifierJob {
  id: string;
  scheme_id: string;
  scope: Record<string, unknown>;
  requested_by?: string;
  status: JobStatus;
  total: number;
  eligible: number;
  generated: number;
  blocked: number;
  conflicts: number;
  skipped: number;
  started_at?: string;
  completed_at?: string;
  error?: string;
  created_at: string;
  updated_at: string;
}

export interface IdentifierStatistics {
  total: number;
  by_status: Record<string, number>;
  by_entity_type: Record<string, number>;
  active: number;
  superseded: number;
  retired: number;
  revoked: number;
  draft: number;
}

export interface BulkPreview {
  scope: Record<string, unknown>;
  total: number;
  already_assigned: number;
  eligible: number;
  blocked: number;
  collisions: number;
  ready_to_generate: number;
  previews: Array<{
    unit_id: string;
    unit_code: string;
    eligible: boolean;
    already_assigned: boolean;
    collision: boolean;
    preview_identifier?: string;
    errors: string[];
  }>;
}

export interface SupersedeResponse {
  old_identifier: PropertyIdentifier;
  new_identifier: PropertyIdentifier;
  message: string;
}

export interface PaginatedIdentifiers {
  items: PropertyIdentifier[];
  total: number;
  page: number;
  size: number;
  total_pages: number;
}
