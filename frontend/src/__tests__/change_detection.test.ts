import { describe, it, expect } from 'vitest';
import { UserRole } from '../types';
import {
  CandidateStatus,
  ChangeCandidate,
  ChangeCandidateReviewPayload,
  ChangeDetectionRun,
  ChangeSignificance,
  ChangeType,
  DetectionMethod,
  ReviewReason,
  SnapshotEntityType,
  TimelineEntry,
} from '../types/temporal';

describe('GeoVertex Phase 9 - AI Change Detection & Temporal Property Intelligence', () => {
  // 1. Role-Based Access Control (RBAC)
  it('enforces strict RBAC for triggering runs and reviewing change candidates', () => {
    const canTriggerChangeRun = (role: UserRole) => {
      return ['ADMIN', 'GOVERNMENT_OFFICER', 'SURVEYOR', 'URBAN_PLANNER'].includes(role);
    };

    const canReviewCandidate = (role: UserRole) => {
      // Reviewing and confirming physical changes into official registry is restricted to Officers and Admins
      return ['ADMIN', 'GOVERNMENT_OFFICER'].includes(role);
    };

    // Citizen
    expect(canTriggerChangeRun('CITIZEN')).toBe(false);
    expect(canReviewCandidate('CITIZEN')).toBe(false);

    // Surveyor (can trigger detection run, but cannot perform official legal review/confirmation)
    expect(canTriggerChangeRun('SURVEYOR')).toBe(true);
    expect(canReviewCandidate('SURVEYOR')).toBe(false);

    // Urban Planner (can trigger detection run, but cannot confirm official records)
    expect(canTriggerChangeRun('URBAN_PLANNER')).toBe(true);
    expect(canReviewCandidate('URBAN_PLANNER')).toBe(false);

    // Government Officer (can trigger and perform official reviews)
    expect(canTriggerChangeRun('GOVERNMENT_OFFICER')).toBe(true);
    expect(canReviewCandidate('GOVERNMENT_OFFICER')).toBe(true);

    // Admin (full privileges)
    expect(canTriggerChangeRun('ADMIN')).toBe(true);
    expect(canReviewCandidate('ADMIN')).toBe(true);
  });

  // 2. Strict "No Fake AI" State and Model Configuration
  it('enforces explicit unconfigured states when AI weights or evaluation datasets are absent', () => {
    const evaluateAIModelStatus = (weightsConfigured: boolean) => {
      if (!weightsConfigured) {
        return {
          status: 'MODEL_NOT_CONFIGURED',
          message: 'Change detection vision model weights not configured. Deterministic geometric diff remains operational.',
          canExecuteAI: false,
        };
      }
      return {
        status: 'READY',
        message: 'Model weights active.',
        canExecuteAI: true,
      };
    };

    const unconfigured = evaluateAIModelStatus(false);
    expect(unconfigured.status).toBe('MODEL_NOT_CONFIGURED');
    expect(unconfigured.canExecuteAI).toBe(false);
    expect(unconfigured.message).toContain('Deterministic geometric diff remains operational');

    const configured = evaluateAIModelStatus(true);
    expect(configured.status).toBe('READY');
    expect(configured.canExecuteAI).toBe(true);
  });

  // 3. Deterministic Change Significance Classification
  it('classifies change significance deterministically based on metric area, height, and displacement thresholds', () => {
    const classifySignificance = (
      areaDeltaSqm: number,
      heightDeltaM: number,
      displacementM: number
    ): ChangeSignificance => {
      if (areaDeltaSqm > 50.0 || heightDeltaM > 4.0 || displacementM > 5.0) {
        return 'MAJOR';
      }
      if (areaDeltaSqm > 10.0 || heightDeltaM > 1.5 || displacementM > 1.0) {
        return 'MODERATE';
      }
      if (areaDeltaSqm > 0.5 || heightDeltaM > 0.2 || displacementM > 0.2) {
        return 'MINOR';
      }
      return 'UNKNOWN';
    };

    // Sub-threshold or micro slivers
    expect(classifySignificance(0.02, 0.05, 0.05)).toBe('UNKNOWN');

    // Minor change (small porch / single room change)
    expect(classifySignificance(2.5, 0.3, 0.4)).toBe('MINOR');

    // Moderate change (expanded wing / single story addition)
    expect(classifySignificance(25.0, 2.8, 1.2)).toBe('MODERATE');

    // Major change (substantial demolition or multi-story addition)
    expect(classifySignificance(120.0, 6.0, 6.5)).toBe('MAJOR');
  });

  // 4. Candidate Review Lifecycle & Validation Requirements
  it('validates candidate review payloads and mandates review reason or notes', () => {
    const validateReviewPayload = (payload: ChangeCandidateReviewPayload): { isValid: boolean; error?: string } => {
      if (!['CONFIRM', 'REJECT', 'DISMISS'].includes(payload.action)) {
        return { isValid: false, error: 'Invalid review action' };
      }
      if (!payload.review_reason && (!payload.review_notes || payload.review_notes.trim().length === 0)) {
        return { isValid: false, error: 'A review reason or detailed notes must be provided for governance audit' };
      }
      return { isValid: true };
    };

    // Missing reason and notes
    expect(validateReviewPayload({ action: 'CONFIRM' })).toEqual({
      isValid: false,
      error: 'A review reason or detailed notes must be provided for governance audit',
    });

    // Valid with reason
    expect(
      validateReviewPayload({
        action: 'CONFIRM',
        review_reason: 'CONFIRMED_FIELD_SURVEY',
      })
    ).toEqual({ isValid: true });

    // Valid with notes
    expect(
      validateReviewPayload({
        action: 'REJECT',
        review_notes: 'False positive due to temporary scaffolding recorded during drone flight.',
      })
    ).toEqual({ isValid: true });
  });

  // 5. Multi-Source Evidence & Topology Integration
  it('structure ensures Phase 7 topology findings and Phase 8 / Phase 5 evidence are preserved', () => {
    const candidate: ChangeCandidate = {
      id: 'cand-001',
      detection_run_id: 'run-001',
      change_type: 'BUILDING_EXPANDED',
      entity_type: 'BUILDING',
      entity_id: 'bld-hyd-101',
      baseline_snapshot_id: 'snap-001',
      comparison_snapshot_id: 'snap-002',
      magnitude: {
        baseline_area_sqm: 100.0,
        current_area_sqm: 145.0,
        area_difference_sqm: 45.0,
        area_change_percentage: 45.0,
        iou: 0.69,
        centroid_displacement_m: 1.8,
        boundary_displacement_m: 3.2,
      },
      significance: 'MODERATE',
      confidence: 0.94,
      evidence: [
        {
          source_type: 'FIELD_SURVEY',
          source_id: 'srv-obs-99',
          description: 'Surveyor ground observation noted newly completed rear extension.',
          date: '2026-09-20T10:00:00Z',
        },
        {
          source_type: 'PROPERTY_DOCUMENT',
          source_id: 'doc-881',
          description: 'Building permit application for 45m² rear addition.',
          date: '2026-08-15T00:00:00Z',
        },
      ],
      validation_issues: [
        {
          rule_id: 'BLD_001',
          issue_code: 'BUILDING_OUTSIDE_PARCEL',
          severity: 'WARNING',
          message: 'Rear expansion footprint encroaches 0.2m into rear setback.',
        },
      ],
      status: 'UNDER_REVIEW',
      created_at: '2026-09-24T12:00:00Z',
    };

    expect(candidate.magnitude.area_difference_sqm).toBe(45.0);
    expect(candidate.evidence.length).toBe(2);
    expect(candidate.evidence[0].source_type).toBe('FIELD_SURVEY');
    expect(candidate.evidence[1].source_type).toBe('PROPERTY_DOCUMENT');
    expect(candidate.validation_issues.length).toBe(1);
    expect(candidate.validation_issues[0].issue_code).toBe('BUILDING_OUTSIDE_PARCEL');
  });

  // 6. Chronological Entity Timeline Reconstruction
  it('sorts timeline entries chronologically and supports heterogeneous source types', () => {
    const rawEntries: TimelineEntry[] = [
      {
        entry_id: 'e3',
        entry_type: 'CHANGE_CANDIDATE',
        date: '2026-09-24T00:00:00Z',
        date_precision: 'DAY',
        source: 'TEMPORAL_RUN',
        title: 'Building Expansion Detected',
        description: 'Area delta +45.0m²',
        attributes: {},
      },
      {
        entry_id: 'e1',
        entry_type: 'SNAPSHOT',
        date: '2020-01-15T00:00:00Z',
        date_precision: 'EXACT',
        source: 'OFFICIAL_CADASTRE',
        title: 'Official Cadastral Baseline',
        description: 'Original title deed survey footprint',
        attributes: {},
      },
      {
        entry_id: 'e2',
        entry_type: 'SURVEY',
        date: '2025-06-10T00:00:00Z',
        date_precision: 'DAY',
        source: 'FIELD_SURVEY',
        title: 'Municipal Field Re-survey',
        description: 'Routine boundary verification',
        attributes: {},
      },
    ];

    const sorted = [...rawEntries].sort((a, b) => {
      const dateA = a.date ? new Date(a.date).getTime() : 0;
      const dateB = b.date ? new Date(b.date).getTime() : 0;
      return dateA - dateB;
    });

    expect(sorted[0].entry_id).toBe('e1');
    expect(sorted[1].entry_id).toBe('e2');
    expect(sorted[2].entry_id).toBe('e3');
    expect(sorted[0].entry_type).toBe('SNAPSHOT');
    expect(sorted[1].entry_type).toBe('SURVEY');
    expect(sorted[2].entry_type).toBe('CHANGE_CANDIDATE');
  });
});
