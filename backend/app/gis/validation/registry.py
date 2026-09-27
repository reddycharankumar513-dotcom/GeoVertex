from typing import Dict, List, Optional
from app.gis.validation.base import ValidationRule


class ValidationRuleRegistry:
    """Registry maintaining active and versioned validation rules."""

    def __init__(self):
        self._rules: Dict[str, ValidationRule] = {}

    def register(self, rule: ValidationRule) -> None:
        """Register a validation rule."""
        self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> Optional[ValidationRule]:
        """Fetch a registered rule by its unique ID."""
        return self._rules.get(rule_id)

    def list_rules(
        self,
        category: Optional[str] = None,
        target_type: Optional[str] = None,
    ) -> List[ValidationRule]:
        """List rules with optional filtering by category or target type."""
        rules = list(self._rules.values())
        if category:
            rules = [r for r in rules if r.category.upper() == category.upper()]
        if target_type:
            rules = [r for r in rules if r.applies_to(target_type)]
        return rules

    def get_rules_for_target(self, target_type: str, rule_ids_filter: Optional[List[str]] = None) -> List[ValidationRule]:
        """Get all rules that apply to a specific target type, optionally filtered by ID list."""
        applicable = [r for r in self._rules.values() if r.applies_to(target_type)]
        if rule_ids_filter:
            applicable = [r for r in applicable if r.rule_id in rule_ids_filter]
        return applicable


# Global rule registry singleton
rule_registry = ValidationRuleRegistry()
