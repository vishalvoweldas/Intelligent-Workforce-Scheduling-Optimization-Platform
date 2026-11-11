"""Dataset export module supporting CSV, JSON, and SQL Seed generation."""
import os
import json
import csv
import hashlib
from typing import Dict, Any, List

class DatasetExporter:
    """Exports dataset collections to disk in multiple enterprise formats."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export_all(
        self,
        data: Dict[str, List[Dict[str, Any]]],
        profile_name: str,
        seed: int,
        validation_report: Dict[str, Any],
        ground_truth: List[Dict[str, Any]] = None,
        anomaly_records: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Exports dataset to CSV, JSON, SQL seed, and writes manifest.json."""
        exported_files = []
        file_hashes = {}

        # 1. Export CSVs
        for table_name, records in data.items():
            if not records:
                continue
            csv_path = os.path.join(self.output_dir, f"{table_name}.csv")
            self._write_csv(csv_path, records)
            exported_files.append(csv_path)
            file_hashes[f"{table_name}.csv"] = self._compute_sha256(csv_path)

        # 2. Export Anomaly & Ground Truth CSVs if provided
        if anomaly_records:
            anom_csv = os.path.join(self.output_dir, "anomaly_records.csv")
            self._write_csv(anom_csv, anomaly_records)
            exported_files.append(anom_csv)
            file_hashes["anomaly_records.csv"] = self._compute_sha256(anom_csv)

        if ground_truth:
            gt_csv = os.path.join(self.output_dir, "ground_truth.csv")
            self._write_csv(gt_csv, ground_truth)
            exported_files.append(gt_csv)
            file_hashes["ground_truth.csv"] = self._compute_sha256(gt_csv)

            gt_json = os.path.join(self.output_dir, "ground_truth.json")
            with open(gt_json, "w", encoding="utf-8") as f:
                json.dump(ground_truth, f, indent=2)
            exported_files.append(gt_json)
            file_hashes["ground_truth.json"] = self._compute_sha256(gt_json)

        # 3. Export Unified JSON
        unified_json_path = os.path.join(self.output_dir, "dataset.json")
        with open(unified_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        exported_files.append(unified_json_path)
        file_hashes["dataset.json"] = self._compute_sha256(unified_json_path)

        # 4. Export SQL Seed Script
        sql_path = os.path.join(self.output_dir, "seed_data.sql")
        self._write_sql_seed(sql_path, data)
        exported_files.append(sql_path)
        file_hashes["seed_data.sql"] = self._compute_sha256(sql_path)

        # 5. Export Validation Report
        val_path = os.path.join(self.output_dir, "validation_report.json")
        with open(val_path, "w", encoding="utf-8") as f:
            json.dump(validation_report, f, indent=2)
        exported_files.append(val_path)
        file_hashes["validation_report.json"] = self._compute_sha256(val_path)

        # 6. Export Manifest
        manifest = {
            "profile": profile_name,
            "seed": seed,
            "record_counts": {k: len(v) for k, v in data.items()},
            "file_checksums_sha256": file_hashes,
            "validation_status": "PASSED" if validation_report.get("is_valid") else "FAILED",
            "generator_command": f"python scripts/generate_datasets.py --profile {profile_name} --seed {seed}"
        }
        manifest_path = os.path.join(self.output_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        file_hashes["manifest.json"] = self._compute_sha256(manifest_path)

        return manifest

    def _write_csv(self, filepath: str, records: List[Dict[str, Any]]):
        if not records:
            return
        fieldnames = list(records[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

    def _write_sql_seed(self, filepath: str, data: Dict[str, List[Dict[str, Any]]]):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("-- Synthetic Workforce Seed Data Script\n")
            f.write("BEGIN TRANSACTION;\n\n")

            table_order = [
                "teams", "skills", "shift_templates", "employees", "employee_skills",
                "coverage_requirements", "holiday_calendar", "shifts", "shift_assignments",
                "leave_requests", "attendance_events", "swap_requests"
            ]

            for table in table_order:
                records = data.get(table, [])
                if not records:
                    continue
                f.write(f"-- Table: {table} ({len(records)} rows)\n")
                columns = list(records[0].keys())
                col_str = ", ".join(columns)

                for r in records:
                    vals = []
                    for col in columns:
                        v = r.get(col)
                        if v is None:
                            vals.append("NULL")
                        elif isinstance(v, (int, float)):
                            vals.append(str(v))
                        elif isinstance(v, bool):
                            vals.append("1" if v else "0")
                        else:
                            clean_str = str(v).replace("'", "''")
                            vals.append(f"'{clean_str}'")
                    val_str = ", ".join(vals)
                    f.write(f"INSERT OR REPLACE INTO {table} ({col_str}) VALUES ({val_str});\n")
                f.write("\n")

            f.write("COMMIT;\n")

    def _compute_sha256(self, filepath: str) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

