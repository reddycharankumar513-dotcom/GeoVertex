import { api, ApiClientError } from './client';
import {
  PaginatedResult,
  SurveyAssignment,
  SurveyEvidence,
  SurveyObservation,
  SurveyProject,
  SurveySession,
  SurveySubmission,
  SurveyValidationSummary,
  SyncBatchResponse,
  SyncOperationItem,
} from '../types';

export const surveyApi = {
  // Projects
  async getProjects(params: {
    jurisdiction_id?: string;
    organization_id?: string;
    status?: string;
    page?: number;
    size?: number;
  } = {}): Promise<PaginatedResult<SurveyProject>> {
    const query = new URLSearchParams();
    if (params.jurisdiction_id) query.set('jurisdiction_id', params.jurisdiction_id);
    if (params.organization_id) query.set('organization_id', params.organization_id);
    if (params.status) query.set('status', params.status);
    if (params.page) query.set('page', params.page.toString());
    if (params.size) query.set('size', params.size.toString());
    const qs = query.toString();
    return api.get<PaginatedResult<SurveyProject>>(`/survey-projects${qs ? `?${qs}` : ''}`);
  },

  async getProject(id: string): Promise<SurveyProject> {
    return api.get<SurveyProject>(`/survey-projects/${id}`);
  },

  async createProject(data: {
    organization_id: string;
    jurisdiction_id: string;
    name: string;
    code: string;
    description?: string;
    status?: string;
  }): Promise<SurveyProject> {
    return api.post<SurveyProject>('/survey-projects', data);
  },

  async createAssignment(
    projectId: string,
    data: {
      surveyor_id: string;
      jurisdiction_id: string;
      parcel_id?: string;
      property_id?: string;
      building_id?: string;
      floor_id?: string;
      unit_id?: string;
      priority?: string;
      status?: string;
      due_at?: string;
      notes?: string;
    }
  ): Promise<SurveyAssignment> {
    return api.post<SurveyAssignment>(`/survey-projects/${projectId}/assignments`, data);
  },

  // Assignments
  async getAssignments(params: {
    surveyor_id?: string;
    survey_project_id?: string;
    jurisdiction_id?: string;
    status?: string;
    priority?: string;
    page?: number;
    size?: number;
  } = {}): Promise<PaginatedResult<SurveyAssignment>> {
    const query = new URLSearchParams();
    if (params.surveyor_id) query.set('surveyor_id', params.surveyor_id);
    if (params.survey_project_id) query.set('survey_project_id', params.survey_project_id);
    if (params.jurisdiction_id) query.set('jurisdiction_id', params.jurisdiction_id);
    if (params.status) query.set('status', params.status);
    if (params.priority) query.set('priority', params.priority);
    if (params.page) query.set('page', params.page.toString());
    if (params.size) query.set('size', params.size.toString());
    const qs = query.toString();
    return api.get<PaginatedResult<SurveyAssignment>>(`/survey-assignments${qs ? `?${qs}` : ''}`);
  },

  async getAssignment(id: string): Promise<SurveyAssignment> {
    return api.get<SurveyAssignment>(`/survey-assignments/${id}`);
  },

  async acceptAssignment(id: string): Promise<SurveyAssignment> {
    return api.post<SurveyAssignment>(`/survey-assignments/${id}/accept`);
  },

  async startSurvey(id: string): Promise<SurveySession> {
    return api.post<SurveySession>(`/survey-assignments/${id}/start`);
  },

  async exportAssignment(id: string): Promise<any> {
    return api.get<any>(`/survey-assignments/${id}/export`);
  },

  // Sessions
  async getSession(id: string): Promise<SurveySession> {
    return api.get<SurveySession>(`/survey-sessions/${id}`);
  },

  async pauseSession(id: string): Promise<SurveySession> {
    return api.post<SurveySession>(`/survey-sessions/${id}/pause`);
  },

  async resumeSession(id: string): Promise<SurveySession> {
    return api.post<SurveySession>(`/survey-sessions/${id}/resume`);
  },

  // Observations
  async getObservations(sessionId: string): Promise<SurveyObservation[]> {
    return api.get<SurveyObservation[]>(`/survey-sessions/${sessionId}/observations`);
  },

  async createObservation(
    sessionId: string,
    data: {
      observation_type: string;
      target_type: string;
      target_id: string;
      value: string;
      unit?: string;
      notes?: string;
      latitude?: number;
      longitude?: number;
      horizontal_accuracy?: number;
      altitude?: number;
      vertical_accuracy?: number;
      source?: string;
      geometry?: any;
    }
  ): Promise<SurveyObservation> {
    return api.post<SurveyObservation>(`/survey-sessions/${sessionId}/observations`, data);
  },

  // Evidence
  async getEvidence(sessionId: string): Promise<SurveyEvidence[]> {
    return api.get<SurveyEvidence[]>(`/survey-sessions/${sessionId}/evidence`);
  },

  async uploadEvidence(
    sessionId: string,
    formData: FormData
  ): Promise<SurveyEvidence> {
    const token = localStorage.getItem('geovertex_access_token');
    const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

    const response = await fetch(`/api/v1/survey-sessions/${sessionId}/evidence`, {
      method: 'POST',
      body: formData,
      headers,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new ApiClientError(response.status, err.error || { code: 'UPLOAD_FAILED', message: 'Failed to upload evidence' });
    }

    return response.json();
  },

  getEvidenceFileUrl(evidenceId: string): string {
    return `/api/v1/survey-evidence/${evidenceId}/file`;
  },

  // Validation & Submission
  async validateSession(sessionId: string): Promise<SurveyValidationSummary> {
    return api.post<SurveyValidationSummary>(`/survey-sessions/${sessionId}/validate`);
  },

  async submitSurvey(sessionId: string): Promise<SurveySubmission> {
    return api.post<SurveySubmission>(`/survey-sessions/${sessionId}/submit`);
  },

  // Submissions & Review
  async getSubmissions(params: {
    assignment_id?: string;
    status?: string;
    page?: number;
    size?: number;
  } = {}): Promise<PaginatedResult<SurveySubmission>> {
    const query = new URLSearchParams();
    if (params.assignment_id) query.set('assignment_id', params.assignment_id);
    if (params.status) query.set('status', params.status);
    if (params.page) query.set('page', params.page.toString());
    if (params.size) query.set('size', params.size.toString());
    const qs = query.toString();
    return api.get<PaginatedResult<SurveySubmission>>(`/survey-submissions${qs ? `?${qs}` : ''}`);
  },

  async getSubmission(id: string): Promise<SurveySubmission> {
    return api.get<SurveySubmission>(`/survey-submissions/${id}`);
  },

  async reviewSubmission(
    submissionId: string,
    action: 'approve' | 'request-revision' | 'reject',
    reviewNotes?: string
  ): Promise<SurveySubmission> {
    return api.post<SurveySubmission>(`/survey-submissions/${submissionId}/${action}`, {
      review_notes: reviewNotes,
    });
  },

  // Batch Sync
  async batchSync(operations: SyncOperationItem[]): Promise<SyncBatchResponse> {
    return api.post<SyncBatchResponse>('/sync/batch', { operations });
  },

  async getSyncStatus(): Promise<any> {
    return api.get<any>('/sync/status');
  },
};
