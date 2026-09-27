import { describe, it, expect } from 'vitest';
import { UserRole } from '../types';
import {
  AssetReviewStatus,
  ClashSeverity,
  ClashStatus,
  ClashType,
  QualityLevel,
  UtilityAsset,
  UtilityClash,
  UtilityNetwork,
  UtilityType,
} from '../types/utility';

describe('GeoVertex Phase 10 - Underground Infrastructure & Subsurface Utility Intelligence', () => {
  // 1. Role-Based Access Control (RBAC)
  it('enforces strict RBAC for subsurface utility viewing, network creation, clash detection, and review', () => {
    const canViewSubsurface = (role: UserRole) => {
      return ['ADMIN', 'GOVERNMENT_OFFICER', 'SURVEYOR', 'URBAN_PLANNER'].includes(role);
    };

    const canCreateNetwork = (role: UserRole) => {
      return ['ADMIN', 'GOVERNMENT_OFFICER'].includes(role);
    };

    const canReviewCandidate = (role: UserRole) => {
      // Official validation and incorporation into official cadastre requires officer/admin authority
      return ['ADMIN', 'GOVERNMENT_OFFICER'].includes(role);
    };

    const canRunClashDetection = (role: UserRole) => {
      return ['ADMIN', 'GOVERNMENT_OFFICER', 'SURVEYOR', 'URBAN_PLANNER'].includes(role);
    };

    // Citizen
    expect(canViewSubsurface('CITIZEN')).toBe(false);
    expect(canCreateNetwork('CITIZEN')).toBe(false);
    expect(canReviewCandidate('CITIZEN')).toBe(false);
    expect(canRunClashDetection('CITIZEN')).toBe(false);

    // Surveyor
    expect(canViewSubsurface('SURVEYOR')).toBe(true);
    expect(canCreateNetwork('SURVEYOR')).toBe(false);
    expect(canReviewCandidate('SURVEYOR')).toBe(false);
    expect(canRunClashDetection('SURVEYOR')).toBe(true);

    // Urban Planner
    expect(canViewSubsurface('URBAN_PLANNER')).toBe(true);
    expect(canCreateNetwork('URBAN_PLANNER')).toBe(false);
    expect(canReviewCandidate('URBAN_PLANNER')).toBe(false);
    expect(canRunClashDetection('URBAN_PLANNER')).toBe(true);

    // Government Officer
    expect(canViewSubsurface('GOVERNMENT_OFFICER')).toBe(true);
    expect(canCreateNetwork('GOVERNMENT_OFFICER')).toBe(true);
    expect(canReviewCandidate('GOVERNMENT_OFFICER')).toBe(true);
    expect(canRunClashDetection('GOVERNMENT_OFFICER')).toBe(true);

    // Admin
    expect(canViewSubsurface('ADMIN')).toBe(true);
    expect(canCreateNetwork('ADMIN')).toBe(true);
    expect(canReviewCandidate('ADMIN')).toBe(true);
    expect(canRunClashDetection('ADMIN')).toBe(true);
  });

  // 2. Depth and Vertical Reference Model
  it('correctly models vertical elevation and depth without fabricating missing values', () => {
    const calculateDepth = (groundZ?: number, centerlineZ?: number) => {
      if (groundZ === undefined || centerlineZ === undefined || groundZ === null || centerlineZ === null) {
        return { depth: undefined, status: 'UNKNOWN_DEPTH' };
      }
      if (centerlineZ > groundZ) {
        return { depth: undefined, status: 'INVALID_ELEVATION_ABOVE_GROUND' };
      }
      return { depth: parseFloat((groundZ - centerlineZ).toFixed(3)), status: 'VALID' };
    };

    // Valid subsurface pipeline
    const valid = calculateDepth(100.0, 97.65);
    expect(valid.status).toBe('VALID');
    expect(valid.depth).toBe(2.35);

    // Missing depth values - must NOT be fabricated
    const missingCenterline = calculateDepth(100.0, undefined);
    expect(missingCenterline.status).toBe('UNKNOWN_DEPTH');
    expect(missingCenterline.depth).toBeUndefined();

    const missingGround = calculateDepth(undefined, 95.0);
    expect(missingGround.status).toBe('UNKNOWN_DEPTH');
    expect(missingGround.depth).toBeUndefined();

    // Inverted elevation (centerline above ground)
    const inverted = calculateDepth(100.0, 102.5);
    expect(inverted.status).toBe('INVALID_ELEVATION_ABOVE_GROUND');
    expect(inverted.depth).toBeUndefined();
  });

  // 3. Subsurface Quality Levels (ASCE 38 Standards)
  it('enforces quality levels QL-A through QL-D based on positioning accuracy and method', () => {
    const assignQualityLevel = (method: 'EXCAVATION' | 'GEOPHYSICAL_SURVEY' | 'SURFACE_FEATURE' | 'RECORD_DRAWING'): QualityLevel => {
      switch (method) {
        case 'EXCAVATION':
          return 'QL-A'; // Exact 3D physical exposure (vacuum excavation)
        case 'GEOPHYSICAL_SURVEY':
          return 'QL-B'; // 2D/3D subsurface geophysics (GPR, electromagnetic)
        case 'SURFACE_FEATURE':
          return 'QL-C'; // Surface survey of appurtenances (manholes, valves)
        case 'RECORD_DRAWING':
        default:
          return 'QL-D'; // Historical records, as-builts, unverified schematics
      }
    };

    expect(assignQualityLevel('EXCAVATION')).toBe('QL-A');
    expect(assignQualityLevel('GEOPHYSICAL_SURVEY')).toBe('QL-B');
    expect(assignQualityLevel('SURFACE_FEATURE')).toBe('QL-C');
    expect(assignQualityLevel('RECORD_DRAWING')).toBe('QL-D');
  });

  // 4. Cadastral Spatial Intersections: Geometry Only, No Unauthorized Easements
  it('reports technical parcel crossing length strictly as geometry without declaring legal easements', () => {
    interface ParcelIntersectionResult {
      parcel_id: string;
      crosses_parcel: boolean;
      intersection_length_m: number;
      is_legal_easement_declared: boolean;
      legal_disclaimer: string;
    }

    const analyzeParcelCrossing = (parcelId: string, segmentLengthWithinParcel: number): ParcelIntersectionResult => {
      return {
        parcel_id: parcelId,
        crosses_parcel: segmentLengthWithinParcel > 0,
        intersection_length_m: parseFloat(segmentLengthWithinParcel.toFixed(2)),
        is_legal_easement_declared: false, // Strict governance: do not declare legal easements automatically
        legal_disclaimer:
          'Technical spatial intersection only. Does not infer legal easement, right-of-way, or cadastral servitude.',
      };
    };

    const result = analyzeParcelCrossing('PARCEL-001', 34.78);
    expect(result.crosses_parcel).toBe(true);
    expect(result.intersection_length_m).toBe(34.78);
    expect(result.is_legal_easement_declared).toBe(false);
    expect(result.legal_disclaimer).toContain('Technical spatial intersection only');
  });

  // 5. Building Basement and Foundation Proximity
  it('determines vertical proximity between building basements and subsurface utility lines', () => {
    const checkBasementInteraction = (
      utilityCenterlineZ: number,
      basementLowestZ: number,
      horizontalDistanceM: number
    ) => {
      const isUnderneath = horizontalDistanceM < 0.5 && utilityCenterlineZ < basementLowestZ;
      const verticalClearance = Math.abs(utilityCenterlineZ - basementLowestZ);
      return {
        isUnderneath,
        verticalClearanceM: parseFloat(verticalClearance.toFixed(2)),
        conflictRisk: isUnderneath && verticalClearance < 1.0 ? 'HIGH' : 'LOW',
      };
    };

    // Deep sewer passing 0.4m under basement slab
    const highRisk = checkBasementInteraction(90.6, 91.0, 0.2);
    expect(highRisk.isUnderneath).toBe(true);
    expect(highRisk.verticalClearanceM).toBe(0.4);
    expect(highRisk.conflictRisk).toBe('HIGH');

    // Utility safely below basement
    const safeBelow = checkBasementInteraction(85.0, 95.0, 0.1);
    expect(safeBelow.isUnderneath).toBe(true);
    expect(safeBelow.verticalClearanceM).toBe(10.0);
    expect(safeBelow.conflictRisk).toBe('LOW');
  });

  // 6. 3D Clash Detection & Configurable Separation Rules
  it('evaluates 3D clash separation rules and falls back to SEPARATION_RULE_NOT_CONFIGURED', () => {
    interface SeparationRule {
      utility_type_1: UtilityType;
      utility_type_2: UtilityType;
      min_horizontal_separation_m: number;
      min_vertical_separation_m: number;
      rule_code: string;
    }

    const rules: SeparationRule[] = [
      {
        utility_type_1: 'WATER',
        utility_type_2: 'SEWER',
        min_horizontal_separation_m: 3.0,
        min_vertical_separation_m: 0.5,
        rule_code: 'MUNI-SEP-001',
      },
    ];

    const evaluateSeparation = (
      type1: UtilityType,
      type2: UtilityType,
      actualHorizontalM: number,
      actualVerticalM: number
    ) => {
      const rule = rules.find(
        (r) =>
          (r.utility_type_1 === type1 && r.utility_type_2 === type2) ||
          (r.utility_type_1 === type2 && r.utility_type_2 === type1)
      );

      if (!rule) {
        const isPhysicalIntersection = actualHorizontalM < 0.1 && actualVerticalM < 0.1;
        return {
          clash: isPhysicalIntersection,
          severity: isPhysicalIntersection ? ('CRITICAL' as ClashSeverity) : ('NONE' as any),
          rule_code: 'SEPARATION_RULE_NOT_CONFIGURED',
        };
      }

      const hViolation = actualHorizontalM < rule.min_horizontal_separation_m;
      const vViolation = actualVerticalM < rule.min_vertical_separation_m;

      if (hViolation || vViolation) {
        return {
          clash: true,
          severity: actualHorizontalM < 0.5 ? ('CRITICAL' as ClashSeverity) : ('MAJOR' as ClashSeverity),
          rule_code: rule.rule_code,
          required_horizontal_m: rule.min_horizontal_separation_m,
          required_vertical_m: rule.min_vertical_separation_m,
        };
      }

      return { clash: false, severity: 'NONE' as any, rule_code: rule.rule_code };
    };

    // Water and Sewer violation
    const violation = evaluateSeparation('WATER', 'SEWER', 1.5, 0.2);
    expect(violation.clash).toBe(true);
    expect(violation.rule_code).toBe('MUNI-SEP-001');

    // Unconfigured rule: Water and Gas with no municipal rule
    const unconfiguredNoClash = evaluateSeparation('WATER', 'GAS', 1.2, 0.8);
    expect(unconfiguredNoClash.clash).toBe(false);
    expect(unconfiguredNoClash.rule_code).toBe('SEPARATION_RULE_NOT_CONFIGURED');

    // Unconfigured rule but direct physical intersection
    const physicalDirect = evaluateSeparation('WATER', 'GAS', 0.0, 0.0);
    expect(physicalDirect.clash).toBe(true);
    expect(physicalDirect.severity).toBe('CRITICAL');
    expect(physicalDirect.rule_code).toBe('SEPARATION_RULE_NOT_CONFIGURED');
  });

  // 7. Strict "No Fake AI" Detector Behavior
  it('returns MODEL_NOT_CONFIGURED when subsurface utility AI weights are absent', () => {
    const runAIUtilityExtraction = (weightsPath: string | null) => {
      if (!weightsPath) {
        return {
          status: 'MODEL_NOT_CONFIGURED',
          message: 'AI utility detection weights not configured. Automated feature fabrication prohibited.',
          candidate_features: [],
        };
      }
      return {
        status: 'READY',
        message: 'Weights loaded',
        candidate_features: [{ id: 'UTL-AI-01' }],
      };
    };

    const res = runAIUtilityExtraction(null);
    expect(res.status).toBe('MODEL_NOT_CONFIGURED');
    expect(res.candidate_features.length).toBe(0);
    expect(res.message).toContain('Automated feature fabrication prohibited');
  });

  // 8. Controlled Update Audit Trail
  it('requires reason and source reference for any controlled updates on utility records', () => {
    const validateControlledUpdate = (payload: { reason?: string; source_reference?: string; updates: any }) => {
      if (!payload.reason || payload.reason.trim().length === 0) {
        throw new Error('Controlled update requires an explicit engineering or survey reason');
      }
      if (!payload.source_reference || payload.source_reference.trim().length === 0) {
        throw new Error('Controlled update requires a valid source reference (e.g. As-Built Drawing #)');
      }
      return true;
    };

    expect(() =>
      validateControlledUpdate({
        reason: '',
        source_reference: 'DWG-902',
        updates: { depth_m: 2.1 },
      })
    ).toThrow('requires an explicit engineering or survey reason');

    expect(() =>
      validateControlledUpdate({
        reason: 'Correction of pipe centerline from field survey',
        source_reference: '',
        updates: { depth_m: 2.1 },
      })
    ).toThrow('requires a valid source reference');

    expect(
      validateControlledUpdate({
        reason: 'Correction of pipe centerline from field survey',
        source_reference: 'SURVEY-2026-09-A',
        updates: { depth_m: 2.1 },
      })
    ).toBe(true);
  });
});
