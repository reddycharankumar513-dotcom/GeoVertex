import json
from typing import Any, Dict, List, Optional
from app.ai.evaluation.metrics import compute_evaluation_metrics
from app.ai.registry.model_registry import model_registry

# Standard sample development evaluation dataset (Section 38: DEMO / DEVELOPMENT DATASET)
DEVELOPMENT_BENCHMARK_DATASET = [
    {
        "id": "sample-01",
        "name": "Commercial Plaza Footprint",
        "ground_truth_wkt": "POLYGON((78.3810 17.4410, 78.3820 17.4410, 78.3820 17.4420, 78.3810 17.4420, 78.3810 17.4410))",
        "target_geometry": "POLYGON((78.3810 17.4410, 78.3820 17.4410, 78.3820 17.4420, 78.3810 17.4420, 78.3810 17.4410))",
    },
    {
        "id": "sample-02",
        "name": "Residential Block Footprint",
        "ground_truth_wkt": "POLYGON((78.3830 17.4430, 78.3840 17.4430, 78.3840 17.4440, 78.3830 17.4440, 78.3830 17.4430))",
        "target_geometry": "POLYGON((78.3830 17.4430, 78.3840 17.4430, 78.3840 17.4440, 78.3830 17.4440, 78.3830 17.4430))",
    },
]


class ModelEvaluator:
    """Evaluates an AI model against a labeled benchmark dataset."""

    def evaluate_model(
        self,
        model_id: str = "building-segmentation-v1",
        model_version: str = "1.0.0",
        dataset: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        eval_data = dataset or DEVELOPMENT_BENCHMARK_DATASET
        model = model_registry.get_or_load_model(model_id, model_version)

        predictions: List[str] = []
        ground_truths: List[str] = []

        for item in eval_data:
            gt_wkt = item["ground_truth_wkt"]
            ground_truths.append(gt_wkt)

            preprocessed = model.preprocess({"target_geometry": item.get("target_geometry", gt_wkt)})
            prediction = model.predict(preprocessed)
            result = model.postprocess(prediction)
            predictions.append(result.geometry_wkt)

        metrics = compute_evaluation_metrics(predictions, ground_truths)

        return {
            "dataset_info": {
                "dataset_name": "GeoVertex Development Baseline Benchmark",
                "dataset_type": "DEMO / DEVELOPMENT DATASET",
                "sample_count": len(eval_data),
            },
            "model_info": {
                "model_id": model_id,
                "model_version": model_version,
            },
            "metrics": metrics,
        }


model_evaluator = ModelEvaluator()
