"""Phase 12 — QR Code generation and secure verification token service.

Generates opaque HMAC-SHA256 signed tokens and QR codes for GeoVertex Technical 3D Identifiers.
"""
import base64
import hashlib
import hmac
import io
import json
import time
from typing import Optional, Tuple

from app.core.config import settings
from app.core.logging import logger

# QR library — optional; graceful fallback if not installed
try:
    import qrcode  # type: ignore
    from qrcode.image.svg import SvgImage  # type: ignore
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    logger.warning("qrcode library not installed. QR generation will return placeholder.")


# ─────────────────────────────────────────────────────────────────────────────
# Token generation
# ─────────────────────────────────────────────────────────────────────────────

_SECRET = settings.JWT_SECRET.encode()


def generate_verification_token(identifier_id: str, identifier_value: str) -> str:
    """Generate a deterministic HMAC-SHA256 verification token.

    Token is opaque — does not expose internal database IDs in a guessable way.
    Format: base64url( identifier_id_prefix + "." + hmac_hex[:32] )
    """
    payload = f"{identifier_id}:{identifier_value}"
    digest = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()
    raw = f"{identifier_id[:8]}.{digest[:32]}"
    token = base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")
    return token


def verify_token_format(token: str) -> bool:
    """Basic structural validation of a verification token."""
    try:
        padded = token + "=" * (-len(token) % 4)
        decoded = base64.urlsafe_b64decode(padded).decode()
        parts = decoded.split(".")
        return len(parts) == 2 and len(parts[0]) == 8 and len(parts[1]) == 32
    except Exception:
        return False


def extract_id_prefix_from_token(token: str) -> Optional[str]:
    """Extract the ID prefix stored in the token (first 8 chars of UUID)."""
    try:
        padded = token + "=" * (-len(token) % 4)
        decoded = base64.urlsafe_b64decode(padded).decode()
        return decoded.split(".")[0]
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# QR Code generation
# ─────────────────────────────────────────────────────────────────────────────

_VERIFY_BASE_URL = "http://localhost:5173/verify"


def _get_verify_url(token: str) -> str:
    """Construct the verification URL encoded in the QR code."""
    return f"{_VERIFY_BASE_URL}/{token}"


def generate_qr_png(token: str) -> Tuple[bytes, str]:
    """Generate a QR code PNG for the given verification token.

    Returns (png_bytes, content_type).
    Falls back to a simple placeholder if qrcode library not available.
    """
    url = _get_verify_url(token)

    if not QR_AVAILABLE:
        # Return minimal 1x1 PNG placeholder
        placeholder = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return placeholder, "image/png"

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), "image/png"


def generate_qr_svg(token: str) -> Tuple[str, str]:
    """Generate a QR code SVG for the given verification token.

    Returns (svg_string, content_type).
    """
    url = _get_verify_url(token)

    if not QR_AVAILABLE:
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><rect width="200" height="200" fill="#f5f5f5"/><text x="100" y="100" text-anchor="middle" font-size="10" fill="#666">QR: {token[:20]}...</text></svg>'
        return svg, "image/svg+xml"

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(image_factory=SvgImage)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode(), "image/svg+xml"


def get_verify_url(token: str) -> str:
    return _get_verify_url(token)
