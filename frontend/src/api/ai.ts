import { apiClient } from './client';
import {
  AIJob,
  BuildingExtractionResult,
  FloorExtractionResult,
  AIModel,
  AIDataset,
  AIReviewDecision,
} from '../types/ai';

export interface AIJobCreateParams {
  client_request_id?: string;
  job_type?: string;
  target_type: string;
  target_id: string;
  model_id?: string;
  model_version?: string;
  parameters?: Record<string, any>;
  survey_evidence_ids?: string[];
}

export const aiApi = {
  // Jobs
  createJob: async (params: AIJobCreateParams): Promise<AIJob> => {
    return apiClient.request<AIJob>('/ai/jobs', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  listJobs: async (params: {
    status?: string;
    job_type?: string;
    target_type?: string;
    target_id?: string;
    page?: number;
    size?: number;
  } = {}): Promise<{ items: AIJob[]; total: number; page: number; size: number }> => {
    const query = new URLSearchParams();
    if (params.status) query.set('status', params.status);
    if (params.job_type) query.set('job_type', params.job_type);
    if (params.target_type) query.set('target_type', params.target_type);
    if (params.target_id) query.set('target_id', params.target_id);
    if (params.page) query.set('page', params.page.toString());
    if (params.size) query.set('size', params.size.toString());

    return apiClient.request<{ items: AIJob[]; total: number; page: number; size: number }>(
      `/ai/jobs?${query.toString()}`
    );
  },

  getJob: async (jobId: string): Promise<AIJob> => {
    return apiClient.request<AIJob>(`/ai/jobs/${jobId}`);
  },

  cancelJob: async (jobId: string): Promise<AIJob> => {
    return apiClient.request<AIJob>(`/ai/jobs/${jobId}/cancel`, {
      method: 'POST',
    });
  },

  // Building Extraction Results
  listBuildingResults: async (params: {
    target_id?: string;
    status?: string;
    model_id?: string;
    page?: number;
    size?: number;
  } = {}): Promise<{ items: BuildingExtractionResult[]; total: number; page: number; size: number }> => {
    const query = new URLSearchParams();
    if (params.target_id) query.set('target_id', params.target_id);
    if (params.status) query.set('status', params.status);
    if (params.model_id) query.set('model_id', params.model_id);
    if (params.page) query.set('page', params.page.toString());
    if (params.size) query.set('size', params.size.toString());

    return apiClient.request<{ items: BuildingExtractionResult[]; total: number; page: number; size: number }>(
      `/ai/building-results?${query.toString()}`
    );
  },

  getBuildingResult: async (resultId: string): Promise<BuildingExtractionResult> => {
    return apiClient.request<BuildingExtractionResult>(`/ai/building-results/${resultId}`);
  },

  // Floor Extraction Results
  listFloorResults: async (params: {
    building_id?: string;
    status?: string;
  } = {}): Promise<FloorExtractionResult[]> => {
    const query = new URLSearchParams();
    if (params.building_id) query.set('building_id', params.building_id);
    if (params.status) query.set('status', params.status);

    return apiClient.request<FloorExtractionResult[]>(`/ai/floor-results?${query.toString()}`);
  },

  // Validation & Review
  validateResult: async (resultId: string): Promise<Record<string, any>> => {
    return apiClient.request<Record<string, any>>(`/ai/results/${resultId}/validate`, {
      method: 'POST',
    });
  },

  approveResult: async (resultId: string, notes?: string): Promise<any> => {
    const query = notes ? `?notes=${encodeURIComponent(notes)}` : '';
    return apiClient.request(`/ai/results/${resultId}/approve${query}`, {
      method: 'POST',
    });
  },

  rejectResult: async (resultId: string, notes: string): Promise<any> => {
    return apiClient.request(`/ai/results/${resultId}/reject?notes=${encodeURIComponent(notes)}`, {
      method: 'POST',
    });
  },

  modifyAndApproveResult: async (resultId: string, decision: AIReviewDecision): Promise<any> => {
    return apiClient.request(`/ai/results/${resultId}/modify`, {
      method: 'POST',
      body: JSON.stringify(decision),
    });
  },

  requestReprocessing: async (resultId: string, notes?: string): Promise<any> => {
    const query = notes ? `?notes=${encodeURIComponent(notes)}` : '';
    return apiClient.request(`/ai/results/${resultId}/request-reprocessing${query}`, {
      method: 'POST',
    });
  },

  // Models & Datasets
  listModels: async (): Promise<AIModel[]> => {
    return apiClient.request<AIModel[]>('/ai/models');
  },

  listDatasets: async (): Promise<AIDataset[]> => {
    return apiClient.request<AIDataset[]>('/ai/datasets');
  },
};
