"""Benchmark evaluator comparing detected anomalies against isolated ground truth."""
from typing import Dict, Any, List

class BenchmarkEvaluator:
    """Computes Confusion Matrix, Precision, Recall, and F1-score against ground truth."""

    def evaluate(
        self,
        predicted_anomalies: List[Dict[str, Any]],
        ground_truth_records: List[Dict[str, Any]],
        total_records_evaluated: int = 1000
    ) -> Dict[str, Any]:
        # Index ground truth by (issue_type, record_id)
        gt_map = {(gt["issue_type"], gt["record_id"]): gt for gt in ground_truth_records}
        pred_map = {(p["issue_type"], p["record_id"]): p for p in predicted_anomalies}

        categories = ["DOUBLE_BOOKING", "LEAVE_CONFLICT", "MISSING_SKILL", "OVERTIME_EXCEEDED", "UNAPPROVED_SWAP"]

        category_metrics = {}
        total_tp = 0
        total_fp = 0
        total_fn = 0

        for cat in categories:
            cat_gt = {k: v for k, v in gt_map.items() if k[0] == cat}
            cat_pred = {k: v for k, v in pred_map.items() if k[0] == cat}

            tp = len(set(cat_pred.keys()) & set(cat_gt.keys()))
            fp = len(set(cat_pred.keys()) - set(cat_gt.keys()))
            fn = len(set(cat_gt.keys()) - set(cat_pred.keys()))

            total_tp += tp
            total_fp += fp
            total_fn += fn

            precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
            f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

            category_metrics[cat] = {
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4)
            }

        overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 1.0
        overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 1.0
        overall_f1 = (2 * overall_precision * overall_recall) / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0.0

        total_tn = max(0, total_records_evaluated - (total_tp + total_fp + total_fn))

        return {
            "confusion_matrix": {
                "true_positives": total_tp,
                "false_positives": total_fp,
                "true_negatives": total_tn,
                "false_negatives": total_fn
            },
            "overall_metrics": {
                "precision": round(overall_precision, 4),
                "recall": round(overall_recall, 4),
                "f1_score": round(overall_f1, 4)
            },
            "by_category": category_metrics,
            "ground_truth_total": len(ground_truth_records),
            "predicted_total": len(predicted_anomalies)
        }

