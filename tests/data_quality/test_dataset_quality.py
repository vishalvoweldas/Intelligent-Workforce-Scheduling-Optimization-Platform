"""Data quality, relational integrity, and reproducibility tests."""
import pytest
import os
import json
from data_engine.generators.synthetic_dataset import SyntheticDataGenerator
from data_engine.validators.integrity_validator import IntegrityValidator
from data_engine.reproducibility import ReproducibilityVerifier
from data_engine.anomaly_injection.injector import AnomalyInjector
from data_engine.ground_truth.vault import GroundTruthVault

def test_starter_baseline_integrity():
    gen = SyntheticDataGenerator(profile_name="STARTER", seed=20261022)
    data = gen.generate_all()
    validator = IntegrityValidator()
    report = validator.validate_dataset(data)
    assert report["is_valid"] is True
    assert len(report["errors"]) == 0

def test_fixed_seed_reproducibility():
    repro = ReproducibilityVerifier.verify(profile_name="STARTER", seed=20261022)
    assert repro["is_reproducible"] is True
    assert repro["run1_sha256"] == repro["run2_sha256"]
    assert repro["row_counts_match"] is True

def test_anomaly_injection_and_ground_truth_isolation():
    gen = SyntheticDataGenerator(profile_name="STARTER", seed=20261022)
    baseline = gen.generate_all()

    injector = AnomalyInjector(seed=20261022)
    injected_data, anom_records, gt_records = injector.inject_anomalies(baseline)

    # 1. Verify 5 anomaly types injected
    assert len(anom_records) == 5
    types_injected = {a["issue_type"] for a in anom_records}
    assert types_injected == {
        "DOUBLE_BOOKING", "LEAVE_CONFLICT", "MISSING_SKILL", "OVERTIME_EXCEEDED", "UNAPPROVED_SWAP"
    }

    # 2. Verify ground truth contains matching records
    assert len(gt_records) == 5
    gt_types = {g["issue_type"] for g in gt_records}
    assert gt_types == types_injected

    # 3. Verify ground truth isolation vault
    vault = GroundTruthVault(base_dir="datasets/ground_truth")
    vault.save_ground_truth(gt_records)
    loaded_gt = vault.load_ground_truth()
    assert len(loaded_gt) == 5

