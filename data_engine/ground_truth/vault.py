"""Isolated ground truth storage vault. Strictly inaccessible to scheduling solver."""
import os
import json
import csv
from typing import List, Dict, Any

class GroundTruthVault:
    """Manages ground-truth anomaly annotations in an isolated filesystem location."""

    def __init__(self, base_dir: str = "datasets/ground_truth"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save_ground_truth(self, ground_truth_records: List[Dict[str, Any]]) -> Dict[str, str]:
        """Saves ground truth to both CSV and JSON formats."""
        csv_path = os.path.join(self.base_dir, "ground_truth.csv")
        json_path = os.path.join(self.base_dir, "ground_truth.json")

        # 1. Save JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(ground_truth_records, f, indent=2)

        # 2. Save CSV
        if ground_truth_records:
            fieldnames = list(ground_truth_records[0].keys())
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(ground_truth_records)

        return {"csv_path": csv_path, "json_path": json_path}

    def load_ground_truth(self) -> List[Dict[str, Any]]:
        """Loads ground-truth exclusively for evaluation purposes."""
        json_path = os.path.join(self.base_dir, "ground_truth.json")
        if not os.path.exists(json_path):
            return []
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

