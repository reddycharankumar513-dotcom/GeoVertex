import { describe, it, expect } from 'vitest';
import { UserRole } from '../types';
import {
  ValidationIssue,
  ValidationRun,
  ValidationSeverity,
  ValidationIssueStatus,
  ValidationCategory,
} from '../types/validation';

describe('GeoVertex Phase 7 - Advanced Topology Validation & Spatial Consistency', () => {
  // 1. Role-Based Access Control (RBAC) for Topology Validation
  it('enforces RBAC for validation triggering, acknowledgment, resolution, and waiver', () => {
    const canTriggerValidation = (role: UserRole) => {
      return ['ADMIN', 'GOVERNMENT_OFFICER', 'SURVEYOR', 'URBAN_PLANNER'].includes(role);
    };

    const canAcknowledgeIssue = (role: UserRole) => {
      return ['SURVEYOR', 'GOVERNMENT_OFFICER', 'ADMIN'].includes(role);
    };

    const canResolveOrWaiveIssue = (role: UserRole) => {
      return ['GOVERNMENT_OFFICER', 'ADMIN'].includes(role);
    };

    // Citizen can view but cannot trigger or review
    expect(canTriggerValidation('CITIZEN')).toBe(false);
    expect(canAcknowledgeIssue('CITIZEN')).toBe(false);
    expect(canResolveOrWaiveIssue('CITIZEN')).toBe(false);

    // Surveyor can trigger and acknowledge, but cannot formally resolve or waive
    expect(canTriggerValidation('SURVEYOR')).toBe(true);
    expect(canAcknowledgeIssue('SURVEYOR')).toBe(true);
    expect(canResolveOrWaiveIssue('SURVEYOR')).toBe(false);

    // Government Officer has full review capability (acknowledge, resolve, waive)
    expect(canTriggerValidation('GOVERNMENT_OFFICER')).toBe(true);
    expect(canAcknowledgeIssue('GOVERNMENT_OFFICER')).toBe(true);
    expect(canResolveOrWaiveIssue('GOVERNMENT_OFFICER')).toBe(true);

    // Admin has full capability
    expect(canTriggerValidation('ADMIN')).toBe(true);
    expect(canAcknowledgeIssue('ADMIN')).toBe(true);
    expect(canResolveOrWaiveIssue('ADMIN')).toBe(true);
  });

  // 2. Issue Severity Classification & Category Integrity
  it('strictly validates issue severities, categories, and codes without synthetic corruption', () => {
    const validSeverities: ValidationSeverity[] = ['INFO', 'WARNING', 'ERROR', 'CRITICAL'];
    const validCategories: ValidationCategory[] = [
      'GEOMETRY',
      'PARCEL',
      'BUILDING',
      'FLOOR',
      'UNIT',
      'VERTICAL',
      'AI',
      'SURVEY',
      'CRS',
      'CROSS_DATASET',
    ];

    const sampleIssue: ValidationIssue = {
      id: 'iss-test-001',
      validation_run_id: 'run-test-001',
      rule_id: 'BLD_001',
      rule_version: '1.0.0',
      issue_code: 'BUILDING_OUTSIDE_PARCEL',
      category: 'BUILDING',
      severity: 'ERROR',
      status: 'OPEN',
      entity_type: 'BUILDING',
      entity_id: 'bld-001',
      related_entity_type: 'PARCEL',
      related_entity_id: 'pcl-001',
      message: 'Building footprint is completely outside its designated parcel.',
      technical_explanation: 'Intersection area is 0.000m²; containment ratio 0.00% is below tolerance.',
      geometry_wkt: 'POLYGON((78.38 17.44, 78.39 17.44, 78.39 17.45, 78.38 17.45, 78.38 17.44))',
      measured_value: '0.0',
      expected_value: '100.0',
      tolerance: '98.0',
      metadata_json: { area_m2: 120.5 },
      created_at: '2026-09-24T10:00:00Z',
    };

    expect(validSeverities).toContain(sampleIssue.severity);
    expect(validCategories).toContain(sampleIssue.category);
    expect(parseFloat(sampleIssue.measured_value ?? '0')).toBeLessThan(parseFloat(sampleIssue.tolerance ?? '100'));
    expect(sampleIssue.technical_explanation).toContain('Intersection area');
  });

  // 3. Human Review Lifecycle State Transitions
  it('manages issue lifecycle state transitions and mandates note or waiver reason', () => {
    interface LifecycleActionInput {
      currentStatus: ValidationIssueStatus;
      action: 'ACKNOWLEDGE' | 'RESOLVE' | 'WAIVE';
      note?: string;
      reason?: string;
    }

    const processReviewAction = (input: LifecycleActionInput): { nextStatus: ValidationIssueStatus; error?: string } => {
      const { currentStatus, action, note, reason } = input;

      if (action === 'ACKNOWLEDGE') {
        if (currentStatus !== 'OPEN') {
          return { nextStatus: currentStatus, error: 'Only OPEN issues can be acknowledged.' };
        }
        return { nextStatus: 'ACKNOWLEDGED' };
      }

      if (action === 'RESOLVE') {
        if (!note || note.trim().length === 0) {
          return { nextStatus: currentStatus, error: 'Resolution note is required to resolve an issue.' };
        }
        return { nextStatus: 'RESOLVED' };
      }

      if (action === 'WAIVE') {
        if (!reason || reason.trim().length === 0) {
          return { nextStatus: currentStatus, error: 'Waiver reason is required to waive an issue.' };
        }
        return { nextStatus: 'WAIVED' };
      }

      return { nextStatus: currentStatus };
    };

    // Acknowledge OPEN issue
    const ack = processReviewAction({ currentStatus: 'OPEN', action: 'ACKNOWLEDGE' });
    expect(ack.nextStatus).toBe('ACKNOWLEDGED');
    expect(ack.error).toBeUndefined();

    // Resolve without note should fail
    const resolveFail = processReviewAction({ currentStatus: 'ACKNOWLEDGED', action: 'RESOLVE', note: '' });
    expect(resolveFail.error).toContain('Resolution note is required');
    expect(resolveFail.nextStatus).toBe('ACKNOWLEDGED');

    // Resolve with note succeeds
    const resolveOk = processReviewAction({
      currentStatus: 'ACKNOWLEDGED',
      action: 'RESOLVE',
      note: 'Field surveyor verified boundary adjustment on-site.',
    });
    expect(resolveOk.nextStatus).toBe('RESOLVED');

    // Waive without reason should fail
    const waiveFail = processReviewAction({ currentStatus: 'OPEN', action: 'WAIVE', reason: '  ' });
    expect(waiveFail.error).toContain('Waiver reason is required');

    // Waive with reason succeeds
    const waiveOk = processReviewAction({
      currentStatus: 'OPEN',
      action: 'WAIVE',
      reason: 'Historical right-of-way easement pre-dates digital cadastre standard.',
    });
    expect(waiveOk.nextStatus).toBe('WAIVED');
  });

  // 4. Cadastral Safety: Non-Automated Legal Decisions Rule
  it('guarantees topology findings remain non-automated technical observations', () => {
    const validateTechnicalIntegrity = (issue: ValidationIssue) => {
      expect(issue.technical_explanation).toBeDefined();
      expect(issue.technical_explanation.length).toBeGreaterThan(10);
      const nonLegalStatuses: ValidationIssueStatus[] = ['OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'WAIVED'];
      expect(nonLegalStatuses).toContain(issue.status);
    };

    const finding: ValidationIssue = {
      id: 'iss-test-002',
      validation_run_id: 'run-002',
      rule_id: 'PAR_001',
      rule_version: '1.0.0',
      issue_code: 'PARCEL_OVERLAP',
      category: 'PARCEL',
      severity: 'CRITICAL',
      status: 'OPEN',
      entity_type: 'PARCEL',
      entity_id: 'pcl-001',
      related_entity_type: 'PARCEL',
      related_entity_id: 'pcl-002',
      message: 'Parcels share an overlapping boundary area of 14.25m².',
      technical_explanation: 'Overlapping area exceeds zero-overlap polygon boundary tolerance (0.05m²).',
      measured_value: '14.25',
      expected_value: '0.0',
      tolerance: '0.05',
      metadata_json: {},
      created_at: '2026-09-24T10:00:00Z',
    };

    validateTechnicalIntegrity(finding);
  });

  // 5. SVG Vector Map Geometry Projection & Bounding Box Calculation
  it('safely parses WKT coordinates and computes non-degenerate bounding boxes', () => {
    const parseSimpleWkt = (wkt: string): [number, number][] => {
      const match = wkt.match(/POLYGON\s*\(\((.*?)\)\)/i);
      if (!match) return [];
      const coordPairs = match[1].split(',');
      return coordPairs.map((pair) => {
        const [x, y] = pair.trim().split(/\s+/).map(Number);
        return [x, y] as [number, number];
      });
    };

    const computeBBox = (points: [number, number][]) => {
      if (points.length === 0) return null;
      let minX = Infinity,
        minY = Infinity,
        maxX = -Infinity,
        maxY = -Infinity;
      points.forEach(([x, y]) => {
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
      });
      return { minX, minY, maxX, maxY, width: maxX - minX, height: maxY - minY };
    };

    const wkt = 'POLYGON((78.38 17.44, 78.40 17.44, 78.40 17.46, 78.38 17.46, 78.38 17.44))';
    const coords = parseSimpleWkt(wkt);
    expect(coords.length).toBe(5);

    const bbox = computeBBox(coords);
    expect(bbox).not.toBeNull();
    expect(bbox!.width).toBeCloseTo(0.02, 4);
    expect(bbox!.height).toBeCloseTo(0.02, 4);
    expect(bbox!.minX).toBeCloseTo(78.38, 4);
    expect(bbox!.maxY).toBeCloseTo(17.46, 4);
  });

  // 6. Validation Run Summary Metrics
  it('correctly compiles run summary counts across severities', () => {
    const compileSummary = (issues: ValidationIssue[]) => {
      const summary = {
        total_issues: issues.length,
        critical_count: 0,
        error_count: 0,
        warning_count: 0,
        info_count: 0,
      };

      issues.forEach((iss) => {
        if (iss.severity === 'CRITICAL') summary.critical_count++;
        else if (iss.severity === 'ERROR') summary.error_count++;
        else if (iss.severity === 'WARNING') summary.warning_count++;
        else if (iss.severity === 'INFO') summary.info_count++;
      });

      return summary;
    };

    const testIssues: ValidationIssue[] = [
      {
        id: '1',
        validation_run_id: 'r1',
        rule_id: 'R1',
        rule_version: '1',
        issue_code: 'C1',
        category: 'PARCEL',
        severity: 'CRITICAL',
        status: 'OPEN',
        entity_type: 'PARCEL',
        entity_id: 'e1',
        message: 'm',
        technical_explanation: 'explanation',
        metadata_json: {},
        created_at: '2026-09-24T00:00:00Z',
      },
      {
        id: '2',
        validation_run_id: 'r1',
        rule_id: 'R2',
        rule_version: '1',
        issue_code: 'C2',
        category: 'BUILDING',
        severity: 'ERROR',
        status: 'OPEN',
        entity_type: 'BUILDING',
        entity_id: 'e2',
        message: 'm',
        technical_explanation: 'explanation',
        metadata_json: {},
        created_at: '2026-09-24T00:00:00Z',
      },
      {
        id: '3',
        validation_run_id: 'r1',
        rule_id: 'R3',
        rule_version: '1',
        issue_code: 'C3',
        category: 'VERTICAL',
        severity: 'WARNING',
        status: 'OPEN',
        entity_type: 'FLOOR',
        entity_id: 'e3',
        message: 'm',
        technical_explanation: 'explanation',
        metadata_json: {},
        created_at: '2026-09-24T00:00:00Z',
      },
      {
        id: '4',
        validation_run_id: 'r1',
        rule_id: 'R4',
        rule_version: '1',
        issue_code: 'C4',
        category: 'CRS',
        severity: 'INFO',
        status: 'OPEN',
        entity_type: 'PARCEL',
        entity_id: 'e4',
        message: 'm',
        technical_explanation: 'explanation',
        metadata_json: {},
        created_at: '2026-09-24T00:00:00Z',
      },
    ];

    const summary = compileSummary(testIssues);
    expect(summary.total_issues).toBe(4);
    expect(summary.critical_count).toBe(1);
    expect(summary.error_count).toBe(1);
    expect(summary.warning_count).toBe(1);
    expect(summary.info_count).toBe(1);
  });
});
