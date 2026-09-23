import { api } from './client';

export interface CesiumExtrusionFeature {
  building_id: string;
  building_reference: string;
  building_type: string;
  status: string;
  parcel_id?: string;
  parcel_code?: string;
  footprint_area_sq_m: number;
  volume_cu_m: number;
  height: number;
  height_source: string;
  height_confidence?: number;
  height_unit: string;
  base_elevation: number;
  elevation_source: string;
  vertical_reference: string;
  extruded_height: number;
  centroid: [number, number, number];
  bbox_3d: [number, number, number, number, number, number];
  rings: {
    exterior: number[];
    holes: number[][];
  }[];
  floors_count?: number;
  units_count?: number;
}

export interface CesiumFloorFeature {
  floor_id: string;
  building_id: string;
  floor_number: number;
  floor_code: string;
  floor_name?: string | null;
  floor_type: string;
  base_elevation: number;
  elevation_min_m: number;
  elevation_max_m: number;
  height_m: number;
  area_sqm?: number | null;
  status: string;
  centroid: [number, number, number];
  bbox_3d: [number, number, number, number, number, number];
  rings: {
    exterior: number[];
    holes: number[][];
  }[];
}

export interface CesiumUnitFeature {
  unit_id: string;
  floor_id: string;
  property_id?: string | null;
  unit_number: string;
  unit_code: string;
  unit_type: string;
  use_category: string;
  base_elevation: number;
  elevation_min_m: number;
  elevation_max_m: number;
  height_m: number;
  gross_area_sqm: number;
  net_area_sqm?: number | null;
  status: string;
  ownership_status: string;
  centroid: [number, number, number];
  bbox_3d: [number, number, number, number, number, number];
  rings: {
    exterior: number[];
    holes: number[][];
  }[];
}

export interface SceneMetadata {
  crs: string;
  vertical_reference: string;
  center: [number, number, number];
  bounds: [number, number, number, number];
  jurisdiction_id?: string;
  camera_preset: {
    destination: [number, number, number];
    orientation: { heading: number; pitch: number; roll: number };
  };
}

export interface ThreeDSceneResponse {
  scene: SceneMetadata;
  buildings: CesiumExtrusionFeature[];
  parcels: any[];
  floors?: CesiumFloorFeature[];
  units?: CesiumUnitFeature[];
  metadata: {
    total_buildings: number;
    total_parcels: number;
    total_floors?: number;
    total_units?: number;
    representation_format: string;
    lod: string;
  };
}

