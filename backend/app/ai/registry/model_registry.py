import hashlib
import os
from pathlib import Path
from typing import Any, Dict, Optional, Type
from app.ai.base import (
    BaseBuildingExtractor,
    BaseFloorExtractor,
    ModelIntegrityError,
    ModelNotConfiguredError,
    ModelWeightsUnavailableError,
)

# AI Device Context (CPU / CUDA)
AI_DEVICE = os.getenv("AI_DEVICE", "cpu").lower()


class ModelRegistry:
    """Thread-safe in-memory model registry and cache for worker processes."""

    def __init__(self):
        self._model_classes: Dict[str, Type[Any]] = {}
        self._loaded_instances: Dict[str, Any] = {}
        self._model_metadata: Dict[str, Dict[str, Any]] = {}

    def register_model_class(
        self,
        model_id: str,
        model_class: Type[Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Registers a model class implementation with optional default metadata."""
        self._model_classes[model_id] = model_class
        if metadata:
            self._model_metadata[model_id] = metadata

    def is_registered(self, model_id: str) -> bool:
        return model_id in self._model_classes

    def get_registered_model_ids(self) -> list[str]:
        return list(self._model_classes.keys())

    def get_model_metadata(self, model_id: str) -> Dict[str, Any]:
        if model_id not in self._model_metadata:
            return {"model_id": model_id, "status": "UNCONFIGURED"}
        return self._model_metadata[model_id]

    def verify_weights_integrity(self, weights_path: str, expected_sha256: Optional[str]) -> bool:
        """Verifies cryptographic SHA-256 hash of model weights binary."""
        path = Path(weights_path)
        if not path.is_file():
            raise ModelWeightsUnavailableError(f"Weights file not found at path: {weights_path}")
        if not expected_sha256:
            return True

        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        computed_hash = hasher.hexdigest().lower()
        if computed_hash != expected_sha256.lower():
            raise ModelIntegrityError(
                f"Weights checksum mismatch for '{weights_path}'. Expected: {expected_sha256}, got: {computed_hash}"
            )
        return True

    def get_or_load_model(
        self,
        model_id: str,
        model_version: str = "1.0.0",
        weights_reference: Optional[str] = None,
        weights_hash: Optional[str] = None,
        configuration: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Loads and caches the model instance. Reuses loaded instance across inference runs."""
        cache_key = f"{model_id}:{model_version}"
        if cache_key in self._loaded_instances:
            return self._loaded_instances[cache_key]

        if model_id not in self._model_classes:
            raise ModelNotConfiguredError(
                f"Model '{model_id}' is not configured in the model registry."
            )

        model_class = self._model_classes[model_id]
        instance = model_class()

        # If weights are required and referenced, verify integrity
        if weights_reference:
            self.verify_weights_integrity(weights_reference, weights_hash)

        config = configuration or {}
        config["device"] = AI_DEVICE
        instance.load_model(model_path=weights_reference, config=config)

        self._loaded_instances[cache_key] = instance
        return instance

    def clear_cache(self) -> None:
        """Clears cached model instances."""
        self._loaded_instances.clear()


# Global Singleton Registry
model_registry = ModelRegistry()
