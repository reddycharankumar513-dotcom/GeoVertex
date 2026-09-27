import os
from pathlib import Path
from typing import Any, Dict, Optional
from shapely.geometry import Polygon, mapping
from shapely import wkt
from app.ai.base import (
    BaseBuildingExtractor,
    ModelNotConfiguredError,
    ModelWeightsUnavailableError,
    OutputGeometryInvalidError,
)
from app.ai.preprocessing.geo_processor import GEOD, geo_preprocessor
from app.ai.preprocessing.image_processor import image_preprocessor
from app.ai.postprocessing.polygonizer import polygonizer
from app.ai.schemas.ai_schemas import (
    BuildingPredictionResult,
    ConfidenceComponents,
)


class DevelopmentBaselineBuildingExtractor(BaseBuildingExtractor):
    """Documented development baseline model for candidate building extraction.
    
    Operates on georeferenced survey evidence context and Area of Interest (AOI).
    Strictly marked as DEVELOPMENT_BASELINE.
    """

    MODEL_ID = "building-segmentation-v1"
    VERSION = "1.0.0"

    def __init__(self):
        self.device = "cpu"
        self.weights_path: Optional[str] = None
        self.config: Dict[str, Any] = {
            "confidence_threshold": 0.65,
            "min_building_area": 10.0,
            "simplification_tolerance": 0.00002,
        }
        self.is_loaded = False

    def load_model(self, model_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> None:
        """Loads configuration and checks weights status."""
        if config:
            self.config.update(config)
            if "device" in config:
                self.device = config["device"]

        self.weights_path = model_path
        # Baseline model operates in heuristic/development mode unless weights are provided
        self.is_loaded = True

    def preprocess(self, raw_input: Any) -> Dict[str, Any]:
        """Preprocesses evidence imagery and spatial context."""
        if not raw_input:
            raise ModelNotConfiguredError("No input data provided to building extractor")

        target_geom = raw_input.get("target_geometry")
        if not target_geom:
            raise ModelNotConfiguredError("Building extraction requires target geometry or spatial boundary")

        aoi = geo_preprocessor.compute_aoi(target_geom, buffer_meters=10.0)

        # Preprocess evidence image if provided
        image_meta = None
        image_path_str = raw_input.get("image_path")
        if image_path_str and Path(image_path_str).exists():
            derived_path, image_meta = image_preprocessor.preprocess_image(Path(image_path_str))

        return {
            "aoi": aoi,
            "image_meta": image_meta,
            "raw_input": raw_input,
        }

    def predict(self, preprocessed_data: Any) -> Dict[str, Any]:
        """Performs forward candidate building extraction from preprocessed context."""
        aoi = preprocessed_data["aoi"]
        target_wkt = aoi["target_wkt"]
        target_poly = geo_preprocessor.parse_geometry(target_wkt)

        # For the documented baseline model, candidate polygon is refined from surveyed
        # field evidence boundaries (e.g. GPS observations / photo points) or contextual AOI
        # If survey observations are attached, adjust boundary coordinates
        obs_points = preprocessed_data.get("raw_input", {}).get("survey_observations", [])
        raw_poly = target_poly

        if obs_points and len(obs_points) >= 3:
            try:
                coords = [(pt["longitude"], pt["latitude"]) for pt in obs_points]
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                obs_poly = Polygon(coords)
                if obs_poly.is_valid and obs_poly.area > 0:
                    raw_poly = obs_poly
            except Exception:
                raw_poly = target_poly

        # Height estimate if survey measurement or image metadata is present
        estimated_height = None
        obs_height = preprocessed_data.get("raw_input", {}).get("survey_height")
        if obs_height is not None:
            try:
                estimated_height = round(float(obs_height), 2)
            except (ValueError, TypeError):
                pass

        # Raw confidence score based on evidence completeness
        has_image = preprocessed_data.get("image_meta") is not None
        has_obs = len(obs_points) > 0
        base_confidence = 0.75 if (has_image and has_obs) else (0.70 if has_image else 0.65)

        return {
            "raw_polygon": raw_poly,
            "estimated_height": estimated_height,
            "model_confidence": base_confidence,
            "evidence_linkage": {
                "source_type": "SURVEY_EVIDENCE_BASELINE",
                "has_imagery": has_image,
                "observation_count": len(obs_points),
            },
        }

    def postprocess(self, raw_prediction: Any, **kwargs: Any) -> BuildingPredictionResult:
        """Applies polygon cleanup, topological repair, and simplification."""
        raw_poly = raw_prediction["raw_polygon"]
        processed_poly, transform_meta = polygonizer.postprocess_polygon(
            raw_poly,
            simplification_tolerance=self.config.get("simplification_tolerance", 0.00002),
            min_area=self.config.get("min_building_area", 10.0),
        )

        area_sqm, _ = GEOD.geometry_area_perimeter(processed_poly)
        model_conf = raw_prediction["model_confidence"]
        geom_quality = 0.85 if transform_meta.get("was_repaired") is False else 0.70
        source_quality = 0.80 if raw_prediction["evidence_linkage"].get("has_imagery") else 0.60

        composite_conf = round((0.5 * model_conf) + (0.3 * geom_quality) + (0.2 * source_quality), 3)

        return BuildingPredictionResult(
            model_name=self.MODEL_ID,
            model_version=self.VERSION,
            geometry_geojson=mapping(processed_poly),
            geometry_wkt=processed_poly.wkt,
            raw_geometry_wkt=raw_poly.wkt,
            estimated_height=raw_prediction.get("estimated_height"),
            confidence_score=composite_conf,
            confidence_components=ConfidenceComponents(
                model_confidence=model_conf,
                geometry_quality=geom_quality,
                source_quality=source_quality,
            ),
            evidence_linkage=raw_prediction.get("evidence_linkage", {}),
            metadata={
                "framework": "BASELINE_HEURISTIC",
                "device": self.device,
                "area_sqm": round(abs(area_sqm), 2),
                "transform_metadata": transform_meta,
            },
        )

    def validate_output(self, output: BuildingPredictionResult) -> bool:
        if not output.geometry_wkt:
            return False
        poly = wkt.loads(output.geometry_wkt)
        return poly.is_valid and not poly.is_empty

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "model_id": self.MODEL_ID,
            "version": self.VERSION,
            "framework": "BASELINE_HEURISTIC",
            "model_type": "BUILDING_EXTRACTION",
            "status": "ACTIVE",
            "device": self.device,
            "configuration": self.config,
        }
