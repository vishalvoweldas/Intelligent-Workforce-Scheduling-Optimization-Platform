"""Constraint programming tests for Google OR-Tools CP-SAT solver (Scenarios TEST-01 through TEST-09)."""
import pytest
from datetime import date, datetime
from backend.scheduling.optimizer import ScheduleOptimizer

def test_cpsat_solver_feasible_output():
    """TEST-01: Baseline Feasibility."""
    employees = [
        {"employee_id": "EMP-001", "team_id": "TEAM-01", "is_active": True, "employment_status": "ACTIVE", "max_working_hours": 48.0},
        {"employee_id": "EMP-002", "team_id": "TEAM-01", "is_active": True, "employment_status": "ACTIVE", "max_working_hours": 48.0}
    ]
    shifts = [
        {
            "shift_id": "S1", "team_id": "TEAM-01", "template_id": "T1",
            "shift_date": "2026-01-01",
            "start_datetime": "2026-01-01T08:00:00", "end_datetime": "2026-01-01T16:30:00"
        },
        {
            "shift_id": "S2", "team_id": "TEAM-01", "template_id": "T1",
            "shift_date": "2026-01-02",
            "start_datetime": "2026-01-02T08:00:00", "end_datetime": "2026-01-02T16:30:00"
        }
    ]
    cov_reqs = [{"team_id": "TEAM-01", "template_id": "T1", "skill_id": "SKL-1", "min_employees": 1}]
    emp_skills = [
        {"employee_id": "EMP-001", "skill_id": "SKL-1", "is_certified": True},
        {"employee_id": "EMP-002", "skill_id": "SKL-1", "is_certified": True}
    ]
    approved_leaves = []

    optimizer = ScheduleOptimizer(
        employees=employees,
        shifts=shifts,
        coverage_requirements=cov_reqs,
        employee_skills=emp_skills,
        approved_leaves=approved_leaves,
        timeout_seconds=5
    )
    result = optimizer.solve()
    assert result["status"] in ("OPTIMAL", "FEASIBLE")
    assert result["assigned_shifts"] == 2
    assert result["unfilled_shifts"] == 0
    assert result["coverage_rate"] == 1.0

def test_solver_double_booking_prevention():
    """TEST-02: Double-Booking Prevention across concurrent shifts."""
    employees = [
        {"employee_id": "EMP-001", "team_id": "TEAM-01", "is_active": True, "employment_status": "ACTIVE", "max_working_hours": 48.0}
    ]
    # S1 and S2 overlap exactly in time
    shifts = [
        {
            "shift_id": "S1", "team_id": "TEAM-01", "template_id": "T1",
            "shift_date": "2026-01-01",
            "start_datetime": "2026-01-01T08:00:00", "end_datetime": "2026-01-01T16:30:00"
        },
        {
            "shift_id": "S2", "team_id": "TEAM-01", "template_id": "T2",
            "shift_date": "2026-01-01",
            "start_datetime": "2026-01-01T08:00:00", "end_datetime": "2026-01-01T16:30:00"
        }
    ]
    cov_reqs = []
    emp_skills = []
    optimizer = ScheduleOptimizer(
        employees=employees, shifts=shifts, coverage_requirements=cov_reqs,
        employee_skills=emp_skills, approved_leaves=[]
    )
    result = optimizer.solve()
    assert result["assigned_shifts"] <= 1
    assert result["unfilled_shifts"] >= 1

