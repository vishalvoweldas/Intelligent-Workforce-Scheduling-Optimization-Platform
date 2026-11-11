"""Unit tests for IDs, durations, overtime math, and fairness calculations."""
import pytest
from datetime import datetime, date
from backend.services.id_generator import IdGenerator
from backend.analytics.fairness import FairnessAnalytics
from backend.analytics.coverage import CoverageAnalytics

def test_id_generator_formatting():
    assert IdGenerator.employee(1) == "EMP-000001"
    assert IdGenerator.employee(142) == "EMP-000142"
    assert IdGenerator.team(1) == "TEAM-001"
    assert IdGenerator.skill(3) == "SKL-003"
    assert IdGenerator.shift_template("morn") == "TMPL-MORN"
    assert IdGenerator.shift(date(2026, 1, 1), "A") == "SHIFT-2026-01-01-A"
    assert IdGenerator.assignment(5) == "ASGN-000005"
    assert IdGenerator.leave(2026, 12) == "LVE-2026-000012"
    assert IdGenerator.swap(2026, 7) == "SWP-2026-000007"
    assert IdGenerator.coverage(1) == "COV-000001"
    assert IdGenerator.schedule_run(2026, 4) == "RUN-2026-000004"
    assert IdGenerator.anomaly(2) == "ANOM-000002"

def test_overnight_shift_duration_math():
    start_dt = datetime(2026, 1, 1, 22, 0, 0)
    end_dt = datetime(2026, 1, 2, 6, 30, 0)
    elapsed = (end_dt - start_dt).total_seconds() / 3600.0
    break_hours = 0.5
    net_hours = elapsed - break_hours
    assert net_hours == 8.0

def test_overtime_math():
    contracted = 40.0
    cap = 8.0
    worked_regular = 38.0
    worked_ot = 46.0
    worked_excess = 52.0

    assert max(0.0, worked_regular - contracted) == 0.0
    assert max(0.0, worked_ot - contracted) == 6.0
    ot_excess = max(0.0, worked_excess - contracted)
    assert ot_excess == 12.0
    assert ot_excess > cap  # Exceeded cap

def test_fairness_analytics_metrics():
    employees = [
        {"employee_id": "EMP-000001", "first_name": "Alex", "last_name": "M", "team_id": "TEAM-001", "contracted_weekly_hours": 40.0},
        {"employee_id": "EMP-000002", "first_name": "Jordan", "last_name": "K", "team_id": "TEAM-001", "contracted_weekly_hours": 40.0}
    ]
    shifts = [
        {"shift_id": "SHIFT-1", "template_id": "TMPL-MORN", "shift_date": "2026-01-01"},
        {"shift_id": "SHIFT-2", "template_id": "TMPL-MORN", "shift_date": "2026-01-02"}
    ]
    # Equal distribution: each gets 1 shift (8 hours)
    assignments = [
        {"assignment_id": "ASGN-1", "shift_id": "SHIFT-1", "employee_id": "EMP-000001"},
        {"assignment_id": "ASGN-2", "shift_id": "SHIFT-2", "employee_id": "EMP-000002"}
    ]
    result = FairnessAnalytics.calculate_fairness(employees, shifts, assignments)
    assert result["mean_scheduled_hours"] == 8.0
    assert result["stdev_scheduled_hours"] == 0.0  # Perfect parity
    assert result["gini_inequality_coefficient"] == 0.0

def test_coverage_analytics_fill_rates():
    shifts = [
        {"shift_id": "SHIFT-1", "team_id": "TEAM-001", "template_id": "TMPL-MORN"},
        {"shift_id": "SHIFT-2", "team_id": "TEAM-001", "template_id": "TMPL-MORN"}
    ]
    assignments = [
        {"assignment_id": "ASGN-1", "shift_id": "SHIFT-1", "employee_id": "EMP-000001"}
    ]
    cov_reqs = []
    res = CoverageAnalytics.calculate_coverage(shifts, assignments, cov_reqs)
    assert res["total_required_shifts"] == 2
    assert res["filled_shifts"] == 1
    assert res["unfilled_shifts"] == 1
    assert res["overall_coverage_rate"] == 0.5

