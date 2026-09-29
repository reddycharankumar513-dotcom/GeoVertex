/**
 * Phase 13 — Audit, Versioning, Notifications & Governance API Client.
 */

import { api, API_BASE } from './client';
import { PaginatedResult } from '../types';
import {
  AuditEventItem,
  AuditStatistics,
  DataIntegrityReport,
  EntityLineage,
  EntityVersion,
  GovernanceDashboard,
  NotificationItem,
  NotificationPreferenceItem,
  RestoreVersionRequest,
  VersionComparison,
} from '../types/governance';

export const auditApi = {
  async listEvents(params: {
    entity_type?: string;
    entity_id?: string;
    action?: string;
    category?: string;
    severity?: string;
    result?: string;
    source_type?: string;
    workflow_id?: string;
    correlation_id?: string;
    case_id?: string;
    date_from?: string;
    date_to?: string;
    page?: number;
    size?: number;
  } = {}): Promise<PaginatedResult<AuditEventItem>> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        query.append(k, String(v));
      }
    });
    return api.get<PaginatedResult<AuditEventItem>>(`/audit?${query.toString()}`);
  },

  async getEvent(id: string): Promise<AuditEventItem> {
    return api.get<AuditEventItem>(`/audit/${id}`);
  },

  async getStatistics(): Promise<AuditStatistics> {
    return api.get<AuditStatistics>('/audit/statistics');
  },

  getExportUrl(format: 'csv' | 'json', filters: Record<string, string> = {}): string {
    const query = new URLSearchParams({ format, ...filters });
    return `${API_BASE}/audit/export?${query.toString()}`;
  },

};

export const versionApi = {
  async listVersions(
    entityType: string,
    entityId: string,
    page: number = 1,
    size: number = 20
  ): Promise<PaginatedResult<EntityVersion>> {
    return api.get<PaginatedResult<EntityVersion>>(
      `/versions/${entityType}/${entityId}?page=${page}&size=${size}`
    );
  },

  async getVersion(
    entityType: string,
    entityId: string,
    versionNumber: number
  ): Promise<EntityVersion> {
    return api.get<EntityVersion>(`/versions/${entityType}/${entityId}/${versionNumber}`);
  },

  async compareVersions(
    versionAId: string,
    versionBId: string
  ): Promise<VersionComparison> {
    return api.get<VersionComparison>(`/versions/compare/${versionAId}/${versionBId}`);
  },

  async restoreVersion(
    entityType: string,
    entityId: string,
    data: RestoreVersionRequest
  ): Promise<EntityVersion> {
    return api.post<EntityVersion>(`/versions/${entityType}/${entityId}/restore`, data);
  },

  async getLineage(entityType: string, entityId: string): Promise<EntityLineage[]> {
    return api.get<EntityLineage[]>(`/versions/${entityType}/${entityId}/lineage`);
  },
};

export const notificationApi = {
  async listNotifications(
    unreadOnly: boolean = false,
    severity?: string,
    page: number = 1,
    size: number = 20
  ): Promise<PaginatedResult<NotificationItem>> {
    const query = new URLSearchParams({
      unread_only: String(unreadOnly),
      page: String(page),
      size: String(size),
    });
    if (severity) query.append('severity', severity);
    return api.get<PaginatedResult<NotificationItem>>(`/notifications?${query.toString()}`);
  },

  async getUnreadCount(): Promise<number> {
    const res = await api.get<{ unread_count: number }>('/notifications/unread-count');
    return res.unread_count;
  },

  async markAsRead(id: string): Promise<NotificationItem> {
    return api.post<NotificationItem>(`/notifications/${id}/read`, {});
  },

  async markAllAsRead(): Promise<{ marked_read: number }> {
    return api.post<{ marked_read: number }>('/notifications/read-all', {});
  },

  async getPreferences(): Promise<NotificationPreferenceItem[]> {
    return api.get<NotificationPreferenceItem[]>('/notifications/preferences');
  },

  async updatePreference(data: {
    notification_type: string;
    channel: string;
    enabled: boolean;
    digest_frequency?: string;
  }): Promise<NotificationPreferenceItem> {
    return api.put<NotificationPreferenceItem>('/notifications/preferences', data);
  },

  async triggerTest(data: {
    notification_type?: string;
    title: string;
    message: string;
    severity?: string;
    channel?: string;
  }): Promise<NotificationItem> {
    return api.post<NotificationItem>('/notifications/test', data);
  },
};

export const governanceApi = {
  async getDashboard(): Promise<GovernanceDashboard> {
    return api.get<GovernanceDashboard>('/governance/dashboard');
  },

  async checkIntegrity(): Promise<DataIntegrityReport> {
    return api.get<DataIntegrityReport>('/governance/integrity');
  },
};
