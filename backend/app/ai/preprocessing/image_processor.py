import hashlib
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from PIL import Image, ExifTags
from app.ai.base import InputInvalidError

DERIVED_ARTIFACTS_DIR = Path("uploads") / "derived"


class ImagePreprocessor:
    """Processes survey photographs and aerial imagery into standardized AI inputs."""

    def __init__(self, derived_dir: Path = DERIVED_ARTIFACTS_DIR):
        self.derived_dir = derived_dir
        self.derived_dir.mkdir(parents=True, exist_ok=True)

    def extract_metadata(self, image_path: Path) -> Dict[str, Any]:
        """Extracts EXIF GPS, timestamp, camera model, orientation, and dimensions."""
        if not image_path.exists():
            raise InputInvalidError(f"Evidence image not found at: {image_path}")

        metadata: Dict[str, Any] = {
            "file_size_bytes": image_path.stat().st_size,
            "filename": image_path.name,
            "dimensions": None,
            "format": None,
            "exif_available": False,
            "timestamp": None,
            "camera_make": None,
            "camera_model": None,
            "gps": {
                "available": False,
                "latitude": None,
                "longitude": None,
                "altitude": None,
            },
            "orientation": 1,
        }

        try:
            with Image.open(image_path) as img:
                metadata["dimensions"] = {"width": img.width, "height": img.height}
                metadata["format"] = img.format

                exif = img.getexif()
                if not exif:
                    return metadata

                metadata["exif_available"] = True

                # Human-readable EXIF tags
                exif_data = {}
                for tag_id, val in exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    exif_data[tag_name] = val

                if "DateTimeOriginal" in exif_data:
                    metadata["timestamp"] = str(exif_data["DateTimeOriginal"])
                elif "DateTime" in exif_data:
                    metadata["timestamp"] = str(exif_data["DateTime"])

                if "Make" in exif_data:
                    metadata["camera_make"] = str(exif_data["Make"]).strip()
                if "Model" in exif_data:
                    metadata["camera_model"] = str(exif_data["Model"]).strip()
                if "Orientation" in exif_data:
                    metadata["orientation"] = int(exif_data["Orientation"])

                # GPS IFD
                gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
                if gps_ifd:
                    lat, lon, alt = self._parse_gps_ifd(gps_ifd)
                    if lat is not None and lon is not None:
                        metadata["gps"] = {
                            "available": True,
                            "latitude": lat,
                            "longitude": lon,
                            "altitude": alt,
                        }
        except Exception as e:
            if isinstance(e, InputInvalidError):
                raise
            raise InputInvalidError(f"Failed to parse evidence image metadata: {str(e)}")

        return metadata

    def _parse_gps_ifd(self, gps_ifd: Dict[int, Any]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        try:
            gps_tags = {}
            for tag_id, val in gps_ifd.items():
                tag_name = ExifTags.GPSTAGS.get(tag_id, str(tag_id))
                gps_tags[tag_name] = val

            def _to_degrees(dms, ref):
                d, m, s = float(dms[0]), float(dms[1]), float(dms[2])
                deg = d + (m / 60.0) + (s / 3600.0)
                if ref in ["S", "W"]:
                    deg = -deg
                return deg

            lat = None
            lon = None
            alt = None

            if "GPSLatitude" in gps_tags and "GPSLatitudeRef" in gps_tags:
                lat = _to_degrees(gps_tags["GPSLatitude"], gps_tags["GPSLatitudeRef"])
            if "GPSLongitude" in gps_tags and "GPSLongitudeRef" in gps_tags:
                lon = _to_degrees(gps_tags["GPSLongitude"], gps_tags["GPSLongitudeRef"])
            if "GPSAltitude" in gps_tags:
                alt = float(gps_tags["GPSAltitude"])

            return lat, lon, alt
        except Exception:
            return None, None, None

    def preprocess_image(
        self,
        image_path: Path,
        target_size: Tuple[int, int] = (512, 512),
        normalize: bool = True,
    ) -> Tuple[Path, Dict[str, Any]]:
        """Validates, applies orientation correction, resizes, and writes derived artifact.
        
        Preserves original evidence image intact.
        Returns:
            (derived_image_path, processing_metadata)
        """
        metadata = self.extract_metadata(image_path)

        try:
            with Image.open(image_path) as img:
                # Convert to standard RGB
                rgb_img = img.convert("RGB")

                # EXIF orientation fix
                orientation = metadata.get("orientation", 1)
                if orientation == 3:
                    rgb_img = rgb_img.rotate(180, expand=True)
                elif orientation == 6:
                    rgb_img = rgb_img.rotate(270, expand=True)
                elif orientation == 8:
                    rgb_img = rgb_img.rotate(90, expand=True)

                # Resize to model input specification
                resized_img = rgb_img.resize(target_size, Image.Resampling.BILINEAR)

                # Hash content for duplicate detection & traceability
                file_hash = hashlib.sha256(resized_img.tobytes()).hexdigest()

                derived_filename = f"derived_{file_hash[:16]}_{target_size[0]}x{target_size[1]}.jpg"
                derived_path = self.derived_dir / derived_filename

                if not derived_path.exists():
                    resized_img.save(derived_path, format="JPEG", quality=90)

                processing_meta = {
                    "source_image": str(image_path.name),
                    "derived_image_path": str(derived_path).replace("\\", "/"),
                    "target_size": target_size,
                    "normalized": normalize,
                    "derived_sha256": file_hash,
                    "original_metadata": metadata,
                }
                return derived_path, processing_meta
        except Exception as e:
            raise InputInvalidError(f"Failed to preprocess image '{image_path.name}': {str(e)}")


image_preprocessor = ImagePreprocessor()
