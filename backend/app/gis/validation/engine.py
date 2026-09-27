import time
from typing import Any, Dict, List, Optional
from app.gis.validation.base import IssueDraft, ValidationContext
from app.gis.validation.registry import rule_registry
from app.gis.validation.tolerances import ValidationToleranceConfig, default_tolerances


class ValidationEngine:
    """Authoritative deterministic validation engine orchestrating rule execution across cadastral scopes."""

    def __init__(self, registry=rule_registry):
        self.registry = registry

    def execute_validation(
        self,
        context: ValidationContext,
        rule_ids_filter: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Executes applicable validation rules against the context and produces deterministic findings and summary."""
        start_time = time.perf_counter()

        # 1. Rule Selection
        applicable_rules = self.registry.get_rules_for_target(
            target_type=context.target_type,
            rule_ids_filter=rule_ids_filter,
        )

        all_issues: List[IssueDraft] = []
        rules_executed_count = 0

        # 2. Sequential Deterministic Rule Execution
        for rule in applicable_rules:
            try:
                rule_issues = rule.validate(context)
                all_issues.extend(rule_issues)
                rules_executed_count += 1
            except Exception as e:
                # Log execution anomaly as an issue if a rule errors
                all_issues.append(IssueDraft(
                    rule_id=rule.rule_id,
                    rule_version=rule.rule_version,
                    issue_code="SYS-001",
                    category=rule.category,
                    severity="ERROR",
                    entity_type=context.target_type,
                    entity_id=str(context.target_id or "UNKNOWN"),
                    message=f"Rule {rule.rule_id} execution exception: {str(e)}",
                    technical_explanation=f"Internal rule execution error: {str(e)}",
                ))

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # 3. Calculate Deterministic Summary
        critical_count = sum(1 for i in all_issues if i.severity == "CRITICAL")
        error_count = sum(1 for i in all_issues if i.severity == "ERROR")
        warning_count = sum(1 for i in all_issues if i.severity == "WARNING")
        info_count = sum(1 for i in all_issues if i.severity == "INFO")

        entities_checked = (
            len(context.parcels) +
            len(context.buildings) +
            len(context.floors) +
            len(context.units) +
            len(context.ai_building_candidates) +
            len(context.survey_observations)
        )
        if entities_checked == 0 and context.raw_geometries:
            entities_checked = len(context.raw_geometries)

        summary = {
            "total_issues": len(all_issues),
            "critical": critical_count,
            "errors": error_count,
            "warnings": warning_count,
            "info": info_count,
            "resolved": 0,
            "open": len(all_issues),
            "waived": 0,
            "acknowledged": 0,
            "rules_executed": rules_executed_count,
            "entities_checked": max(entities_checked, 1),
            "execution_time_ms": duration_ms,
        }

        return {
            "summary": summary,
            "issues": all_issues,
            "duration_ms": duration_ms,
            "rules_executed_count": rules_executed_count,
        }


# Global validation engine instance
validation_engine = ValidationEngine()
