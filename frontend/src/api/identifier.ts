// Phase 12 — API client for Technical 3D Property Identifier Engine
import type {
  BulkPreview,
  IdentifierJob,
  IdentifierScheme,
  IdentifierStatistics,
  PaginatedIdentifiers,
  PreviewResult,
  PropertyIdentifier,
  SupersedeResponse,
  VerificationResult,
  IdentifierLineage,
} from '../types/identifier';
import { API_BASE } from './client';

const BASE = API_BASE;

function getHeaders(): Record<string, string> {
  const token = localStorage.getItem('access_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new Error(err?.error?.message || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── Schemes ─────────────────────────────────────────────────────────────────

export async function fetchSchemes(): Promise<IdentifierScheme[]> {
  const res = await fetch(`${BASE}/identifiers/schemes`, { headers: getHeaders() });
  return handleResponse(res);
}

export async function createScheme(data: Partial<IdentifierScheme>): Promise<IdentifierScheme> {
  const res = await fetch(`${BASE}/identifiers/schemes`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function patchScheme(id: string, data: Partial<IdentifierScheme>): Promise<IdentifierScheme> {
  const res = await fetch(`${BASE}/identifiers/schemes/${id}`, {
    method: 'PATCH',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

// ── Identifiers ──────────────────────────────────────────────────────────────

export async function fetchIdentifiers(params: {
  status?: string;
  entity_type?: string;
  scheme_id?: string;
  jurisdiction_id?: string;
  parcel_id?: string;
  building_id?: string;
  search?: string;
  skip?: number;
  limit?: number;
}): Promise<PaginatedIdentifiers> {
  const q = new URLSearchParams();
  if (params.status) q.set('status', params.status);
  if (params.entity_type) q.set('entity_type', params.entity_type);
  if (params.scheme_id) q.set('scheme_id', params.scheme_id);
  if (params.jurisdiction_id) q.set('jurisdiction_id', params.jurisdiction_id);
  if (params.parcel_id) q.set('parcel_id', params.parcel_id);
  if (params.building_id) q.set('building_id', params.building_id);
  if (params.search) q.set('search', params.search);
  if (params.skip !== undefined) q.set('skip', String(params.skip));
  if (params.limit !== undefined) q.set('limit', String(params.limit));
  const res = await fetch(`${BASE}/identifiers?${q}`, { headers: getHeaders() });
  return handleResponse(res);
}

export async function fetchIdentifierById(id: string): Promise<PropertyIdentifier> {
  const res = await fetch(`${BASE}/identifiers/${id}`, { headers: getHeaders() });
  return handleResponse(res);
}

export async function fetchIdentifierHistory(id: string): Promise<PropertyIdentifier[]> {
  const res = await fetch(`${BASE}/identifiers/${id}/history`, { headers: getHeaders() });
  return handleResponse(res);
}

export async function fetchIdentifierLineage(id: string): Promise<IdentifierLineage[]> {
  const res = await fetch(`${BASE}/identifiers/${id}/lineage`, { headers: getHeaders() });
  return handleResponse(res);
}

export async function fetchIdentifierStatistics(): Promise<IdentifierStatistics> {
  const res = await fetch(`${BASE}/identifiers/statistics`, { headers: getHeaders() });
  return handleResponse(res);
}

// ── Generate / Preview ───────────────────────────────────────────────────────

export async function previewIdentifier(data: {
  entity_type: string;
  entity_id: string;
  scheme_id?: string;
}): Promise<PreviewResult> {
  const res = await fetch(`${BASE}/identifiers/preview`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function generateIdentifier(data: {
  entity_type: string;
  entity_id: string;
  scheme_id?: string;
  force_new?: boolean;
}): Promise<PropertyIdentifier> {
  const res = await fetch(`${BASE}/identifiers/generate`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

// ── Lifecycle ────────────────────────────────────────────────────────────────

export async function supersedeIdentifier(
  id: string,
  data: { reason: string; new_entity_id?: string },
): Promise<SupersedeResponse> {
  const res = await fetch(`${BASE}/identifiers/${id}/supersede`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function retireIdentifier(id: string, reason: string): Promise<PropertyIdentifier> {
  const res = await fetch(`${BASE}/identifiers/${id}/retire`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ reason }),
  });
  return handleResponse(res);
}

export async function revokeIdentifier(id: string, reason: string): Promise<PropertyIdentifier> {
  const res = await fetch(`${BASE}/identifiers/${id}/revoke`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ reason }),
  });
  return handleResponse(res);
}

// ── Verification ────────────────────────────────────────────────────────────

export async function verifyIdentifier(id: string): Promise<VerificationResult> {
  const res = await fetch(`${BASE}/identifiers/${id}/verify`, { headers: getHeaders() });
  return handleResponse(res);
}

export async function verifyByToken(token: string): Promise<VerificationResult> {
  const res = await fetch(`${BASE}/verify/${token}`);
  return handleResponse(res);
}

export function getQrUrl(id: string, fmt: 'png' | 'svg' = 'png'): string {
  const token = localStorage.getItem('access_token');
  return `${BASE}/identifiers/${id}/qr?fmt=${fmt}&_token=${token ?? ''}`;
}

// ── Bulk ─────────────────────────────────────────────────────────────────────

export async function bulkPreview(data: {
  entity_type: string;
  building_id: string;
  scheme_id?: string;
}): Promise<BulkPreview> {
  const res = await fetch(`${BASE}/identifiers/bulk-preview`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function bulkGenerate(data: {
  entity_type: string;
  building_id: string;
  scheme_id?: string;
  confirmed: boolean;
}): Promise<{ job_id: string; status: string; total: number; generated: number }> {
  const res = await fetch(`${BASE}/identifiers/bulk-generate`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

// ── Jobs ─────────────────────────────────────────────────────────────────────

export async function fetchJobs(skip = 0, limit = 20): Promise<{ items: IdentifierJob[]; total: number }> {
  const res = await fetch(`${BASE}/identifiers/jobs?skip=${skip}&limit=${limit}`, { headers: getHeaders() });
  return handleResponse(res);
}

export async function fetchJobById(id: string): Promise<IdentifierJob> {
  const res = await fetch(`${BASE}/identifiers/jobs/${id}`, { headers: getHeaders() });
  return handleResponse(res);
}