def test_solver_rest_period_enforcement():
    """TEST-03: Minimum Rest Period (BR-02: 11 hours minimum rest)."""
    employees = [
        {"employee_id": "EMP-001", "team_id": "TEAM-01", "is_active": True, "employment_status": "ACTIVE", "max_working_hours": 48.0}
    ]
    # S1 ends at 16:30, S2 starts at 20:00 (only 3.5h rest gap!)
    shifts = [
        {
            "shift_id": "S1", "team_id": "TEAM-01", "template_id": "T1",
            "shift_date": "2026-01-01",
            "start_datetime": "2026-01-01T08:00:00", "end_datetime": "2026-01-01T16:30:00"
        },
        {
            "shift_id": "S2", "team_id": "TEAM-01", "template_id": "T1",
            "shift_date": "2026-01-01",
            "start_datetime": "2026-01-01T20:00:00", "end_datetime": "2026-01-02T04:30:00"
        }
    ]
    cov_reqs = [{"team_id": "TEAM-01", "template_id": "T1", "skill_id": "GENERAL", "min_employees": 1}]

    optimizer = ScheduleOptimizer(
        employees=employees, shifts=shifts, coverage_requirements=cov_reqs,
        employee_skills=[], approved_leaves=[]
    )
    result = optimizer.solve()
    assert result["assigned_shifts"] == 1
    assert result["unfilled_shifts"] == 1
    assert len(result["gaps"]) == 1

def test_solver_maximum_weekly_hours_enforcement():
    """TEST-04: Maximum Weekly Hours (BR-01: cap at 48 hours per week)."""
    # 7 shifts of 8 hours = 56 hours > 48h limit
    employees = [
        {"employee_id": "EMP-001", "team_id": "TEAM-01", "is_active": True, "employment_status": "ACTIVE", "max_working_hours": 40.0}
    ]
    shifts = [
        {
            "shift_id": f"S{i}", "team_id": "TEAM-01", "template_id": "T1",
            "shift_date": f"2026-01-{i:02d}",
            "start_datetime": f"2026-01-{i:02d}T08:00:00", "end_datetime": f"2026-01-{i:02d}T16:00:00"
        }
        for i in range(1, 8)
    ]
    optimizer = ScheduleOptimizer(
        employees=employees, shifts=shifts, coverage_requirements=[],
        employee_skills=[], approved_leaves=[]
    )
    result = optimizer.solve()
    # At most 5 shifts (40h) can be assigned to EMP-001
    assert result["assigned_shifts"] <= 5
    assert result["unfilled_shifts"] >= 2

def test_solver_skill_eligibility_enforcement():
    """TEST-05: Certified Skill Coverage (BR-03)."""
    employees = [
        {"employee_id": "EMP-001", "team_id": "TEAM-01", "is_active": True, "employment_status": "ACTIVE", "max_working_hours": 48.0},
        {"employee_id": "EMP-002", "team_id": "TEAM-01", "is_active": True, "employment_status": "ACTIVE", "max_working_hours": 48.0}
    ]
    shifts = [
        {
            "shift_id": "S1", "team_id": "TEAM-01", "template_id": "T1",
            "shift_date": "2026-01-01",
            "start_datetime": "2026-01-01T08:00:00", "end_datetime": "2026-01-01T16:30:00"
        }
    ]
    cov_reqs = [{"team_id": "TEAM-01", "template_id": "T1", "skill_id": "SKL-SPECIAL", "min_employees": 1}]
    emp_skills = [
        {"employee_id": "EMP-001", "skill_id": "SKL-OTHER", "is_certified": True},
        {"employee_id": "EMP-002", "skill_id": "SKL-SPECIAL", "is_certified": True}
    ]

    optimizer = ScheduleOptimizer(
        employees=employees, shifts=shifts, coverage_requirements=cov_reqs,
        employee_skills=emp_skills, approved_leaves=[]
    )
    result = optimizer.solve()
    assert result["status"] in ("OPTIMAL", "FEASIBLE")
    assert result["assignments"][0]["employee_id"] == "EMP-002"

def test_solver_approved_leave_protection():
    """TEST-06: Approved Leave Blackout (BR-04)."""
    employees = [
        {"employee_id": "EMP-001", "team_id": "TEAM-01", "is_active": True, "employment_status": "ACTIVE", "max_working_hours": 48.0},
        {"employee_id": "EMP-002", "team_id": "TEAM-01", "is_active": True, "employment_status": "ACTIVE", "max_working_hours": 48.0}
    ]
    shifts = [
        {
            "shift_id": "S1", "team_id": "TEAM-01", "template_id": "T1",
            "shift_date": "2026-01-01",
            "start_datetime": "2026-01-01T08:00:00", "end_datetime": "2026-01-01T16:30:00"
        }
    ]
    approved_leaves = [{"employee_id": "EMP-001", "start_date": "2026-01-01", "end_date": "2026-01-01", "approval_status": "APPROVED"}]

    optimizer = ScheduleOptimizer(
        employees=employees, shifts=shifts, coverage_requirements=[],
        employee_skills=[], approved_leaves=approved_leaves
    )
    result = optimizer.solve()
    assert result["status"] in ("OPTIMAL", "FEASIBLE")
    assert result["assignments"][0]["employee_id"] == "EMP-002"

