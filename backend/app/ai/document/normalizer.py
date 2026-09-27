import re
from datetime import datetime
from typing import Optional, Tuple


class DocumentNormalizer:
    """Deterministic normalizer for property document metadata, identifiers, and measurements."""

    # Area conversion constants to Square Meters (m²)
    SQFT_TO_SQM = 0.092903
    SQYD_TO_SQM = 0.836127
    ACRE_TO_SQM = 4046.86
    HECTARE_TO_SQM = 10000.0
    GUNTAS_TO_SQM = 101.17

    @classmethod
    def normalize_survey_number(cls, raw: str) -> str:
        """Normalizes cadastral survey numbers: '123 / 4 B' -> '123/4B'."""
        if not raw:
            return ""
        s = raw.strip().upper()
        # Remove spaces around slashes and hyphens
        s = re.sub(r"\s*/\s*", "/", s)
        s = re.sub(r"\s*-\s*", "-", s)
        # Collapse multiple spaces
        s = re.sub(r"\s+", "", s)
        return s

    @classmethod
    def normalize_parcel_code(cls, raw: str) -> str:
        """Normalizes parcel reference codes e.g. 'PCL - 001 - A' -> 'PCL-001-A'."""
        if not raw:
            return ""
        s = raw.strip().upper()
        s = re.sub(r"\s*-\s*", "-", s)
        s = re.sub(r"\s+", "", s)
        return s

    @classmethod
    def normalize_postal_code(cls, raw: str) -> str:
        """Normalizes postal codes e.g. '500 081' -> '500081'."""
        if not raw:
            return ""
        return re.sub(r"\D", "", raw.strip())

    @classmethod
    def normalize_date(cls, raw: str) -> Tuple[Optional[str], Optional[datetime]]:
        """Parses various date formats into canonical ISO 'YYYY-MM-DD' and Python datetime.
        
        Supports:
        - 2026-05-12
        - 12/05/2026, 12-05-2026
        - 12 May 2026, 12th May 2026
        - May 12, 2026
        """
        if not raw:
            return None, None

        cleaned = raw.strip()
        # Remove ordinals (st, nd, rd, th)
        cleaned = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned)

        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d.%m.%Y",
            "%m/%d/%Y",
            "%d %B %Y",
            "%d %b %Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y/%m/%d",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(cleaned, fmt)
                return dt.strftime("%Y-%m-%d"), dt
            except ValueError:
                continue

        return None, None

    @classmethod
    def normalize_area(cls, raw: str) -> Tuple[Optional[float], Optional[str]]:
        """Parses raw area string and converts to numeric square meters (m²).
        
        Examples:
        - '1,250 sq.ft' -> (116.13, '116.13 sq.m (from 1,250 sq.ft)')
        - '250 sq.m' -> (250.0, '250.00 sq.m')
        - '200 sq.yards' -> (167.23, '167.23 sq.m (from 200 sq.yards)')
        - '1.5 acres' -> (6070.29, '6070.29 sq.m (from 1.5 acres)')
        """
        if not raw:
            return None, None

        cleaned = raw.strip().lower().replace(",", "")

        # Extract number
        num_match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
        if not num_match:
            return None, None

        val = float(num_match.group(1))

        # Check unit
        if re.search(r"\b(sq\.?\s*ft|sq\.?\s*feet|square\s*feet|sft)\b", cleaned):
            sqm = round(val * cls.SQFT_TO_SQM, 2)
            return sqm, f"{sqm:.2f} sq.m ({val} sq.ft)"

        if re.search(r"\b(sq\.?\s*yd|sq\.?\s*yards|square\s*yards|syd)\b", cleaned):
            sqm = round(val * cls.SQYD_TO_SQM, 2)
            return sqm, f"{sqm:.2f} sq.m ({val} sq.yards)"

        if re.search(r"\b(acre|acres)\b", cleaned):
            sqm = round(val * cls.ACRE_TO_SQM, 2)
            return sqm, f"{sqm:.2f} sq.m ({val} acres)"

        if re.search(r"\b(hectare|hectares|ha)\b", cleaned):
            sqm = round(val * cls.HECTARE_TO_SQM, 2)
            return sqm, f"{sqm:.2f} sq.m ({val} hectares)"

        if re.search(r"\b(gunta|guntas)\b", cleaned):
            sqm = round(val * cls.GUNTAS_TO_SQM, 2)
            return sqm, f"{sqm:.2f} sq.m ({val} guntas)"

        # Default assumes square meters
        return val, f"{val:.2f} sq.m"

    @classmethod
    def normalize_address(cls, raw: str) -> str:
        """Normalizes postal/street address for spatial matching."""
        if not raw:
            return ""
        s = raw.strip()
        # Collapse multiple spaces and trim punctuation
        s = re.sub(r"[\t\r\n]+", " ", s)
        s = re.sub(r"\s+", " ", s)
        s = re.sub(r"\s*,\s*", ", ", s)
        s = re.sub(r",+", ",", s)
        return s.strip(", ")


document_normalizer = DocumentNormalizer()
