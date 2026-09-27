export type UtilityType =
  | 'WATER'
  | 'SEWER'
  | 'STORMWATER'
  | 'GAS'
  | 'ELECTRICITY'
  | 'TELECOM'
  | 'FIBER'
  | 'DRAINAGE'
  | 'OTHER';

export type UtilityAssetType =
  | 'PIPE'
  | 'CABLE'
  | 'DUCT'
  | 'CONDUIT'
  | 'MANHOLE'
  | 'VALVE'
  | 'METER'
  | 'TRANSFORMER'
  | 'POLE_BASE'
  | 'CHAMBER'
  | 'HANDHOLE'
  | 'DRAIN'
  | 'CULVERT'
  | 'PUMP'
  | 'TANK'
  | 'UTILITY_STRUCTURE'
  | 'OTHER';

export type UtilityStatus =
  | 'PLANNED'
  | 'PROPOSED'
  | 'UNDER_CONSTRUCTION'
  | 'ACTIVE'
  | 'INACTIVE'
  | 'ABANDONED'
  | 'REMOVED'
  | 'UNKNOWN';

export type UtilityReviewStatus =
  | 'CANDIDATE'
  | 'VALIDATED'
  | 'UNDER_REVIEW'
  | 'VERIFIED'
  | 'REJECTED'
  | 'REVISION_REQUIRED';

export type AssetReviewStatus = UtilityReviewStatus;

export type QualityLevel = 'QL-A' | 'QL-B' | 'QL-C' | 'QL-D';

export type ElevationReference =
  | 'GROUND_RELATIVE'
  | 'LOCAL_MSL'
  | 'WGS84_ELLIPSOID'
  | 'EGM96_GEOID';

export type UtilitySourceType =
  | 'OFFICIAL_RECORD'
  | 'SURVEY'
  | 'DOCUMENT'
  | 'AI_CANDIDATE'
  | 'MANUAL'
  | 'REMOTE_SENSING'
  | 'OTHER';

export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN';

export type ClashSeverity = 'CRITICAL' | 'ERROR' | 'WARNING' | 'INFO' | 'MAJOR' | 'MODERATE';

export type ClashStatus =
  | 'OPEN'
  | 'DETECTED'
  | 'ACKNOWLEDGED'
  | 'RESOLVED'
  | 'WAIVED'
  | 'FALSE_POSITIVE';

export type ClashType =
  | 'DIRECT_PHYSICAL'
  | 'HORIZONTAL_CLEARANCE'
  | 'VERTICAL_CLEARANCE'
  | 'ENVELOPE_INTERSECTION';

export interface UtilityNetwork {
  id: string;
  name: string;
  utility_type: UtilityType;
  owner_organization?: string | null;
  operator_organization?: string | null;
  owner?: string | null;
  operator?: string | null;
  jurisdiction_id: string;
  status: UtilityStatus;
  coordinate_system?: string;
  vertical_datum?: string;
  source: string;
  metadata_json: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface UtilityAsset {
  id: string;
  network_id: string;
  asset_type: UtilityAssetType;
  asset_reference: string;
  status: UtilityStatus;
  review_status: UtilityReviewStatus;
  geometry_type: string;
  geometry_wkt?: string | null;
  elevation_reference: ElevationReference;
  depth?: number | null;
  depth_min?: number | null;
  depth_max?: number | null;
  ground_elevation?: number | null;
  centerline_elevation?: number | null;
  depth_m?: number | null;
  elevation_m?: number | null;
  material?: string | null;
  diameter?: number | null;
  diameter_mm?: number | null;
  width?: number | null;
  capacity?: string | null;
  quality_level?: QualityLevel | string;
  installation_date?: string | null;
  commissioning_date?: string | null;
  source_type: UtilitySourceType;
  source_reference?: string | null;
  confidence: ConfidenceLevel;
  parcel_id?: string | null;
  building_id?: string | null;
  metadata_json: Record<string, any>;
  network?: UtilityNetwork;
  created_at: string;
  updated_at: string;
}

export interface UtilitySegment {
  id: string;
  utility_asset_id: string;
  start_node_id?: string | null;
  end_node_id?: string | null;
  geometry_wkt?: string | null;
  length_meters: number;
  depth_start?: number | null;
  depth_end?: number | null;
  elevation_start?: number | null;
  elevation_end?: number | null;
  slope_percentage?: number | null;
  flow_direction: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface UtilityNode {
  id: string;
  network_id: string;
  node_type: string;
  asset_reference: string;
  geometry_wkt?: string | null;
  elevation?: number | null;
  depth?: number | null;
  status: string;
  source: string;
  metadata_json: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface UtilityClash {
  id: string;
  asset_a_id: string;
  asset_b_id: string;
  asset_1_id?: string;
  asset_2_id?: string;
  clash_type?: ClashType | string;
  horizontal_relationship?: string;
  vertical_relationship?: string;
  measured_horizontal_separation_m?: number;
  measured_vertical_separation_m?: number;
  required_horizontal_separation_m?: number;
  required_vertical_separation_m?: number;
  distance_m?: number;
  clearance_distance_m?: number;
  required_clearance_m?: number;
  rule_id?: string;
  rule_code?: string;
  clash_geometry_wkt?: string | null;
  severity: ClashSeverity;
  status: ClashStatus;
  resolution_notes?: string | null;
  resolved_by?: string | null;
  resolved_at?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface UtilityInspection {
  id: string;
  utility_asset_id: string;
  inspection_date: string;
  inspector_id?: string | null;
  condition: string;
  depth_measurement?: number | null;
  observations?: string | null;
  evidence_references: Array<Record<string, any>>;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface UtilityMaintenanceEvent {
  id: string;
  utility_asset_id: string;
  event_type: string;
  event_date: string;
  description: string;
  evidence_references: Array<Record<string, any>>;
  performed_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface UtilityMetrics {
  total_networks: number;
  total_assets: number;
  active_assets: number;
  candidates_requiring_review: number;
  verified_assets: number;
  total_clashes: number;
  open_clashes: number;
  unknown_depth_assets: number;
  low_confidence_assets: number;
  by_review_status?: Record<string, number>;
  unresolved_clashes?: number;
  assets_with_unknown_depth?: number;
}

export interface Utility3DFeature {
  id?: string;
  asset_id: string;
  asset_reference: string;
  network_id: string;
  utility_type: string;
  asset_type: string;
  feature_type?: string;
  geometry_type: string;
  coordinates: any[];
  depth?: number | null;
  ground_elevation?: number | null;
  centerline_elevation?: number | null;
  centerline_elevation_m?: number | null;
  depth_m?: number | null;
  diameter_m: number;
  diameter_mm?: number | null;
  material?: string | null;
  status: string;
  color_hex: string;
}

export interface UtilityReviewPayload {
  action: 'VERIFY' | 'REJECT' | 'REVISION_REQUIRED';
  review_notes: string;
}

export interface UtilityClashReviewPayload {
  action?: 'ACKNOWLEDGE' | 'RESOLVE' | 'WAIVE' | 'FALSE_POSITIVE';
  status?: ClashStatus;
  resolution_notes?: string;
}

export interface UtilityNetworkCreatePayload {
  name: string;
  utility_type: UtilityType;
  jurisdiction_id?: string;
  owner_organization?: string;
  operator_organization?: string;
  owner?: string;
  operator?: string;
  coordinate_system?: string;
  vertical_datum?: string;
  status?: UtilityStatus;
  source?: string;
}
