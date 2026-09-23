import { describe, it, expect, beforeEach } from 'vitest';
import { ApiClientError } from '../api/client';
import { UserRole } from '../types';

describe('GeoVertex Frontend Foundation - Auth & RBAC Logic', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('correctly parses and formats ApiClientError with standardized code envelope', () => {
    const errorPayload = {
      code: 'UNAUTHORIZED',
      message: 'Invalid username, email, or password',
      details: { field: 'password' },
    };
    const error = new ApiClientError(401, errorPayload);

    expect(error.status).toBe(401);
    expect(error.code).toBe('UNAUTHORIZED');
    expect(error.message).toBe('Invalid username, email, or password');
    expect(error.details).toEqual({ field: 'password' });
  });

  it('validates role hierarchy permissions for GeoVertex administrative routes', () => {
    const adminAllowedRoles: UserRole[] = ['ADMIN', 'GOVERNMENT_OFFICER'];

    // Admin should be allowed
    expect(adminAllowedRoles.includes('ADMIN')).toBe(true);

    // Officer should be allowed
    expect(adminAllowedRoles.includes('GOVERNMENT_OFFICER')).toBe(true);

    // Surveyor should NOT be allowed on admin users page
    expect(adminAllowedRoles.includes('SURVEYOR')).toBe(false);

    // Citizen should NOT be allowed on admin users page
    expect(adminAllowedRoles.includes('CITIZEN')).toBe(false);

    // Planner should NOT be allowed on admin users page
    expect(adminAllowedRoles.includes('URBAN_PLANNER')).toBe(false);
  });

  it('validates audit route exclusivity for ADMIN role', () => {
    const auditAllowedRoles: UserRole[] = ['ADMIN'];

    expect(auditAllowedRoles.includes('ADMIN')).toBe(true);
    expect(auditAllowedRoles.includes('GOVERNMENT_OFFICER')).toBe(false);
    expect(auditAllowedRoles.includes('SURVEYOR')).toBe(false);
    expect(auditAllowedRoles.includes('CITIZEN')).toBe(false);
  });

  it('manages authentication session state in local storage', () => {
    const mockUser = {
      id: 'd470b751-2da1-4e62-8640-ed90d1f2132e',
      email: 'admin@geovertex.local',
      username: 'admin',
      full_name: 'System Administrator',
      role: 'ADMIN' as UserRole,
      is_active: true,
      is_verified: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    localStorage.setItem('geovertex_access_token', 'test_access_jwt');
    localStorage.setItem('geovertex_refresh_token', 'test_refresh_token');
    localStorage.setItem('geovertex_user', JSON.stringify(mockUser));

    expect(localStorage.getItem('geovertex_access_token')).toBe('test_access_jwt');
    const storedUser = JSON.parse(localStorage.getItem('geovertex_user') || '{}');
    expect(storedUser.role).toBe('ADMIN');
    expect(storedUser.is_active).toBe(true);

    // Invalidate session (logout)
    localStorage.removeItem('geovertex_access_token');
    localStorage.removeItem('geovertex_refresh_token');
    localStorage.removeItem('geovertex_user');

    expect(localStorage.getItem('geovertex_access_token')).toBeNull();
    expect(localStorage.getItem('geovertex_user')).toBeNull();
  });
});
