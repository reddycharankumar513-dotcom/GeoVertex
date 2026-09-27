/**
 * GeoVertex Phase 11: Citizen Portal & Government Workflow Types
 */

export type RequestStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'MORE_INFO_REQUESTED'
  | 'SURVEY_COMMISSIONED'
  | 'SURVEY_COMPLETED'
  | 'FIELD_VERIFIED'
  | 'APPROVED'
  | 'REJECTED'
  | 'CANCELLED'
  | 'COMPLETED';

export type RequestPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';

export type EventType =
  | 'STATUS_CHANGE'
  | 'ASSIGNMENT_CHANGE'
  | 'SURVEY_COMMISSIONED'
  | 'DOCUMENT_ATTACHED'
  | 'OFFICER_NOTE'
  | 'CITIZEN_COMMENT'
  | 'REVISION_REQUESTED'
  | 'REVISION_SUBMITTED'
  | 'ESCALATED'
  | 'OFFICIAL_RECORD_UPDATED';

export type MessageType = 'PUBLIC_MESSAGE' | 'INTERNAL_NOTE' | 'SYSTEM_EVENT';

export type TaskType =
  | 'INITIAL_REVIEW'
  | 'DOCUMENT_VERIFICATION'
  | 'FIELD_SURVEY_EXECUTION'
  | 'GIS_BOUNDARY_VERIFICATION'
  | 'FINAL_APPROVAL'
  | 'OFFICIAL_RECORD_UPDATE';

export type TaskStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';

export type NotificationType =
  | 'STATUS_CHANGED'
  | 'ACTION_REQUIRED'
  | 'DOCUMENT_REJECTED'
  | 'SURVEY_SCHEDULED'
  | 'CASE_APPROVED'
  | 'CASE_REJECTED'
  | 'CASE_ESCALATED';

export type DeliveryChannel = 'IN_APP' | 'EMAIL_QUEUED' | 'EMAIL_NOT_CONFIGURED';

export type AuthorizationType = 'OWNER' | 'AUTHORIZED_REPRESENTATIVE' | 'OCCUPANT' | 'TENANT';

export type LinkStatus = 'ACTIVE' | 'VERIFIED' | 'PENDING_VERIFICATION' | 'REVOKED';

export interface ServiceType {
  id: string;
  code: string;
  name: string;
  description?: string;
  active: boolean;
  citizen_visible: boolean;
  required_documents: string[];
  required_fields: string[];
  response_sla_hours: number;
  completion_sla_hours: number;
  allowed_roles: string[];
  created_at: string;
  updated_at: string;
}

export interface ServiceRequest {
  id: string;
  request_reference: string;
  case_reference: string;
  citizen_id: string;
  jurisdiction_id: string;
  property_id?: string;
  parcel_id?: string;
  building_id?: string;
  floor_id?: string;
  unit_id?: string;
  request_type: string;
  title: string;
  description: string;
  status: RequestStatus;
  priority: RequestPriority;
  assigned_to?: string;
  assigned_team?: string;
  survey_project_id?: string;
  survey_assignment_id?: string;
  assigned_surveyor_id?: string;
  submitted_at?: string;
  acknowledged_at?: string;
  due_at?: string;
  completed_at?: string;
  escalated_at?: string;
  escalation_reason?: string;
  metadata_json: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface ServiceRequestEvent {
  id: string;
  service_request_id: string;
  previous_status?: RequestStatus;
  new_status: RequestStatus;
  actor_id?: string;
  actor_role: string;
  event_type: EventType;
  reason?: string;
  comment?: string;
  is_internal: boolean;
  created_at: string;
}

export interface CaseMessage {
  id: string;
  service_request_id: string;
  sender_id?: string;
  sender_role: string;
  message_type: MessageType;
  message_body: string;
  attachments_json: Record<string, any>[];
  is_internal: boolean;
  created_at: string;
  sender_name?: string;
}

export interface WorkflowTask {
  id: string;
  service_request_id: string;
  assigned_to?: string;
  task_type: TaskType;
  title: string;
  description?: string;
  status: TaskStatus;
  due_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface Notification {
  id: string;
  user_id: string;
  notification_type: NotificationType;
  title: string;
  message: string;
  related_entity_type?: string;
  related_entity_id?: string;
  delivery_channel: DeliveryChannel;
  read_at?: string;
  created_at: string;
}

export interface CitizenProperty {
  id: string;
  property_id: string;
  property_reference: string;
  parcel_id: string;
  parcel_number?: string;
  property_type: string;
  status: string;
  address: string;
  locality?: string;
  postal_code?: string;
  description?: string;
  authorization_type: AuthorizationType;
  link_status: LinkStatus;
  units_count: number;
  created_at: string;
}

export interface CitizenDashboardMetrics {
  total_properties: number;
  active_requests: number;
  pending_action_requests: number;
  completed_requests: number;
  unread_notifications: number;
}

export interface GovernmentDashboardMetrics {
  total_active_cases: number;
  unassigned_cases: number;
  overdue_cases: number;
  due_soon_cases: number;
  surveys_commissioned: number;
  completed_last_30_days: number;
  sla_compliance_rate: number;
  cases_by_status: Record<string, number>;
  cases_by_priority: Record<string, number>;
}

export interface CrossPhaseCaseWorkspace {
  service_request: ServiceRequest;
  service_type?: ServiceType;
  property?: Record<string, any>;
  parcel?: Record<string, any>;
  building?: Record<string, any>;
  documents: Record<string, any>[];
  surveys: Record<string, any>[];
  survey_assignments: Record<string, any>[];
  topology_validation_runs: Record<string, any>[];
  topology_issues: Record<string, any>[];
  change_candidates: Record<string, any>[];
  utility_clashes: Record<string, any>[];
  sla: {
    status: 'ON_TRACK' | 'DUE_SOON' | 'OVERDUE' | 'NOT_APPLICABLE';
    hours_remaining: number;
    due_at?: string;
  };
}

export interface ServiceRequestDetail {
  request: ServiceRequest;
  events: ServiceRequestEvent[];
  messages: CaseMessage[];
  tasks: WorkflowTask[];
  sla: {
    status: 'ON_TRACK' | 'DUE_SOON' | 'OVERDUE' | 'NOT_APPLICABLE';
    hours_remaining: number;
    due_at?: string;
  };
}

export interface ServiceRequestCreatePayload {
  request_type: string;
  title: string;
  description: string;
  jurisdiction_id: string;
  property_id?: string;
  parcel_id?: string;
  building_id?: string;
  floor_id?: string;
  unit_id?: string;
  priority?: RequestPriority;
  metadata_json?: Record<string, any>;
}

export interface TransitionPayload {
  new_status: RequestStatus;
  reason?: string;
  comment?: string;
}

export interface CaseAssignmentPayload {
  assigned_to: string;
  assigned_team?: string;
  notes?: string;
}

export interface CaseEscalationPayload {
  escalation_reason: string;
  assigned_to?: string;
  escalated_priority?: RequestPriority;
}

export interface SurveyCommissionPayload {
  surveyor_id: string;
  instructions: string;
  due_days?: number;
}

export interface ControlledPropertyUpdatePayload {
  updates: Record<string, any>;
  audit_reason: string;
  source_reference: string;
}

export interface CaseMessageCreatePayload {
  message_body: string;
  message_type?: MessageType;
  attachments_json?: Record<string, any>[];
}
