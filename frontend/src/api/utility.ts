import { apiClient } from './client';
import {
  Utility3DFeature,
  UtilityAsset,
  UtilityClash,
  UtilityClashReviewPayload,
  UtilityInspection,
  UtilityMaintenanceEvent,
  UtilityMetrics,
  UtilityNetwork,
  UtilityNetworkCreatePayload,
  UtilityNode,
  UtilityReviewPayload,
  UtilitySegment,
} from '../types/utility';

export const utilityApi = {
  // Networks
  createNetwork: async (payload: UtilityNetworkCreatePayload): Promise<UtilityNetwork> => {
    return apiClient.request<UtilityNetwork>('/utilities/networks', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  listNetworks: async (params: {
    jurisdiction_id?: string;
    utility_type?: string;
    status?: string;
    skip?: number;
    limit?: number;
  } = {}): Promise<UtilityNetwork[]> => {
    const query = new URLSearchParams();
    if (params.jurisdiction_id) query.set('jurisdiction_id', params.jurisdiction_id);
    if (params.utility_type) query.set('utility_type', params.utility_type);
    if (params.status) query.set('status', params.status);
    if (params.skip !== undefined) query.set('skip', params.skip.toString());
    if (params.limit !== undefined) query.set('limit', params.limit.toString());
    return apiClient.request<UtilityNetwork[]>(`/utilities/networks?${query.toString()}`);
  },

  getNetwork: async (id: string): Promise<UtilityNetwork> => {
    return apiClient.request<UtilityNetwork>(`/utilities/networks/${id}`);
  },

  getNetworkTopology: async (id: string): Promise<any> => {
    return apiClient.request<any>(`/utilities/networks/${id}/topology`);
  },

  // Assets
  createAsset: async (payload: any): Promise<UtilityAsset> => {
    return apiClient.request<UtilityAsset>('/utilities/assets', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  listAssets: async (params: {
    network_id?: string;
    asset_type?: string;
    status?: string;
    review_status?: string;
    parcel_id?: string;
    building_id?: string;
    min_depth?: number;
    max_depth?: number;
    confidence?: string;
    skip?: number;
    limit?: number;
  } = {}): Promise<UtilityAsset[]> => {
    const query = new URLSearchParams();
    if (params.network_id) query.set('network_id', params.network_id);
    if (params.asset_type) query.set('asset_type', params.asset_type);
    if (params.status) query.set('status', params.status);
    if (params.review_status) query.set('review_status', params.review_status);
    if (params.parcel_id) query.set('parcel_id', params.parcel_id);
    if (params.building_id) query.set('building_id', params.building_id);
    if (params.min_depth !== undefined) query.set('min_depth', params.min_depth.toString());
    if (params.max_depth !== undefined) query.set('max_depth', params.max_depth.toString());
    if (params.confidence) query.set('confidence', params.confidence);
    if (params.skip !== undefined) query.set('skip', params.skip.toString());
    if (params.limit !== undefined) query.set('limit', params.limit.toString());
    return apiClient.request<UtilityAsset[]>(`/utilities/assets?${query.toString()}`);
  },

  getAssetDetails: async (id: string): Promise<any> => {
    return apiClient.request<any>(`/utilities/assets/${id}`);
  },

  reviewCandidate: async (id: string, payload: UtilityReviewPayload): Promise<UtilityAsset> => {
    return apiClient.request<UtilityAsset>(`/utilities/assets/${id}/verify`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  controlledUpdate: async (id: string, payload: { reason: string; source_reference: string; updates: any }): Promise<UtilityAsset> => {
    return apiClient.request<UtilityAsset>(`/utilities/assets/${id}/controlled-update`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Clashes
  runClashDetection: async (params: { jurisdiction_id?: string; network_id?: string } = {}): Promise<UtilityClash[]> => {
    const query = new URLSearchParams();
    if (params.jurisdiction_id) query.set('jurisdiction_id', params.jurisdiction_id);
    if (params.network_id) query.set('network_id', params.network_id);
    return apiClient.request<UtilityClash[]>(`/utilities/clashes/detect?${query.toString()}`, {
      method: 'POST',
    });
  },

  listClashes: async (params: {
    status?: string;
    severity?: string;
    asset_id?: string;
    skip?: number;
    limit?: number;
  } = {}): Promise<UtilityClash[]> => {
    const query = new URLSearchParams();
    if (params.status) query.set('status', params.status);
    if (params.severity) query.set('severity', params.severity);
    if (params.asset_id) query.set('asset_id', params.asset_id);
    if (params.skip !== undefined) query.set('skip', params.skip.toString());
    if (params.limit !== undefined) query.set('limit', params.limit.toString());
    return apiClient.request<UtilityClash[]>(`/utilities/clashes?${query.toString()}`);
  },

  reviewClash: async (id: string, payload: UtilityClashReviewPayload): Promise<UtilityClash> => {
    return apiClient.request<UtilityClash>(`/utilities/clashes/${id}/review`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // 2D & 3D Spatial
  getMapGeoJSON: async (bounds: { min_lon: number; min_lat: number; max_lon: number; max_lat: number; utility_type?: string }): Promise<any> => {
    const query = new URLSearchParams({
      min_lon: bounds.min_lon.toString(),
      min_lat: bounds.min_lat.toString(),
      max_lon: bounds.max_lon.toString(),
      max_lat: bounds.max_lat.toString(),
    });
    if (bounds.utility_type) query.set('utility_type', bounds.utility_type);
    return apiClient.request<any>(`/utilities/map?${query.toString()}`);
  },

  get3DScene: async (params: { network_id?: string; utility_type?: string } = {}): Promise<{ total_features: number; features: Utility3DFeature[] }> => {
    const query = new URLSearchParams();
    if (params.network_id) query.set('network_id', params.network_id);
    if (params.utility_type) query.set('utility_type', params.utility_type);
    return apiClient.request<{ total_features: number; features: Utility3DFeature[] }>(`/utilities/3d?${query.toString()}`);
  },

  // Metrics
  getMetrics: async (jurisdiction_id?: string): Promise<UtilityMetrics> => {
    const query = new URLSearchParams();
    if (jurisdiction_id) query.set('jurisdiction_id', jurisdiction_id);
    return apiClient.request<UtilityMetrics>(`/utilities/metrics?${query.toString()}`);
  },
};
