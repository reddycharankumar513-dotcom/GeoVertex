from typing import Any, Dict, List, Optional


class AttributeDiffItem:
    def __init__(self, attribute_name: str, old_value: Any, new_value: Any):
        self.attribute_name = attribute_name
        self.old_value = old_value
        self.new_value = new_value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attribute_name": self.attribute_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
        }


class AttributeComparator:
    """Compares relevant structured attributes between baseline and comparison snapshots."""

    ATTRIBUTES_TO_TRACK = [
        "building_type",
        "building_reference",
        "status",
        "height_estimate",
        "height",
        "base_elevation",
        "floor_count",
        "land_use",
        "ownership_status",
        "parcel_number",
        "survey_number",
        "property_reference",
        "area",
        "built_up_area",
    ]

    @classmethod
    def compare_attributes(
        cls,
        baseline_attrs: Dict[str, Any],
        current_attrs: Dict[str, Any],
        tracked_keys: Optional[List[str]] = None,
    ) -> List[AttributeDiffItem]:
        keys = tracked_keys or cls.ATTRIBUTES_TO_TRACK
        diffs: List[AttributeDiffItem] = []

        all_keys = set(keys).intersection(set(baseline_attrs.keys()).union(set(current_attrs.keys())))

        for key in sorted(all_keys):
            old_val = baseline_attrs.get(key)
            new_val = current_attrs.get(key)

            # Compare normalized values (handling floats and strings gracefully)
            if old_val is not None and new_val is not None:
                if isinstance(old_val, float) and isinstance(new_val, float):
                    if abs(old_val - new_val) > 0.01:
                        diffs.append(AttributeDiffItem(key, old_val, new_val))
                elif str(old_val).strip() != str(new_val).strip():
                    diffs.append(AttributeDiffItem(key, old_val, new_val))
            elif old_val != new_val:
                diffs.append(AttributeDiffItem(key, old_val, new_val))

        return diffs
