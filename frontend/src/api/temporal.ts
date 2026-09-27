import { apiClient } from './client';
import {
  CandidateStatus,
  ChangeCandidate,
  ChangeCandidateReviewPayload,
  ChangeDetectionRun,
  ChangeRunCreatePayload,
  ChangeSignificance,
  ChangeType,
  PropertySnapshot,
  SnapshotEntityType,
  TemporalMetrics,
  TimelineEntry,
} from '../types/temporal';

export const temporalApi = {
  // Snapshots
  createSnapshot: async (payload: any): Promise<PropertySnapshot> => {
    return apiClient.request<PropertySnapshot>('/change-detection/snapshots', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  listSnapshots: async (params: {
    entity_type?: SnapshotEntityType;
    entity_id?: string;
    is_current?: boolean;
    skip?: number;
    limit?: number;
  } = {}): Promise<PropertySnapshot[]> => {
    const query = new URLSearchParams();
    if (params.entity_type) query.set('entity_type', params.entity_type);
    if (params.entity_id) query.set('entity_id', params.entity_id);
    if (params.is_current !== undefined) query.set('is_current', params.is_current.toString());
    if (params.skip !== undefined) query.set('skip', params.skip.toString());
    if (params.limit !== undefined) query.set('limit', params.limit.toString());

    return apiClient.request<PropertySnapshot[]>(`/change-detection/snapshots?${query.toString()}`);
  },

  // Runs
  dispatchRun: async (payload: ChangeRunCreatePayload): Promise<ChangeDetectionRun> => {
    return apiClient.request<ChangeDetectionRun>('/change-detection/runs', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  createRun: async (payload: ChangeRunCreatePayload): Promise<ChangeDetectionRun> => {
    return apiClient.request<ChangeDetectionRun>('/change-detection/runs', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  listRuns: async (params: {
    target_type?: string;
    status?: string;
    detection_method?: string;
    skip?: number;
    limit?: number;
  } = {}): Promise<ChangeDetectionRun[]> => {
    const query = new URLSearchParams();
    if (params.target_type) query.set('target_type', params.target_type);
    if (params.status) query.set('status', params.status);
    if (params.detection_method) query.set('detection_method', params.detection_method);
    if (params.skip !== undefined) query.set('skip', params.skip.toString());
    if (params.limit !== undefined) query.set('limit', params.limit.toString());

    return apiClient.request<ChangeDetectionRun[]>(`/change-detection/runs?${query.toString()}`);
  },

  getRun: async (runId: string): Promise<ChangeDetectionRun> => {
    return apiClient.request<ChangeDetectionRun>(`/change-detection/runs/${runId}`);
  },

  cancelRun: async (runId: string): Promise<ChangeDetectionRun> => {
    return apiClient.request<ChangeDetectionRun>(`/change-detection/runs/${runId}/cancel`, {
      method: 'POST',
    });
  },

  getRunChanges: async (runId: string): Promise<ChangeCandidate[]> => {
    return apiClient.request<ChangeCandidate[]>(`/change-detection/runs/${runId}/changes`);
  },

  // Candidates & Reviews
  listCandidates: async (params: {
    detection_run_id?: string;
    entity_type?: string;
    entity_id?: string;
    change_type?: ChangeType;
    status?: CandidateStatus;
    significance?: ChangeSignificance;
    skip?: number;
    limit?: number;
  } = {}): Promise<ChangeCandidate[]> => {
    const query = new URLSearchParams();
    if (params.detection_run_id) query.set('detection_run_id', params.detection_run_id);
    if (params.entity_type) query.set('entity_type', params.entity_type);
    if (params.entity_id) query.set('entity_id', params.entity_id);
    if (params.change_type) query.set('change_type', params.change_type);
    if (params.status) query.set('status', params.status);
    if (params.significance) query.set('significance', params.significance);
    if (params.skip !== undefined) query.set('skip', params.skip.toString());
    if (params.limit !== undefined) query.set('limit', params.limit.toString());

    return apiClient.request<ChangeCandidate[]>(`/change-detection/changes?${query.toString()}`);
  },

  getCandidate: async (candidateId: string): Promise<ChangeCandidate> => {
    return apiClient.request<ChangeCandidate>(`/change-detection/changes/${candidateId}`);
  },

  confirmCandidate: async (
    candidateId: string,
    payload: ChangeCandidateReviewPayload
  ): Promise<ChangeCandidate> => {
    return apiClient.request<ChangeCandidate>(`/change-detection/changes/${candidateId}/confirm`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  rejectCandidate: async (
    candidateId: string,
    payload: ChangeCandidateReviewPayload
  ): Promise<ChangeCandidate> => {
    return apiClient.request<ChangeCandidate>(`/change-detection/changes/${candidateId}/reject`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  dismissCandidate: async (
    candidateId: string,
    payload: ChangeCandidateReviewPayload
  ): Promise<ChangeCandidate> => {
    return apiClient.request<ChangeCandidate>(`/change-detection/changes/${candidateId}/dismiss`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  reviewCandidate: async (
    candidateId: string,
    payload: ChangeCandidateReviewPayload
  ): Promise<ChangeCandidate> => {
    if (payload.action === 'CONFIRM') {
      return temporalApi.confirmCandidate(candidateId, payload);
    } else if (payload.action === 'REJECT') {
      return temporalApi.rejectCandidate(candidateId, payload);
    } else {
      return temporalApi.dismissCandidate(candidateId, payload);
    }
  },

  // Timeline
  getEntityTimeline: async (entityType: string, entityId: string): Promise<TimelineEntry[]> => {
    return apiClient.request<TimelineEntry[]>(`/change-detection/entities/${entityType}/${entityId}/timeline`);
  },

  // Metrics
  getMetrics: async (): Promise<TemporalMetrics> => {
    return apiClient.request<TemporalMetrics>('/change-detection/metrics');
  },
};