def test_solver_inactive_employee_exclusion():
    """TEST-07: Inactive Employee Exclusion."""
    employees = [
        {"employee_id": "EMP-001", "team_id": "TEAM-01", "is_active": False, "employment_status": "TERMINATED", "max_working_hours": 48.0},
        {"employee_id": "EMP-002", "team_id": "TEAM-01", "is_active": True, "employment_status": "ACTIVE", "max_working_hours": 48.0}
    ]
    shifts = [
        {
            "shift_id": "S1", "team_id": "TEAM-01", "template_id": "T1",
            "shift_date": "2026-01-01",
            "start_datetime": "2026-01-01T08:00:00", "end_datetime": "2026-01-01T16:30:00"
        }
    ]
    optimizer = ScheduleOptimizer(
        employees=employees, shifts=shifts, coverage_requirements=[],
        employee_skills=[], approved_leaves=[]
    )
    result = optimizer.solve()
    assert result["assignments"][0]["employee_id"] == "EMP-002"

def test_solver_objective_fairness_distribution():
    """TEST-08: Objective Function Quality (Fair Distribution)."""
    employees = [
        {"employee_id": "EMP-001", "team_id": "TEAM-01", "is_active": True, "employment_status": "ACTIVE", "max_working_hours": 48.0},
        {"employee_id": "EMP-002", "team_id": "TEAM-01", "is_active": True, "employment_status": "ACTIVE", "max_working_hours": 48.0}
    ]
    shifts = [
        {
            "shift_id": f"S{i}", "team_id": "TEAM-01", "template_id": "T1",
            "shift_date": f"2026-01-{i:02d}",
            "start_datetime": f"2026-01-{i:02d}T08:00:00", "end_datetime": f"2026-01-{i:02d}T16:00:00"
        }
        for i in range(1, 5)
    ]
    optimizer = ScheduleOptimizer(
        employees=employees, shifts=shifts, coverage_requirements=[],
        employee_skills=[], approved_leaves=[]
    )
    result = optimizer.solve()
    assert result["assigned_shifts"] == 4
    counts = {}
    for a in result["assignments"]:
        counts[a["employee_id"]] = counts.get(a["employee_id"], 0) + 1
    # Both employees should receive shifts fairly (2 each)
    assert counts.get("EMP-001") == 2
    assert counts.get("EMP-002") == 2

def test_solver_timeout_guarantee():
    """TEST-09: Solver Timeout Guarantee."""
    employees = [
        {"employee_id": f"EMP-{i:03d}", "team_id": "TEAM-01", "is_active": True, "employment_status": "ACTIVE", "max_working_hours": 48.0}
        for i in range(1, 20)
    ]
    shifts = [
        {
            "shift_id": f"S{i}", "team_id": "TEAM-01", "template_id": "T1",
            "shift_date": f"2026-01-{i%14 + 1:02d}",
            "start_datetime": f"2026-01-{i%14 + 1:02d}T08:00:00", "end_datetime": f"2026-01-{i%14 + 1:02d}T16:00:00"
        }
        for i in range(1, 50)
    ]
    import time
    t0 = time.time()
    optimizer = ScheduleOptimizer(
        employees=employees, shifts=shifts, coverage_requirements=[],
        employee_skills=[], approved_leaves=[], timeout_seconds=2
    )
    result = optimizer.solve()
    elapsed = time.time() - t0
    assert elapsed < 5.0  # Finished within reasonable window
    assert "status" in result
