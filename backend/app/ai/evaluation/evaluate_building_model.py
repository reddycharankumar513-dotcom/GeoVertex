import json
import sys
from app.ai.models import DevelopmentBaselineBuildingExtractor, UnconfiguredFloorExtractor
from app.ai.evaluation.evaluator import model_evaluator


def main():
    print("=" * 60)
    print("GEOVERTEX: MODEL EVALUATION RUNNER")
    print("=" * 60)

    report = model_evaluator.evaluate_model(
        model_id="building-segmentation-v1",
        model_version="1.0.0",
    )

    print(f"Dataset Name:    {report['dataset_info']['dataset_name']}")
    print(f"Dataset Type:    {report['dataset_info']['dataset_type']}")
    print(f"Sample Count:    {report['dataset_info']['sample_count']}")
    print(f"Model ID:        {report['model_info']['model_id']}")
    print(f"Model Version:   {report['model_info']['model_version']}")
    print("-" * 60)
    print("Evaluation Metrics:")
    for key, value in report["metrics"].items():
        print(f"  {key:25}: {value}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
