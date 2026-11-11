"""Automated platform initialization and synthetic dataset generation script."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.models.database import Base, engine, SessionLocal
from backend.models.entities import (
    Employee, Team, Skill, ShiftTemplate, Shift, ShiftAssignment, LeaveRequest,
    CoverageRequirement, HolidayCalendar, AttendanceEvent, SwapRequest, AnomalyRecord, DatasetRun
)
from data_engine.generators.synthetic_dataset import SyntheticDataGenerator
from data_engine.validators.integrity_validator import IntegrityValidator
from data_engine.anomaly_injection.injector import AnomalyInjector
from data_engine.ground_truth.vault import GroundTruthVault
from data_engine.exporters.dataset_exporter import DatasetExporter
from data_engine.reproducibility import ReproducibilityVerifier
import json

def init_platform():
    print("=" * 70)
    print("INTELLIGENT WORKFORCE SCHEDULING PLATFORM INITIALIZATION")
    print("=" * 70)

    # 1. Initialize Tables
    print("\n[Step 1/5] Initializing Database Schema...")
    Base.metadata.create_all(bind=engine)
    print("✓ Schema initialized successfully.")

    # 2. Generate Starter Dataset
    print("\n[Step 2/5] Generating STARTER Dataset (Seed: 20261022)...")
    gen = SyntheticDataGenerator(profile_name="STARTER", seed=20261022)
    baseline_data = gen.generate_all()
    print(f"✓ Generated {len(baseline_data['employees'])} employees across {len(baseline_data['teams'])} teams.")
    print(f"✓ Generated {len(baseline_data['shifts'])} shifts and {len(baseline_data['shift_assignments'])} baseline assignments.")
    print(f"✓ Generated {len(baseline_data['leave_requests'])} leave requests.")

    # 3. Validate Baseline Integrity
    print("\n[Step 3/5] Validating Baseline Relational Integrity...")
    validator = IntegrityValidator()
    val_report = validator.validate_dataset(baseline_data)
    if val_report["is_valid"]:
        print("✓ All relational checks passed (PK uniqueness, FK integrity, date ordering, enum validity).")
    else:
        print(f"✗ Validation errors: {val_report['errors']}")

    # 4. Inject Labelled Edge Cases & Save Ground Truth
    print("\n[Step 4/5] Injecting 5 Labelled Anomaly Scenarios & Saving Ground Truth...")
    injector = AnomalyInjector(seed=20261022)
    active_data, anomaly_records, ground_truth = injector.inject_anomalies(baseline_data)

    vault = GroundTruthVault(base_dir="datasets/ground_truth")
    vault.save_ground_truth(ground_truth)
    print(f"✓ Saved {len(ground_truth)} isolated ground-truth records to datasets/ground_truth/.")

    # Export datasets
    export_dir = "datasets/starter"
    exporter = DatasetExporter(output_dir=export_dir)
    manifest = exporter.export_all(
        data=active_data,
        profile_name="STARTER",
        seed=20261022,
        validation_report=val_report,
        ground_truth=ground_truth,
        anomaly_records=anomaly_records
    )
    print(f"✓ Exported CSV, JSON, and SQL seed files to {export_dir}/.")

    # 5. Populate Database
    print("\n[Step 5/5] Populating Platform Database...")
    db = SessionLocal()
    from backend.api.datasets import _seed_database
    _seed_database(db, active_data, anomaly_records)

    # Record DatasetRun
    db.add(DatasetRun(
        run_id="DSR-2026-000001",
        profile="STARTER",
        seed=20261022,
        row_counts_json=json.dumps(manifest["record_counts"]),
        checksum=manifest["file_checksums_sha256"].get("dataset.json", "")
    ))
    db.commit()
    db.close()
    print("✓ Platform database populated with starter data.")

    # Reproducibility Verification
    print("\nVerifying Deterministic Reproducibility...")
    repro = ReproducibilityVerifier.verify(profile_name="STARTER", seed=20261022)
    print(f"✓ {repro['message']}")
    print("=" * 70)
    print("PLATFORM INITIALIZATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    init_platform()

