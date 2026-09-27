import { apiClient } from './client';
import {
  EntityValidationSummary,
  ValidationIssue,
  ValidationIssueActionPayload,
  ValidationRule,
  ValidationRun,
  ValidationRunCreatePayload,
} from '../types/validation';

export const validationApi = {
  // Validation Runs
  createRun: async (payload: ValidationRunCreatePayload): Promise<ValidationRun> => {
    return apiClient.request<ValidationRun>('/validation/runs', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  listRuns: async (params: {
    status?: string;
    validation_type?: string;
    target_type?: string;
    target_id?: string;
    skip?: number;
    limit?: number;
  } = {}): Promise<ValidationRun[]> => {
    const query = new URLSearchParams();
    if (params.status) query.set('status', params.status);
    if (params.validation_type) query.set('validation_type', params.validation_type);
    if (params.target_type) query.set('target_type', params.target_type);
    if (params.target_id) query.set('target_id', params.target_id);
    if (params.skip !== undefined) query.set('skip', params.skip.toString());
    if (params.limit !== undefined) query.set('limit', params.limit.toString());

    return apiClient.request<ValidationRun[]>(`/validation/runs?${query.toString()}`);
  },

  getRun: async (runId: string): Promise<ValidationRun> => {
    return apiClient.request<ValidationRun>(`/validation/runs/${runId}`);
  },

  getRunIssues: async (
    runId: string,
    params: { severity?: string; status?: string; category?: string } = {}
  ): Promise<ValidationIssue[]> => {
    const query = new URLSearchParams();
    if (params.severity) query.set('severity', params.severity);
    if (params.status) query.set('status', params.status);
    if (params.category) query.set('category', params.category);

    return apiClient.request<ValidationIssue[]>(`/validation/runs/${runId}/issues?${query.toString()}`);
  },

  cancelRun: async (runId: string): Promise<ValidationRun> => {
    return apiClient.request<ValidationRun>(`/validation/runs/${runId}/cancel`, {
      method: 'POST',
    });
  },

  // Issues
  listIssues: async (params: {
    run_id?: string;
    severity?: string;
    status?: string;
    category?: string;
    rule_id?: string;
    entity_type?: string;
    entity_id?: string;
    skip?: number;
    limit?: number;
  } = {}): Promise<ValidationIssue[]> => {
    const query = new URLSearchParams();
    if (params.run_id) query.set('run_id', params.run_id);
    if (params.severity) query.set('severity', params.severity);
    if (params.status) query.set('status', params.status);
    if (params.category) query.set('category', params.category);
    if (params.rule_id) query.set('rule_id', params.rule_id);
    if (params.entity_type) query.set('entity_type', params.entity_type);
    if (params.entity_id) query.set('entity_id', params.entity_id);
    if (params.skip !== undefined) query.set('skip', params.skip.toString());
    if (params.limit !== undefined) query.set('limit', params.limit.toString());

    return apiClient.request<ValidationIssue[]>(`/validation/issues?${query.toString()}`);
  },

  getIssue: async (issueId: string): Promise<ValidationIssue> => {
    return apiClient.request<ValidationIssue>(`/validation/issues/${issueId}`);
  },

  reviewIssue: async (issueId: string, payload: ValidationIssueActionPayload): Promise<ValidationIssue> => {
    return apiClient.request<ValidationIssue>(`/validation/issues/${issueId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  // Entity-Level Targeted Validation
  validateEntity: async (entityType: string, entityId: string): Promise<ValidationRun> => {
    return apiClient.request<ValidationRun>(`/validation/entities/${entityType}/${entityId}`, {
      method: 'POST',
    });
  },

  getEntityValidationSummary: async (entityType: string, entityId: string): Promise<EntityValidationSummary> => {
    return apiClient.request<EntityValidationSummary>(`/validation/entities/${entityType}/${entityId}/summary`);
  },

  // Rules
  listRules: async (category?: string, targetType?: string): Promise<ValidationRule[]> => {
    const query = new URLSearchParams();
    if (category) query.set('category', category);
    if (targetType) query.set('target_type', targetType);

    return apiClient.request<ValidationRule[]>(`/validation/rules?${query.toString()}`);
  },

  getRule: async (ruleId: string): Promise<ValidationRule> => {
    return apiClient.request<ValidationRule>(`/validation/rules/${ruleId}`);
  },
};
