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

