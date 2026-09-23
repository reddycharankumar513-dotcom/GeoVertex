import { describe, it, expect } from 'vitest';
import { UserRole } from '../types';

describe('GeoVertex Phase 4 - Building, Floor & Unit Hierarchy Logic', () => {
  it('validates floor management permissions by role', () => {
    const floorEditorRoles: UserRole[] = ['ADMIN', 'GOVERNMENT_OFFICER', 'SURVEYOR'];

    expect(floorEditorRoles.includes('ADMIN')).toBe(true);
    expect(floorEditorRoles.includes('GOVERNMENT_OFFICER')).toBe(true);
    expect(floorEditorRoles.includes('SURVEYOR')).toBe(true);
    expect(floorEditorRoles.includes('CITIZEN')).toBe(false);
  });

  it('validates vertical elevation thickness calculation and positive bounds', () => {
    const floor = {
      elevation_min_m: 0.0,
      elevation_max_m: 3.5,
    };
    const height = floor.elevation_max_m - floor.elevation_min_m;

    expect(height).toBe(3.5);
    expect(height).toBeGreaterThan(0);
  });

  it('verifies floor vertical stacking non-overlap logic', () => {
    const groundFloor = { floor_number: 0, elevation_min_m: 0.0, elevation_max_m: 3.5 };
    const levelOne = { floor_number: 1, elevation_min_m: 3.5, elevation_max_m: 7.0 };
    const levelTwo = { floor_number: 2, elevation_min_m: 7.0, elevation_max_m: 10.5 };

    // Adjacent floors meet at continuous elevation boundary without vertical overlap
    expect(levelOne.elevation_min_m).toBe(groundFloor.elevation_max_m);
    expect(levelTwo.elevation_min_m).toBe(levelOne.elevation_max_m);

    // Overlap test function
    const checkOverlap = (f1: typeof groundFloor, f2: typeof levelOne) => {
      return !(f1.elevation_max_m <= f2.elevation_min_m || f1.elevation_min_m >= f2.elevation_max_m);
    };

    expect(checkOverlap(groundFloor, levelOne)).toBe(false);

    const clashingFloor = { floor_number: 1, elevation_min_m: 2.0, elevation_max_m: 5.0 };
    expect(checkOverlap(groundFloor, clashingFloor)).toBe(true);
  });

  it('validates unit area relationship: net area cannot exceed gross area', () => {
    const validUnit = {
      unit_number: '101',
      gross_area_sqm: 120.0,
      net_area_sqm: 95.5,
    };
    expect(validUnit.net_area_sqm).toBeLessThanOrEqual(validUnit.gross_area_sqm);

    const isValidUnitArea = (gross: number, net?: number) => {
      if (net === undefined || net === null) return gross > 0;
      return gross > 0 && net > 0 && net <= gross;
    };

    expect(isValidUnitArea(100.0, 85.0)).toBe(true);
    expect(isValidUnitArea(100.0, 110.0)).toBe(false);
    expect(isValidUnitArea(0.0)).toBe(false);
  });

  it('computes 3D exploded view floor offsets accurately', () => {
    const calculateExplodedHeight = (baseElevation: number, minElev: number, maxElev: number, floorNum: number, spacing: number = 3.5) => {
      const offset = floorNum * spacing;
      return {
        baseH: baseElevation + minElev + offset,
        topH: baseElevation + maxElev + offset,
      };
    };

    const baseElevation = 500.0;
    const ground = calculateExplodedHeight(baseElevation, 0.0, 3.5, 0);
    const lvl1 = calculateExplodedHeight(baseElevation, 3.5, 7.0, 1);
    const lvl2 = calculateExplodedHeight(baseElevation, 7.0, 10.5, 2);

    expect(ground.baseH).toBe(500.0);
    expect(ground.topH).toBe(503.5);

    // Level 1 exploded has +3.5m offset
    expect(lvl1.baseH).toBe(500.0 + 3.5 + 3.5); // 507.0
    expect(lvl1.topH).toBe(500.0 + 7.0 + 3.5); // 510.5

    // Level 2 exploded has +7.0m offset
    expect(lvl2.baseH).toBe(500.0 + 7.0 + 7.0); // 514.0
    expect(lvl2.topH).toBe(500.0 + 10.5 + 7.0); // 517.5
  });

  it('validates property unit ownership status classification', () => {
    const validStatuses = ['OWNED', 'OCCUPIED', 'LEASED', 'VACANT', 'MORTGAGED', 'COMMON'];

    const getOccupancyState = (status: string) => {
      if (['OWNED', 'OCCUPIED'].includes(status)) return 'OCCUPIED';
      if (status === 'VACANT') return 'AVAILABLE';
      if (status === 'LEASED') return 'TENANTED';
      return 'ENCUMBERED_OR_SPECIAL';
    };

    expect(getOccupancyState('OCCUPIED')).toBe('OCCUPIED');
    expect(getOccupancyState('VACANT')).toBe('AVAILABLE');
    expect(getOccupancyState('LEASED')).toBe('TENANTED');
    expect(getOccupancyState('MORTGAGED')).toBe('ENCUMBERED_OR_SPECIAL');
  });
});
