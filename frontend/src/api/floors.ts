import { api } from './client';

export type FloorType = 'RESIDENTIAL' | 'COMMERCIAL' | 'MIXED_USE' | 'PARKING' | 'BASEMENT' | 'MECHANICAL' | 'ROOF' | 'OTHER';
export type FloorStatus = 'ACTIVE' | 'INACTIVE' | 'UNDER_CONSTRUCTION' | 'DEMOLISHED';

export interface FloorResponse {
  id: string;
  building_id: string;
  floor_number: number;
  floor_code: string;
  floor_name?: string | null;
  floor_type: FloorType;
  elevation_min_m: number;
  elevation_max_m: number;
  height_m: number;
  area_sqm?: number | null;
  status: FloorStatus;
  geometry_geojson?: any | null;
  created_at: string;
  updated_at: string;
}

export interface FloorCreate {
  building_id: string;
  floor_number: number;
  floor_code: string;
  floor_name?: string | null;
  floor_type?: FloorType;
  elevation_min_m: number;
  elevation_max_m: number;
  status?: FloorStatus;
  geometry?: string | null;
}

export interface FloorUpdate {
  floor_name?: string | null;
  floor_type?: FloorType;
  elevation_min_m?: number;
  elevation_max_m?: number;
  status?: FloorStatus;
  geometry?: string | null;
}

export const floorsApi = {
  list: (params: { building_id?: string; skip?: number; limit?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.building_id) query.append('building_id', params.building_id);
    if (params.skip !== undefined) query.append('skip', String(params.skip));
    if (params.limit !== undefined) query.append('limit', String(params.limit));
    const qs = query.toString();
    return api.get<FloorResponse[]>(`/floors${qs ? `?${qs}` : ''}`);
  },

  listByBuilding: (buildingId: string) => api.get<FloorResponse[]>(`/buildings/${buildingId}/floors`),

  get: (id: string) => api.get<FloorResponse>(`/floors/${id}`),

  create: (data: FloorCreate) => api.post<FloorResponse>('/floors', data),

  update: (id: string, data: FloorUpdate) => api.put<FloorResponse>(`/floors/${id}`, data),

  delete: (id: string) => api.delete<void>(`/floors/${id}`),
};
