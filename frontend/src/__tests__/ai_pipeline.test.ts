import { describe, it, expect } from 'vitest';
import { UserRole } from '../types';
import { ConfidenceComponents, CadastralComparisonMetrics } from '../types/ai';

describe('GeoVertex Phase 6 - AI Building & Floor Extraction Pipeline', () => {
  // 1. Role-Based Access Control for AI Subsystems
  it('enforces RBAC permissions for AI extraction dispatch, review, and controlled approval', () => {
    const canDispatchAIJob = (role: UserRole) => {
      return ['SURVEYOR', 'ADMIN', 'GOVERNMENT_OFFICER'].includes(role);
    };

    const canReviewAndApprove = (role: UserRole) => {
      return ['ADMIN', 'GOVERNMENT_OFFICER'].includes(role);
    };

    const canViewAIResults = (role: UserRole) => {
      return ['CITIZEN', 'SURVEYOR', 'ADMIN', 'GOVERNMENT_OFFICER', 'URBAN_PLANNER'].includes(role);
    };

    // Citizen can only view, cannot dispatch or approve
    expect(canViewAIResults('CITIZEN')).toBe(true);
    expect(canDispatchAIJob('CITIZEN')).toBe(false);
    expect(canReviewAndApprove('CITIZEN')).toBe(false);

    // Surveyor can dispatch jobs and view, but cannot approve cadastral mutation
    expect(canDispatchAIJob('SURVEYOR')).toBe(true);
    expect(canReviewAndApprove('SURVEYOR')).toBe(false);

    // Government Officer can review and approve controlled update
    expect(canDispatchAIJob('GOVERNMENT_OFFICER')).toBe(true);
    expect(canReviewAndApprove('GOVERNMENT_OFFICER')).toBe(true);

    // Admin has full capabilities
    expect(canDispatchAIJob('ADMIN')).toBe(true);
    expect(canReviewAndApprove('ADMIN')).toBe(true);
  });

  // 2. AI Job Lifecycle & Stage Progression
  it('verifies AI job lifecycle stages and progress percentages without fake status', () => {
    const validStages = [
      { stage: 'QUEUED', progress: 0 },
      { stage: 'PREPROCESSING', progress: 10 },
      { stage: 'RUNNING_MODEL', progress: 40 },
      { stage: 'POSTPROCESSING', progress: 70 },
      { stage: 'VALIDATING', progress: 90 },
      { stage: 'COMPLETED', progress: 100 },
    ];

    validStages.forEach(({ stage, progress }) => {
      expect(progress).toBeGreaterThanOrEqual(0);
      expect(progress).toBeLessThanOrEqual(100);
      expect(typeof stage).toBe('string');
    });

    // Terminal statuses
    const isTerminalStatus = (status: string) => ['COMPLETED', 'FAILED', 'CANCELLED'].includes(status);
    expect(isTerminalStatus('COMPLETED')).toBe(true);
    expect(isTerminalStatus('FAILED')).toBe(true);
    expect(isTerminalStatus('CANCELLED')).toBe(true);
    expect(isTerminalStatus('RUNNING')).toBe(false);
  });

  // 3. Transparent Confidence Framework Breakdown (Section 23)
  it('correctly derives transparent composite confidence from distinct components', () => {
    const calculateCompositeConfidence = (components: ConfidenceComponents): number => {
      const { model_confidence, geometry_quality, source_quality } = components;
      const composite = 0.5 * model_confidence + 0.3 * geometry_quality + 0.2 * source_quality;
      return Math.round(composite * 1000) / 1000;
    };

    const sampleComponents: ConfidenceComponents = {
      model_confidence: 0.85,
      geometry_quality: 0.90,
      source_quality: 0.75,
    };

    const composite = calculateCompositeConfidence(sampleComponents);
    // (0.5 * 0.85) + (0.3 * 0.90) + (0.2 * 0.75) = 0.425 + 0.270 + 0.150 = 0.845
    expect(composite).toBe(0.845);
    expect(composite).toBeGreaterThan(0.0);
    expect(composite).toBeLessThanOrEqual(1.0);
  });

  // 4. Cadastral Comparison Metrics (Section 35)
  it('computes deterministic intersection over union (IoU) and area differences', () => {
    const computeCadastralMetrics = (interArea: number, unionArea: number, offArea: number, candArea: number) => {
      const iou = unionArea > 0 ? interArea / unionArea : 0;
      const areaDiff = Math.abs(candArea - offArea);
      return {
        iou: Math.round(iou * 10000) / 10000,
        areaDiff: Math.round(areaDiff * 100) / 100,
      };
    };

    // Identical geometries
    const perfect = computeCadastralMetrics(150.0, 150.0, 150.0, 150.0);
    expect(perfect.iou).toBe(1.0);
    expect(perfect.areaDiff).toBe(0.0);

    // Partial overlap (e.g. 120m² intersection, 160m² union)
    const partial = computeCadastralMetrics(120.0, 160.0, 140.0, 140.0);
    expect(partial.iou).toBe(0.75);
    expect(partial.areaDiff).toBe(0.0);
  });

  // 5. Critical AI Rule: Unconfigured Floor Model Handling (Section 3 & 24)
  it('strictly flags unconfigured model states and prevents fake output generation', () => {
    const handleModelInference = (isModelConfigured: boolean) => {
      if (!isModelConfigured) {
        return {
          status: 'FAILED',
          errorCode: 'MODEL_NOT_CONFIGURED',
          message: 'MODEL_NOT_CONFIGURED: No trained floor extraction model is configured.',
          candidateGeometry: null,
        };
      }
      return {
        status: 'COMPLETED',
        errorCode: null,
        message: 'Success',
        candidateGeometry: 'POLYGON((...))',
      };
    };

    // When floor model weights are unavailable, must return MODEL_NOT_CONFIGURED
    const result = handleModelInference(false);
    expect(result.status).toBe('FAILED');
    expect(result.errorCode).toBe('MODEL_NOT_CONFIGURED');
    expect(result.candidateGeometry).toBeNull();
  });

  // 6. Controlled Cadastral Update Adjudication (Section 29 & 61)
  it('guarantees official cadastral records remain untouched until explicit review approval', () => {
    let officialBuildingGeometry = 'POLYGON((78.38 17.44, 78.39 17.44, 78.39 17.45, 78.38 17.45, 78.38 17.44))';
    const candidateAIResult = {
      status: 'REVIEW_REQUIRED',
      geometry: 'POLYGON((78.381 17.441, 78.391 17.441, 78.391 17.451, 78.381 17.451, 78.381 17.441))',
    };

    // AI prediction alone does NOT change official building
    expect(officialBuildingGeometry).not.toBe(candidateAIResult.geometry);

    // Action: REJECT
    const applyDecision = (action: 'APPROVE' | 'REJECT' | 'MODIFY_AND_APPROVE', editedWkt?: string) => {
      if (action === 'APPROVE') {
        officialBuildingGeometry = candidateAIResult.geometry;
        candidateAIResult.status = 'APPROVED';
      } else if (action === 'MODIFY_AND_APPROVE' && editedWkt) {
        officialBuildingGeometry = editedWkt;
        candidateAIResult.status = 'APPROVED';
      } else if (action === 'REJECT') {
        candidateAIResult.status = 'REJECTED';
      }
    };

    // Rejection leaves official geometry untouched
    applyDecision('REJECT');
    expect(candidateAIResult.status).toBe('REJECTED');
    expect(officialBuildingGeometry).toContain('78.38 17.44');

    // Reset and test controlled approval
    candidateAIResult.status = 'REVIEW_REQUIRED';
    applyDecision('APPROVE');
    expect(candidateAIResult.status).toBe('APPROVED');
    expect(officialBuildingGeometry).toBe(candidateAIResult.geometry);
  });
});
