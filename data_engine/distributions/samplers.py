"""Realistic statistical probability distributions for synthetic workforce generation."""
import random
import numpy as np
from typing import List, Tuple, Dict, Any

class DistributionSampler:
    """Deterministic statistical sampler initialized with a specific seed."""

    def __init__(self, seed: int = 20261022):
        self.seed = seed
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)

    def sample_employment_type(self) -> Tuple[str, float, float, float]:
        """Returns (employment_type, contracted_weekly_hours, max_hours, ot_cap).
        Realistic distribution: 75% Full-time, 20% Part-time, 5% Contractor.
        """
        roll = self.rng.random()
        if roll < 0.75:
            # Full Time: 40h standard, 48h max, 8h OT cap
            return "FULL_TIME", 40.0, 48.0, 8.0
        elif roll < 0.95:
            # Part Time: 20h standard, 25h max, 5h OT cap
            return "PART_TIME", 20.0, 25.0, 5.0
        else:
            # Contractor: 35h standard, 40h max, 5h OT cap
            return "CONTRACTOR", 35.0, 40.0, 5.0

    def sample_skill_assignments(self, available_skill_ids: List[str]) -> List[Dict[str, Any]]:
        """Assign 1 to 3 skills per employee with realistic proficiency distributions."""
        num_skills = int(self.np_rng.choice([1, 2, 3], p=[0.50, 0.35, 0.15]))
        selected_skills = self.rng.sample(available_skill_ids, min(num_skills, len(available_skill_ids)))

        results = []
        for sk_id in selected_skills:
            # Proficiency: 30% Beginner, 50% Intermediate, 20% Expert
            prof = self.rng.choices(
                ["BEGINNER", "INTERMEDIATE", "EXPERT"],
                weights=[0.30, 0.50, 0.20]
            )[0]
            # 92% certified, 8% uncertified / expired
            is_cert = self.rng.random() < 0.92
            results.append({
                "skill_id": sk_id,
                "proficiency_level": prof,
                "is_certified": is_cert
            })
        return results

    def sample_leave_type(self) -> str:
        """Realistic leave distribution: Annual (60%), Sick (25%), Unpaid (10%), Parental (5%)."""
        return self.rng.choices(
            ["ANNUAL", "SICK", "UNPAID", "PARENTAL"],
            weights=[0.60, 0.25, 0.10, 0.05]
        )[0]

    def sample_leave_approval(self) -> Tuple[str, str]:
        """Returns (approval_status, rejection_reason). 88% approved, 12% rejected."""
        if self.rng.random() < 0.88:
            return "APPROVED", ""
        else:
            reasons = [
                "Staffing shortage for requested dates",
                "Exceeds concurrent team leave quota",
                "Blackout period for operational transition",
                "Insufficient accumulated leave balance"
            ]
            return "REJECTED", self.rng.choice(reasons)

    def sample_attendance_noise(self, scheduled_start: float, scheduled_duration: float) -> Tuple[float, float, str]:
        """Simulate realistic biometric clock-in/out variations.
        Returns: (clock_in_offset_minutes, actual_worked_duration_hours, attendance_status)
        """
        roll = self.rng.random()
        if roll < 0.85:
            # On-time (within -5 to +5 minutes)
            offset_min = self.rng.uniform(-5.0, 5.0)
            worked_duration = scheduled_duration + (self.rng.uniform(-0.1, 0.2))
            return offset_min, max(1.0, round(worked_duration, 2)), "ON_TIME"
        elif roll < 0.94:
            # Late arrival (10 to 45 minutes late)
            offset_min = self.rng.uniform(10.0, 45.0)
            worked_duration = scheduled_duration - (offset_min / 60.0) + self.rng.uniform(0.0, 0.5)
            return offset_min, max(1.0, round(worked_duration, 2)), "LATE"
        elif roll < 0.98:
            # Early departure
            offset_min = self.rng.uniform(-5.0, 5.0)
            early_leave_hours = self.rng.uniform(1.0, 3.0)
            worked_duration = max(1.0, scheduled_duration - early_leave_hours)
            return offset_min, round(worked_duration, 2), "EARLY_DEPARTURE"
        else:
            # Unplanned absence / Missed
            return 0.0, 0.0, "MISSED"

