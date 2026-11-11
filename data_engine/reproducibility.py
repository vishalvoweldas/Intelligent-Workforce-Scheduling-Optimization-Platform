"""Deterministic reproducibility verification harness."""
import hashlib
import json
from typing import Dict, Any
from data_engine.generators.synthetic_dataset import SyntheticDataGenerator

class ReproducibilityVerifier:
    """Verifies that two consecutive generations with identical seeds yield bit-for-bit identical outputs."""

    @staticmethod
    def verify(profile_name: str = "STARTER", seed: int = 20261022) -> Dict[str, Any]:
        # Run 1
        gen1 = SyntheticDataGenerator(profile_name=profile_name, seed=seed)
        data1 = gen1.generate_all()
        json1 = json.dumps(data1, sort_keys=True)
        hash1 = hashlib.sha256(json1.encode("utf-8")).hexdigest()

        # Run 2
        gen2 = SyntheticDataGenerator(profile_name=profile_name, seed=seed)
        data2 = gen2.generate_all()
        json2 = json.dumps(data2, sort_keys=True)
        hash2 = hashlib.sha256(json2.encode("utf-8")).hexdigest()

        match = (hash1 == hash2)

        # Compare row counts
        row_counts_run1 = {k: len(v) for k, v in data1.items()}
        row_counts_run2 = {k: len(v) for k, v in data2.items()}

        return {
            "profile": profile_name,
            "seed": seed,
            "is_reproducible": match,
            "run1_sha256": hash1,
            "run2_sha256": hash2,
            "row_counts": row_counts_run1,
            "row_counts_match": row_counts_run1 == row_counts_run2,
            "message": "Deterministic reproducibility verified: 100% hash & count equality." if match else "Reproducibility failure: Hashes differ."
        }

