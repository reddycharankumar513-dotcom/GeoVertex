from typing import Any, Dict, List
from collections import defaultdict
from app.gis.validation.base import IssueDraft, ValidationContext, ValidationRule


class VerticalStackingRule(ValidationRule):
    rule_id = "VERTICAL_STACK_CONSISTENCY"
    name = "Vertical Stacking & Building Height Consistency"
    description = "Checks that unit vertical ranges [z_min, z_max] are contained in parent floor ranges, and building vertical envelope encloses all floors."
    category = "VERTICAL"
    severity = "ERROR"

    def applies_to(self, target_type: str) -> bool:
        return target_type in ["BUILDING", "FLOOR", "UNIT", "SYSTEM"]

    def validate(self, context: ValidationContext) -> List[IssueDraft]:
        issues = []
        floor_map = {str(f.id): f for f in context.floors}
        tol = context.tolerances.vertical_elevation_tolerance_m

        # 1. Unit vertical containment inside floor
        for u in context.units:
            fl_id = getattr(u, "floor_id", None)
            if not fl_id or str(fl_id) not in floor_map:
                continue
            fl = floor_map[str(fl_id)]
            u_min = getattr(u, "elevation_min_m", None)
            u_max = getattr(u, "elevation_max_m", None)
            f_min = getattr(fl, "elevation_min_m", None)
            f_max = getattr(fl, "elevation_max_m", None)

            if u_min is not None and u_max is not None and f_min is not None and f_max is not None:
                if u_min < (f_min - tol) or u_max > (f_max + tol):
                    u_code = getattr(u, "unit_code", str(u.id))
                    fl_code = getattr(fl, "floor_code", str(fl.id))
                    issues.append(IssueDraft(
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        issue_code="VRT-001",
                        category=self.category,
                        severity=self.severity,
                        entity_type="UNIT",
                        entity_id=str(u.id),
                        related_entity_type="FLOOR",
                        related_entity_id=str(fl.id),
                        message=f"Unit {u_code} vertical range [{u_min:.2f}m, {u_max:.2f}m] exceeds floor {fl_code} range [{f_min:.2f}m, {f_max:.2f}m].",
                        technical_explanation=f"Vertical containment violation: Unit [{u_min:.2f}m, {u_max:.2f}m] is not within floor vertical bounds [{f_min:.2f}m, {f_max:.2f}m].",
                        measured_value=f"[{u_min:.2f}m, {u_max:.2f}m]",
                        expected_value=f"Inside [{f_min:.2f}m, {f_max:.2f}m]",
                        tolerance=f"{tol:.2f}m",
                    ))

        # 2. Building envelope vs floor elevation span
        bld_map = {str(b.id): b for b in context.buildings}
        bld_floors = defaultdict(list)
        for f in context.floors:
            b_id = getattr(f, "building_id", None)
            if b_id:
                bld_floors[str(b_id)].append(f)

        for b_id, flist in bld_floors.items():
            if b_id not in bld_map:
                continue
            b = bld_map[b_id]
            b_height = getattr(b, "height_estimate", None) or getattr(b, "height", None) or getattr(b, "total_height", None)
            if b_height and b_height > 0:
                elevs = [f.elevation_max_m for f in flist if getattr(f, "elevation_max_m", None) is not None]
                base_elevs = [f.elevation_min_m for f in flist if getattr(f, "elevation_min_m", None) is not None]
                if elevs and base_elevs:
                    top_elev = max(elevs)
                    lowest_elev = min(base_elevs)
                    floor_stack_height = top_elev - lowest_elev
                    # If floor stack exceeds building height by > 1.5m
                    if floor_stack_height > (b_height + 1.5):
                        b_ref = getattr(b, "building_reference", b.id)
                        issues.append(IssueDraft(
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            issue_code="VRT-002",
                            category=self.category,
                            severity="WARNING",
                            entity_type="BUILDING",
                            entity_id=str(b.id),
                            message=f"Building {b_ref} recorded height ({b_height:.2f}m) is less than its cumulative floor stack height ({floor_stack_height:.2f}m).",
                            technical_explanation=f"Floors span [{lowest_elev:.2f}m to {top_elev:.2f}m] = {floor_stack_height:.2f}m, exceeding recorded building height {b_height:.2f}m.",
                            measured_value=f"{floor_stack_height:.2f}m",
                            expected_value=f"<= {b_height:.2f}m",
                        ))
        return issues
