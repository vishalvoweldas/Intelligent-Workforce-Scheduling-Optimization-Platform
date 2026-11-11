"""Integration tests for Employee Identity Synchronization, Dynamic Persona Switching,
and Role-Based Dashboard Authorization.
"""
import pytest
from fastapi import HTTPException
from backend.models.database import SessionLocal
from backend.models.entities import Employee
from backend.api.auth import list_demo_identities, get_user_session
from backend.api.schedules import get_my_schedule, run_schedule_optimizer
from backend.api.leave import list_leave_requests
from backend.api.attendance import reconcile_attendance, list_attendance_events
from backend.schemas.schemas import ScheduleRunRequest
from backend.security.rbac import (
    get_current_user, CurrentUser,
    ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_HR_PARTNER, ROLE_OPERATIONS, ROLE_ADMIN,
    ROLE_PERMISSIONS
)

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_demo_users_payload_structure(db):
    """Validates that demo identities endpoint provides valid arrays for all roles."""
    demo_data = list_demo_identities(db=db)
    assert demo_data["total"] == 100
    assert len(demo_data["employees"]) == 100
    assert len(demo_data["managers"]) == 10

    # Ensure array types for functional roles (prevents frontend runtime map exceptions)
    assert isinstance(demo_data["hr_partners"], list)
    assert len(demo_data["hr_partners"]) >= 1
    assert isinstance(demo_data["operations"], list)
    assert len(demo_data["operations"]) >= 1
    assert isinstance(demo_data["admins"], list)
    assert len(demo_data["admins"]) >= 1

    # Ensure backward compatibility single objects
    assert "hr_partner" in demo_data
    assert "admin" in demo_data

def test_identity_switching_employee_scoping(db):
    """Tests switching between target employee identities without cross-contamination.
    
    Verifies EMP-000001, EMP-000011, EMP-000025, EMP-000050, EMP-000100.
    """
    target_ids = ["EMP-000001", "EMP-000011", "EMP-000025", "EMP-000050", "EMP-000100"]

    for emp_id in target_ids:
        # 1. Test RBAC resolution with explicit identity header
        user = get_current_user(x_user_id=emp_id, x_role=ROLE_EMPLOYEE, db=db)
        assert user.employee_id == emp_id
        assert user.role == ROLE_EMPLOYEE

        emp_record = db.query(Employee).filter(Employee.employee_id == emp_id).first()
        assert emp_record is not None
        assert user.team_id == emp_record.team_id
        assert user.first_name == emp_record.first_name
        assert user.last_name == emp_record.last_name

        # 2. Test Session endpoint
        session = get_user_session(current_user=user)
        assert session["employee_id"] == emp_id
        assert session["role"] == ROLE_EMPLOYEE
        assert session["name"] == f"{emp_record.first_name} {emp_record.last_name}"

        # 3. Test My Schedule endpoint scoping
        my_shifts = get_my_schedule(current_user=user, db=db)
        assert isinstance(my_shifts, list)
        for s in my_shifts:
            assert "shift_id" in s
            assert "shift_date" in s

        # 4. Test Leave Requests scoping: only records for this employee
        leaves = list_leave_requests(current_user=user, db=db)
        for l in leaves["items"]:
            assert l["employee_id"] == emp_id

        # 5. Test Attendance Reconciliation scoping: only records for this employee
        recon = reconcile_attendance(current_user=user, db=db)
        for r in recon["reconciliation"]:
            assert r["employee_id"] == emp_id

def test_role_authorization_boundaries(db):
    """Tests that RBAC permissions and endpoint guards function properly across all 5 canonical roles."""
    # 1. EMPLOYEE role forbidden from running scheduler
    emp_user = get_current_user(x_user_id="EMP-000014", x_role=ROLE_EMPLOYEE, db=db)
    sched_req = ScheduleRunRequest(
        team_id="TEAM-001",
        start_date="2026-01-01",
        end_date="2026-01-07",
        timeout_seconds=5
    )
    with pytest.raises(HTTPException) as exc_info:
        run_schedule_optimizer(sched_req, current_user=emp_user, db=db)
    assert exc_info.value.status_code == 403

    # 2. MANAGER role restricted to own team
    mgr_user = get_current_user(x_user_id="EMP-000001", x_role=ROLE_MANAGER, db=db)
    assert mgr_user.team_id == "TEAM-001"
    cross_team_req = ScheduleRunRequest(
        team_id="TEAM-002",
        start_date="2026-01-01",
        end_date="2026-01-07",
        timeout_seconds=5
    )
    with pytest.raises(HTTPException) as exc_info:
        run_schedule_optimizer(cross_team_req, current_user=mgr_user, db=db)
    assert exc_info.value.status_code == 403

    # 3. OPERATIONS role can inspect telemetry
    ops_user = get_current_user(x_user_id="EMP-000012", x_role=ROLE_OPERATIONS, db=db)
    assert ops_user.role == ROLE_OPERATIONS
    assert ops_user.has_permission("schedule.monitor")
    assert ops_user.has_permission("evaluation.execute")

    # 4. HR_PARTNER role can inspect workforce
    hr_user = get_current_user(x_user_id="EMP-000011", x_role=ROLE_HR_PARTNER, db=db)
    assert hr_user.role == ROLE_HR_PARTNER
    assert hr_user.has_permission("employee.read.all")
    assert hr_user.has_permission("analytics.fairness")

    # 5. ADMIN role has global wildcard access
    admin_user = get_current_user(x_user_id="EMP-000013", x_role=ROLE_ADMIN, db=db)
    assert admin_user.role == ROLE_ADMIN
    assert admin_user.has_permission("anything.anywhere")

