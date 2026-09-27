import { apiClient } from './client';
import {
  CaseAssignmentPayload,
  CaseEscalationPayload,
  CaseMessage,
  CaseMessageCreatePayload,
  CitizenDashboardMetrics,
  CitizenProperty,
  ControlledPropertyUpdatePayload,
  CrossPhaseCaseWorkspace,
  GovernmentDashboardMetrics,
  Notification,
  ServiceRequest,
  ServiceRequestCreatePayload,
  ServiceRequestDetail,
  ServiceType,
  SurveyCommissionPayload,
  TransitionPayload,
  WorkflowTask,
} from '../types/workflow';

export const workflowApi = {
  // Service Types
  listServiceTypes: async (citizen_visible_only: boolean = false): Promise<ServiceType[]> => {
    const query = new URLSearchParams();
    if (citizen_visible_only) query.set('citizen_visible_only', 'true');
    return apiClient.request<ServiceType[]>(`/workflows/service-types?${query.toString()}`);
  },

  getServiceType: async (code: string): Promise<ServiceType> => {
    return apiClient.request<ServiceType>(`/workflows/service-types/${code}`);
  },

  createServiceType: async (payload: Partial<ServiceType>): Promise<ServiceType> => {
    return apiClient.request<ServiceType>('/workflows/service-types', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Service Requests
  createServiceRequest: async (payload: ServiceRequestCreatePayload): Promise<ServiceRequest> => {
    return apiClient.request<ServiceRequest>('/workflows/service-requests', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  listServiceRequests: async (params: {
    status?: string;
    request_type?: string;
    priority?: string;
    jurisdiction_id?: string;
    search?: string;
    skip?: number;
    limit?: number;
  } = {}): Promise<{ items: ServiceRequest[]; total: number; skip: number; limit: number }> => {
    const query = new URLSearchParams();
    if (params.status) query.set('status', params.status);
    if (params.request_type) query.set('request_type', params.request_type);
    if (params.priority) query.set('priority', params.priority);
    if (params.jurisdiction_id) query.set('jurisdiction_id', params.jurisdiction_id);
    if (params.search) query.set('search', params.search);
    if (params.skip !== undefined) query.set('skip', params.skip.toString());
    if (params.limit !== undefined) query.set('limit', params.limit.toString());
    return apiClient.request<{ items: ServiceRequest[]; total: number; skip: number; limit: number }>(
      `/workflows/service-requests?${query.toString()}`
    );
  },

  getServiceRequestDetail: async (id: string): Promise<ServiceRequestDetail> => {
    return apiClient.request<ServiceRequestDetail>(`/workflows/service-requests/${id}`);
  },

  getCrossPhaseWorkspace: async (id: string): Promise<CrossPhaseCaseWorkspace> => {
    return apiClient.request<CrossPhaseCaseWorkspace>(`/workflows/service-requests/${id}/workspace`);
  },

  // Workflow Operations
  transitionServiceRequest: async (id: string, payload: TransitionPayload): Promise<ServiceRequestDetail> => {
    return apiClient.request<ServiceRequestDetail>(`/workflows/service-requests/${id}/transition`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  assignServiceRequest: async (id: string, payload: CaseAssignmentPayload): Promise<ServiceRequestDetail> => {
    return apiClient.request<ServiceRequestDetail>(`/workflows/service-requests/${id}/assign`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  commissionFieldSurvey: async (id: string, payload: SurveyCommissionPayload): Promise<ServiceRequestDetail> => {
    return apiClient.request<ServiceRequestDetail>(`/workflows/service-requests/${id}/commission-survey`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  escalateServiceRequest: async (id: string, payload: CaseEscalationPayload): Promise<ServiceRequestDetail> => {
    return apiClient.request<ServiceRequestDetail>(`/workflows/service-requests/${id}/escalate`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  executeControlledUpdate: async (id: string, payload: ControlledPropertyUpdatePayload): Promise<Record<string, any>> => {
    return apiClient.request<Record<string, any>>(`/workflows/service-requests/${id}/execute-update`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Case Messages
  listCaseMessages: async (id: string): Promise<CaseMessage[]> => {
    return apiClient.request<CaseMessage[]>(`/workflows/service-requests/${id}/messages`);
  },

  postCaseMessage: async (id: string, payload: CaseMessageCreatePayload): Promise<CaseMessage> => {
    return apiClient.request<CaseMessage>(`/workflows/service-requests/${id}/messages`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Citizen Portal
  listCitizenProperties: async (): Promise<CitizenProperty[]> => {
    return apiClient.request<CitizenProperty[]>('/workflows/citizen/properties');
  },

  linkCitizenProperty: async (payload: {
    citizen_id: string;
    property_id: string;
    authorization_type?: string;
    status?: string;
  }): Promise<any> => {
    return apiClient.request<any>('/workflows/citizen/properties', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getCitizenDashboard: async (): Promise<CitizenDashboardMetrics> => {
    return apiClient.request<CitizenDashboardMetrics>('/workflows/citizen/dashboard');
  },

  // Government Operations
  getGovernmentDashboard: async (): Promise<GovernmentDashboardMetrics> => {
    return apiClient.request<GovernmentDashboardMetrics>('/workflows/government/dashboard');
  },

  listGovernmentTasks: async (params: {
    task_type?: string;
    status?: string;
    my_tasks_only?: boolean;
  } = {}): Promise<WorkflowTask[]> => {
    const query = new URLSearchParams();
    if (params.task_type) query.set('task_type', params.task_type);
    if (params.status) query.set('status', params.status);
    if (params.my_tasks_only) query.set('my_tasks_only', 'true');
    return apiClient.request<WorkflowTask[]>(`/workflows/government/queues?${query.toString()}`);
  },

  // Notifications
  listNotifications: async (unread_only: boolean = false, limit: number = 50): Promise<Notification[]> => {
    const query = new URLSearchParams();
    if (unread_only) query.set('unread_only', 'true');
    query.set('limit', limit.toString());
    return apiClient.request<Notification[]>(`/workflows/notifications?${query.toString()}`);
  },

  markNotificationRead: async (id: string): Promise<Notification> => {
    return apiClient.request<Notification>(`/workflows/notifications/${id}/read`, {
      method: 'POST',
    });
  },

  markAllNotificationsRead: async (): Promise<{ marked_count: number; message: string }> => {
    return apiClient.request<{ marked_count: number; message: string }>('/workflows/notifications/read-all', {
      method: 'POST',
    });
  },
};
