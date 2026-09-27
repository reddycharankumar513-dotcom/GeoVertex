import { apiClient } from './client';
import {
  DocumentExtractedField,
  DocumentMetrics,
  DocumentProcessingJob,
  DocumentStatus,
  DocumentType,
  DocumentVerificationPayload,
  EntityLinkCreatePayload,
  FieldReviewPayload,
  PropertyDocument,
} from '../types/document';

export const documentsApi = {
  listDocuments: async (params: {
    skip?: number;
    limit?: number;
    status?: DocumentStatus;
    document_type?: DocumentType;
    jurisdiction_id?: string;
    parcel_id?: string;
    requires_review?: boolean;
  } = {}): Promise<PropertyDocument[]> => {
    const query = new URLSearchParams();
    if (params.skip !== undefined) query.set('skip', params.skip.toString());
    if (params.limit !== undefined) query.set('limit', params.limit.toString());
    if (params.status) query.set('status', params.status);
    if (params.document_type) query.set('document_type', params.document_type);
    if (params.jurisdiction_id) query.set('jurisdiction_id', params.jurisdiction_id);
    if (params.parcel_id) query.set('parcel_id', params.parcel_id);
    if (params.requires_review !== undefined) query.set('requires_review', params.requires_review.toString());

    return apiClient.request<PropertyDocument[]>(`/documents?${query.toString()}`);
  },

  getDocument: async (documentId: string): Promise<PropertyDocument> => {
    return apiClient.request<PropertyDocument>(`/documents/${documentId}`);
  },

  getMetrics: async (): Promise<DocumentMetrics> => {
    return apiClient.request<DocumentMetrics>('/documents/metrics');
  },

  uploadDocument: async (formData: FormData): Promise<PropertyDocument> => {
    return apiClient.request<PropertyDocument>('/documents/upload', {
      method: 'POST',
      body: formData,
    });
  },

  triggerProcessing: async (documentId: string): Promise<DocumentProcessingJob> => {
    return apiClient.request<DocumentProcessingJob>(`/documents/${documentId}/process`, {
      method: 'POST',
    });
  },

  reviewField: async (
    documentId: string,
    fieldId: string,
    payload: FieldReviewPayload
  ): Promise<DocumentExtractedField> => {
    return apiClient.request<DocumentExtractedField>(`/documents/${documentId}/fields/${fieldId}/review`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  createEntityLink: async (
    documentId: string,
    payload: EntityLinkCreatePayload
  ): Promise<PropertyDocument> => {
    return apiClient.request<PropertyDocument>(`/documents/${documentId}/links`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  confirmEntityLink: async (documentId: string, linkId: string): Promise<PropertyDocument> => {
    return apiClient.request<PropertyDocument>(`/documents/${documentId}/links/${linkId}/confirm`, {
      method: 'PATCH',
    });
  },

  rejectEntityLink: async (documentId: string, linkId: string): Promise<PropertyDocument> => {
    return apiClient.request<PropertyDocument>(`/documents/${documentId}/links/${linkId}/reject`, {
      method: 'PATCH',
    });
  },

  verifyDocument: async (
    documentId: string,
    payload: DocumentVerificationPayload
  ): Promise<PropertyDocument> => {
    return apiClient.request<PropertyDocument>(`/documents/${documentId}/verify`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getPageImageUrl: (documentId: string, pageNumber: number): string => {
    return `/api/v1/documents/${documentId}/pages/${pageNumber}/image`;
  },

  getDownloadUrl: (documentId: string): string => {
    return `/api/v1/documents/${documentId}/download`;
  },
};
