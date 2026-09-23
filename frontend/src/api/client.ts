import { ApiError } from '../types';

const API_BASE = '/api/v1';

export class ApiClientError extends Error {
  code: string;
  details?: Record<string, any>;
  status: number;

  constructor(status: number, errorData: ApiError) {
    super(errorData.message || 'An API error occurred');
    this.name = 'ApiClientError';
    this.status = status;
    this.code = errorData.code || 'UNKNOWN_ERROR';
    this.details = errorData.details;
  }
}

class ApiClient {
  private getAuthHeader(): Record<string, string> {
    const token = localStorage.getItem('geovertex_access_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...this.getAuthHeader(),
      ...((options.headers as Record<string, string>) || {}),
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 204) {
      return {} as T;
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      if (response.status === 401) {
        // If unauthenticated on protected route, trigger auth cleanup
        const isAuthRoute = endpoint.includes('/auth/login') || endpoint.includes('/auth/register');
        if (!isAuthRoute) {
          localStorage.removeItem('geovertex_access_token');
          localStorage.removeItem('geovertex_refresh_token');
          localStorage.removeItem('geovertex_user');
          window.dispatchEvent(new Event('geovertex_auth_expired'));
        }
      }

      const errorPayload: ApiError = data.error || {
        code: 'HTTP_ERROR',
        message: data.message || `Request failed with status ${response.status}`,
        details: data,
      };
      throw new ApiClientError(response.status, errorPayload);
    }

    return data as T;
  }

  get<T>(endpoint: string, headers?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', headers });
  }

  post<T>(endpoint: string, body?: any, headers?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
      headers,
    });
  }

  patch<T>(endpoint: string, body?: any, headers?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
      headers,
    });
  }

  delete<T>(endpoint: string, headers?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE', headers });
  }
}

export const api = new ApiClient();
