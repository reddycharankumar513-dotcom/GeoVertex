import { api } from './client';

export type UnitType = 'RESIDENTIAL' | 'COMMERCIAL' | 'RETAIL' | 'INDUSTRIAL' | 'OFFICE' | 'STORAGE' | 'PARKING_SPACE' | 'COMMON_AREA' | 'OTHER';
export type UnitUseCategory = 'APARTMENT' | 'OFFICE' | 'RETAIL_SHOP' | 'RESTAURANT' | 'WAREHOUSE' | 'CLINIC' | 'DATA_CENTER' | 'UTILITY' | 'OTHER';
export type UnitOwnershipStatus = 'OWNED' | 'LEASED' | 'VACANT' | 'MORTGAGED' | 'DISPUTED' | 'COMMON';
export type UnitStatus = 'ACTIVE' | 'INACTIVE' | 'UNDER_RENOVATION' | 'MERGED' | 'SPLIT';

export interface PropertyUnitResponse {
  id: string;
  floor_id: string;
  property_id?: string | null;
  unit_number: string;
  unit_code: string;
  unit_type: UnitType;
  use_category: UnitUseCategory;
  ownership_status: UnitOwnershipStatus;
  gross_area_sqm: number;
  net_area_sqm?: number | null;
  elevation_min_m: number;
  elevation_max_m: number;
  height_m: number;
  status: UnitStatus;
  geometry_geojson?: any | null;
  property_reference?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PropertyUnitCreate {
  floor_id: string;
  property_id?: string | null;
  unit_number: string;
  unit_code: string;
  unit_type?: UnitType;
  use_category?: UnitUseCategory;
  ownership_status?: UnitOwnershipStatus;
  gross_area_sqm: number;
  net_area_sqm?: number | null;
  elevation_min_m: number;
  elevation_max_m: number;
  status?: UnitStatus;
  geometry?: string | null;
}

export interface PropertyUnitUpdate {
  property_id?: string | null;
  unit_type?: UnitType;
  use_category?: UnitUseCategory;
  ownership_status?: UnitOwnershipStatus;
  gross_area_sqm?: number | null;
  net_area_sqm?: number | null;
  elevation_min_m?: number;
  elevation_max_m?: number;
  status?: UnitStatus;
  geometry?: string | null;
}

export const unitsApi = {
  list: (params: { floor_id?: string; property_id?: string; skip?: number; limit?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.floor_id) query.append('floor_id', params.floor_id);
    if (params.property_id) query.append('property_id', params.property_id);
    if (params.skip !== undefined) query.append('skip', String(params.skip));
    if (params.limit !== undefined) query.append('limit', String(params.limit));
    const qs = query.toString();
    return api.get<PropertyUnitResponse[]>(`/units${qs ? `?${qs}` : ''}`);
  },

  get: (id: string) => api.get<PropertyUnitResponse>(`/units/${id}`),

  create: (data: PropertyUnitCreate) => api.post<PropertyUnitResponse>('/units', data),

  update: (id: string, data: PropertyUnitUpdate) => api.put<PropertyUnitResponse>(`/units/${id}`, data),

  delete: (id: string) => api.delete<void>(`/units/${id}`),
};
