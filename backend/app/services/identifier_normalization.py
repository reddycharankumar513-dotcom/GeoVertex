"""Phase 12 — Deterministic Identifier Normalization Engine.

Extracts stable, normalized components from spatial entity technical references.
Normalization is deterministic — same input always produces same output.
"""
import re
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Normalization helpers
# ─────────────────────────────────────────────────────────────────────────────

def _clean(value: str) -> str:
    """Remove non-alphanumeric characters except hyphens, uppercase."""
    return re.sub(r"[^A-Z0-9\-]", "", value.upper().strip())


def _pad_numeric(value: str, width: int) -> str:
    """Zero-pad purely numeric strings."""
    if value.isdigit():
        return value.zfill(width)
    return value


# ─────────────────────────────────────────────────────────────────────────────
# Component extraction rules
# ─────────────────────────────────────────────────────────────────────────────

def extract_jurisdiction_component(jurisdiction_code: str, rule: str = "strip_prefix_code") -> str:
    """Extract normalized jurisdiction component from jurisdiction.code.

    Examples:
        "JUR-W101"  → "W101"
        "JUR-VSK"   → "VSK"
        "W101"      → "W101"
    """
    code = _clean(jurisdiction_code)
    if rule == "strip_prefix_code":
        # Remove leading "JUR-" or similar prefix
        code = re.sub(r"^(JUR|JURIS|JURISDICTION)-?", "", code)
    return code or jurisdiction_code.upper()[:12]


def extract_parcel_component(parcel_code: str, rule: str = "strip_prefix_code") -> str:
    """Extract normalized parcel component from parcel.parcel_code.

    Examples:
        "GV-W101-P101"   → "P101"
        "P101"           → "P101"
        "123"            → "P00123"  (padded)
    """
    code = _clean(parcel_code)
    if rule == "strip_prefix_code":
        # Remove leading "GV-XXXX-" prefix (jurisdiction+platform prefix)
        parts = code.split("-")
        if len(parts) >= 3:
            # Last segment is the parcel identifier
            code = parts[-1]
        elif len(parts) == 2:
            code = parts[-1]
    # Ensure parcel prefix
    if code.isdigit():
        code = "P" + _pad_numeric(code, 5)
    elif not code.startswith("P"):
        code = "P" + code
    return code[:12]


def extract_building_component(building_reference: str, rule: str = "strip_prefix_ref") -> str:
    """Extract normalized building component from building.building_reference.

    Examples:
        "BLD-W101-001"   → "B001"
        "B01"            → "B001"
        "001"            → "B001"
    """
    ref = _clean(building_reference)
    if rule == "strip_prefix_ref":
        # Remove leading "BLD-XXXX-" or "BLD-" prefix
        ref = re.sub(r"^BLD-[A-Z0-9]+-", "", ref)
        ref = re.sub(r"^BLD-?", "", ref)
    # Ensure B prefix and zero-pad numeric tail
    match = re.match(r"B?(\d+)(.*)", ref)
    if match:
        num_part = _pad_numeric(match.group(1), 3)
        suffix = match.group(2)
        ref = "B" + num_part + suffix
    elif not ref.startswith("B"):
        ref = "B" + ref
    return ref[:10]


def extract_floor_component(floor_code: str, floor_number: Optional[int] = None, rule: str = "strip_floor_suffix") -> str:
    """Extract normalized floor component from floor.floor_code.

    Examples:
        "BLD-W101-001-F1"   → "F01"
        "BLD-W101-001-F-2"  → "FB02"  (basement)
        floor_number=2      → "F02"
        floor_number=-1     → "FB01"
    """
    if floor_number is not None:
        if floor_number < 0:
            return "FB" + _pad_numeric(str(abs(floor_number)), 2)
        return "F" + _pad_numeric(str(floor_number), 2)

    code = _clean(floor_code)
    if rule == "strip_floor_suffix":
        # Extract F-suffix from end of code
        m = re.search(r"F(-?)(\d+)$", code)
        if m:
            neg = m.group(1) == "-" or "B" in code
            num = _pad_numeric(m.group(2), 2)
            return ("FB" if neg else "F") + num
    return code[-4:] if len(code) > 4 else code


def extract_unit_component(unit_code: str, unit_number: Optional[str] = None, rule: str = "strip_unit_suffix") -> str:
    """Extract normalized unit component from unit.unit_code.

    Examples:
        "BLD-W101-001-F1-U101"  → "U101"
        "BLD-W101-001-F1-U204B" → "U204B"
        unit_number="101"       → "U101"
    """
    if unit_number is not None:
        u = _clean(unit_number)
        if not u.startswith("U"):
            u = "U" + u
        return u[:10]

    code = _clean(unit_code)
    if rule == "strip_unit_suffix":
        m = re.search(r"U([A-Z0-9]+)$", code)
        if m:
            return "U" + m.group(1)[:9]
    return code[-6:] if len(code) > 6 else code


# ─────────────────────────────────────────────────────────────────────────────
# Full identifier assembly
# ─────────────────────────────────────────────────────────────────────────────

def assemble_identifier(
    prefix: str,
    separator: str,
    jurisdiction_comp: Optional[str] = None,
    parcel_comp: Optional[str] = None,
    building_comp: Optional[str] = None,
    floor_comp: Optional[str] = None,
    unit_comp: Optional[str] = None,
) -> str:
    """Assemble the final identifier string from normalized components.

    Always includes: prefix + separator + all non-None components.
    """
    parts = [prefix]
    for comp in [jurisdiction_comp, parcel_comp, building_comp, floor_comp, unit_comp]:
        if comp is not None:
            parts.append(comp)
    return separator.join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Validation helpers
# ─────────────────────────────────────────────────────────────────────────────

ALLOWED_CHARS = re.compile(r"^[A-Z0-9\-]+$")


def validate_component(value: str, name: str, max_len: int = 64) -> list[str]:
    """Return list of validation errors for a component."""
    errors = []
    if not value:
        errors.append(f"{name}: empty component")
    elif not ALLOWED_CHARS.match(value):
        errors.append(f"{name}: contains invalid characters (only A-Z, 0-9, - allowed)")
    elif len(value) > max_len:
        errors.append(f"{name}: exceeds max length {max_len}")
    return errors
