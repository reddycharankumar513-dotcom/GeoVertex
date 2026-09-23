import { api } from './client';
import {
  Building,
  GeoJSONFeatureCollection,
  GeometryValidationResponse,
  GISImportSummary,
  Jurisdiction,
  PaginatedResult,
  Parcel,
  Property,
  SpatialIdentifyResponse,
} from '../types';

export const gisApi = {
  // Parcels
  listParcels: (params: { query?: string; jurisdiction_id?: string; status?: string; page?: number; size?: number } = {}) => {
    const queryParts = [];
    if (params.query) queryParts.push(`query=${encodeURIComponent(params.query)}`);
    if (params.jurisdiction_id) queryParts.push(`jurisdiction_id=${encodeURIComponent(params.jurisdiction_id)}`);
    if (params.status) queryParts.push(`status=${encodeURIComponent(params.status)}`);
    if (params.page) queryParts.push(`page=${params.page}`);
    if (params.size) queryParts.push(`size=${params.size}`);
    const qs = queryParts.length ? `?${queryParts.join('&')}` : '';
    return api.get<PaginatedResult<Parcel>>(`/parcels${qs}`);
  },

  getParcel: (id: string) => api.get<Parcel>(`/parcels/${id}`),

  createParcel: (data: {
    jurisdiction_id: string;
    parcel_number: string;
    parcel_code: string;
    survey_number?: string;
    subdivision_number?: string;
    land_use?: string;
    geometry: any;
    source?: string;
  }) => api.post<Parcel>('/parcels', data),

  updateParcel: (id: string, data: Partial<Parcel> & { geometry?: any }) =>
    api.patch<Parcel>(`/parcels/${id}`, data),

  deleteParcel: (id: string) => api.delete<{ message: string; id: string }>(`/parcels/${id}`),

  // Properties
  listProperties: (params: { query?: string; parcel_id?: string; page?: number; size?: number } = {}) => {
    const queryParts = [];
    if (params.query) queryParts.push(`query=${encodeURIComponent(params.query)}`);
    if (params.parcel_id) queryParts.push(`parcel_id=${encodeURIComponent(params.parcel_id)}`);
    if (params.page) queryParts.push(`page=${params.page}`);
    if (params.size) queryParts.push(`size=${params.size}`);
    const qs = queryParts.length ? `?${queryParts.join('&')}` : '';
    return api.get<PaginatedResult<Property>>(`/properties${qs}`);
  },

  getProperty: (id: string) => api.get<Property>(`/properties/${id}`),

  createProperty: (data: {
    parcel_id: string;
    property_reference: string;
    property_type?: string;
    address: string;
    locality?: string;
    postal_code?: string;
    description?: string;
  }) => api.post<Property>('/properties', data),

  // Buildings
  listBuildings: (params: { query?: string; parcel_id?: string; page?: number; size?: number } = {}) => {
    const queryParts = [];
    if (params.query) queryParts.push(`query=${encodeURIComponent(params.query)}`);
    if (params.parcel_id) queryParts.push(`parcel_id=${encodeURIComponent(params.parcel_id)}`);
    if (params.page) queryParts.push(`page=${params.page}`);
    if (params.size) queryParts.push(`size=${params.size}`);
    const qs = queryParts.length ? `?${queryParts.join('&')}` : '';
    return api.get<PaginatedResult<Building>>(`/buildings${qs}`);
  },

  getBuilding: (id: string) => api.get<Building>(`/buildings/${id}`),

  createBuilding: (data: {
    parcel_id?: string;
    building_reference: string;
    building_type?: string;
    height_estimate?: number;
    geometry: any;
  }) => api.post<Building>('/buildings', data),

  // Map Feature Endpoints
  getMapParcels: (bbox?: string, jurisdiction_id?: string) => {
    const queryParts = [];
    if (bbox) queryParts.push(`bbox=${encodeURIComponent(bbox)}`);
    if (jurisdiction_id) queryParts.push(`jurisdiction_id=${encodeURIComponent(jurisdiction_id)}`);
    const qs = queryParts.length ? `?${queryParts.join('&')}` : '';
    return api.get<GeoJSONFeatureCollection>(`/map/parcels${qs}`);
  },

  getMapBuildings: (bbox?: string, parcel_id?: string) => {
    const queryParts = [];
    if (bbox) queryParts.push(`bbox=${encodeURIComponent(bbox)}`);
    if (parcel_id) queryParts.push(`parcel_id=${encodeURIComponent(parcel_id)}`);
    const qs = queryParts.length ? `?${queryParts.join('&')}` : '';
    return api.get<GeoJSONFeatureCollection>(`/map/buildings${qs}`);
  },

  getMapBoundaries: (jurisdiction_id?: string) => {
    const qs = jurisdiction_id ? `?jurisdiction_id=${encodeURIComponent(jurisdiction_id)}` : '';
    return api.get<GeoJSONFeatureCollection>(`/map/boundaries${qs}`);
  },

  // Spatial Analysis
  identify: (lon: number, lat: number, radiusMeters: number = 30) =>
    api.get<SpatialIdentifyResponse>(
      `/spatial/identify?longitude=${lon}&latitude=${lat}&radius_meters=${radiusMeters}`
    ),

  validateGeometry: (geometry: any, expected_type: string = 'POLYGON') =>
    api.post<GeometryValidationResponse>('/spatial/validate', {
      geometry,
      expected_type,
    }),

  checkOverlap: (geometry: any, jurisdiction_id?: string) =>
    api.post<{ has_conflicts: boolean; conflicts: any[] }>('/spatial/check-overlap', {
      geometry,
      jurisdiction_id,
    }),

  // GIS Import & Export
  importGeoJSON: (jurisdiction_id: string, payload: any) =>
    api.post<GISImportSummary>(`/gis/import?jurisdiction_id=${encodeURIComponent(jurisdiction_id)}`, payload),

  exportGeoJSON: (jurisdiction_id?: string, status?: string) => {
    const queryParts = [];
    if (jurisdiction_id) queryParts.push(`jurisdiction_id=${encodeURIComponent(jurisdiction_id)}`);
    if (status) queryParts.push(`status=${encodeURIComponent(status)}`);
    const qs = queryParts.length ? `?${queryParts.join('&')}` : '';
    return api.get<GeoJSONFeatureCollection>(`/gis/export${qs}`);
  },

  // Jurisdictions
  listJurisdictions: () => api.get<PaginatedResult<Jurisdiction>>('/jurisdictions?size=100'),
};
