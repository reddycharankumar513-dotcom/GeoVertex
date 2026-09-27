from typing import Any, Dict, List, Optional


class ChangeDetectionEvaluator:
    """Evaluates change detection models against labeled ground truth benchmark datasets."""

    @classmethod
    def evaluate(
        cls,
        predictions: List[Dict[str, Any]],
        ground_truth: Optional[List[Dict[str, Any]]] = None,
        dataset_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculates evaluation metrics only when a valid ground truth dataset is provided."""
        if not ground_truth or len(ground_truth) == 0:
            return {
                "status": "EVALUATION_DATASET_NOT_CONFIGURED",
                "message": f"Ground-truth labeled change dataset '{dataset_id or 'UNSET'}' is not configured. Evaluation metrics cannot be claimed without empirical ground truth.",
                "dataset_id": dataset_id,
                "precision": None,
                "recall": None,
                "f1_score": None,
                "mean_iou": None,
            }

        # Calculate standard confusion matrix metrics when labeled data exists
        tp = 0
        fp = 0
        fn = 0
        total_iou = 0.0

        for pred in predictions:
            matched = False
            pred_id = pred.get("entity_id")
            for gt in ground_truth:
                if pred_id and pred_id == gt.get("entity_id"):
                    matched = True
                    iou = pred.get("magnitude", {}).get("iou", 0.0)
                    total_iou += iou
                    if iou >= 0.5:
                        tp += 1
                    else:
                        fp += 1
                    break
            if not matched:
                fp += 1

        fn = max(0, len(ground_truth) - tp)
        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        mean_iou = (total_iou / max(1, tp + fp))

        return {
            "status": "EVALUATION_COMPLETED",
            "dataset_id": dataset_id,
            "sample_count": len(predictions),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "mean_iou": round(mean_iou, 4),
        }