export interface Building3DRepresentation {
  id: string;
  building_id: string;
  geometry_type: string;
  height: number;
  height_source: string;
  height_confidence?: number;
  height_unit: string;
  base_elevation: number;
  elevation_source: string;
  vertical_reference: string;
  model_source: string;
  model_version: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Building3DDetailResponse {
  building: {
    id: string;
    building_reference: string;
    building_type: string;
    status: string;
    area_sq_m: number;
    source?: string;
    created_at: string;
    updated_at: string;
  };
  representation_3d: Building3DRepresentation;
  parcel?: {
    id: string;
    parcel_number: string;
    parcel_code: string;
    land_use: string;
    status: string;
    area_sq_m: number;
  };
  properties: Array<{
    id: string;
    property_reference: string;
    property_type: string;
    address: string;
    status: string;
  }>;
  cesium_extrusion: CesiumExtrusionFeature;
  floors?: Array<{
    id: string;
    floor_number: number;
    floor_code: string;
    floor_name?: string | null;
    floor_type: string;
    elevation_min_m: number;
    elevation_max_m: number;
    height_m: number;
    area_sqm?: number | null;
    units: Array<{
      id: string;
      unit_number: string;
      unit_code: string;
      unit_type: string;
      gross_area_sqm: number;
      net_area_sqm?: number | null;
      status: string;
      ownership_status: string;
      property_id?: string | null;
    }>;
  }>;
}

export interface Parcel3DDetailResponse {
  parcel: {
    id: string;
    parcel_number: string;
    parcel_code: string;
    land_use: string;
    status: string;
    area_sq_m: number;
    centroid: [number, number, number];
    geometry: any;
  };
  buildings: CesiumExtrusionFeature[];
  properties: any[];
  camera_preset: {
    destination: [number, number, number];
    orientation: { heading: number; pitch: number; roll: number };
  };
}

export interface ThreeDIdentifyResponse {
  unit?: {
    id: string;
    unit_number: string;
    unit_code: string;
    unit_type: string;
    gross_area_sqm: number;
    net_area_sqm?: number | null;
    elevation_min_m: number;
    elevation_max_m: number;
    status: string;
    ownership_status: string;
  };
  floor?: {
    id: string;
    floor_number: number;
    floor_code: string;
    floor_name?: string | null;
    floor_type: string;
    elevation_min_m: number;
    elevation_max_m: number;
    height_m: number;
    area_sqm?: number | null;
    units_count: number;
  };
  building?: {
    id: string;
    building_reference: string;
    building_type: string;
    status: string;
    footprint_area_sq_m: number;
    height: number;
    height_source: string;
    height_unit: string;
    base_elevation: number;
    elevation_source: string;
    vertical_reference: string;
    extruded_height: number;
  };
  parcel?: {
    id: string;
    parcel_number: string;
    parcel_code: string;
    land_use: string;
    status: string;
    area_sq_m: number;
  };
  property?: {
    id: string;
    property_reference: string;
    property_type: string;
    address: string;
    status: string;
  };
  jurisdiction?: {
    id: string;
    name: string;
    code: string;
    level: string;
  };
}

export interface ThreeDAsset {
  id: string;
  building_id?: string;
  representation_id?: string;
  asset_type: string;
  storage_location: string;
  format: string;
  version: number;
  status: string;
  source: string;
  metadata_json?: string;
  created_at: string;
  updated_at: string;
}

export const threedApi = {
  getScene: (params: { bbox?: string; jurisdiction_id?: string; limit?: number } = {}) => {
    const queryParts = [];
    if (params.bbox) queryParts.push(`bbox=${encodeURIComponent(params.bbox)}`);
    if (params.jurisdiction_id) queryParts.push(`jurisdiction_id=${encodeURIComponent(params.jurisdiction_id)}`);
    if (params.limit) queryParts.push(`limit=${params.limit}`);
    const qs = queryParts.length ? `?${queryParts.join('&')}` : '';
    return api.get<ThreeDSceneResponse>(`/3d/scene${qs}`);
  },

  getBuilding: (id: string) => api.get<Building3DDetailResponse>(`/3d/buildings/${id}`),

  updateBuildingHeight: (
    id: string,
    data: {
      height: number;
      height_source?: string;
      height_confidence?: number;
      base_elevation?: number;
      elevation_source?: string;
      vertical_reference?: string;
    }
  ) => api.patch<Building3DRepresentation>(`/3d/buildings/${id}/height`, data),

  getParcel: (id: string) => api.get<Parcel3DDetailResponse>(`/3d/parcels/${id}`),

  identify: (params: { lon: number; lat: number; height?: number; radius?: number }) => {
    const queryParts = [`lon=${params.lon}`, `lat=${params.lat}`];
    if (params.height !== undefined) queryParts.push(`height=${params.height}`);
    if (params.radius !== undefined) queryParts.push(`radius=${params.radius}`);
    return api.get<ThreeDIdentifyResponse>(`/3d/identify?${queryParts.join('&')}`);
  },

  listAssets: (params: { building_id?: string; asset_type?: string; status?: string; page?: number; size?: number } = {}) => {
    const queryParts = [];
    if (params.building_id) queryParts.push(`building_id=${encodeURIComponent(params.building_id)}`);
    if (params.asset_type) queryParts.push(`asset_type=${encodeURIComponent(params.asset_type)}`);
    if (params.status) queryParts.push(`status=${encodeURIComponent(params.status)}`);
    if (params.page) queryParts.push(`page=${params.page}`);
    if (params.size) queryParts.push(`size=${params.size}`);
    const qs = queryParts.length ? `?${queryParts.join('&')}` : '';
    return api.get<ThreeDAsset[]>(`/3d/assets${qs}`);
  },

  createAsset: (data: Partial<ThreeDAsset>) => api.post<ThreeDAsset>('/3d/assets', data),

  deleteAsset: (id: string) => api.delete<void>(`/3d/assets/${id}`),
};
