"""Comprehensive Security & RBAC Enforcement Test Suite."""
import pytest
from fastapi import HTTPException, status
from backend.models.database import SessionLocal
from backend.models.entities import Employee, Team, ShiftAssignment, LeaveRequest, SwapRequest
from backend.security.rbac import (
    CurrentUser, ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_HR_PARTNER, ROLE_OPERATIONS, ROLE_ADMIN,
    verify_ownership, verify_team_scope, require_role, require_permission
)
from backend.api.schedules import run_schedule_optimizer, publish_schedule
from backend.api.datasets import generate_synthetic_dataset
from backend.api.evaluations import run_evaluation
from backend.api.workforce import list_employees, get_employee_profile
from backend.api.leave import submit_leave_request, decide_leave_request
from backend.api.swaps import decide_swap_request
from backend.schemas.schemas import (
    ScheduleRunRequest, DatasetGenerateRequest,
    LeaveSubmitRequest, LeaveDecisionRequest, SwapDecisionRequest
)

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_employee_forbidden_from_running_solver(db):
    """Frontline employees must be strictly denied from triggering optimization."""
    emp_user = CurrentUser(
        employee_id="EMP-000014", role=ROLE_EMPLOYEE, team_id="TEAM-001",
        email="emp14@workforce.local", first_name="John", last_name="Doe", permissions=set()
    )
    req = ScheduleRunRequest(start_date="2026-01-01", end_date="2026-01-14", team_id="TEAM-001")
    with pytest.raises(HTTPException) as exc_info:
        run_schedule_optimizer(req, current_user=emp_user, db=db)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

def test_employee_forbidden_from_publishing_schedules(db):
    emp_user = CurrentUser(
        employee_id="EMP-000014", role=ROLE_EMPLOYEE, team_id="TEAM-001",
        email="emp14@workforce.local", first_name="John", last_name="Doe", permissions=set()
    )
    with pytest.raises(HTTPException) as exc_info:
        publish_schedule(start_date="2026-01-01", end_date="2026-01-14", team_id="TEAM-001", current_user=emp_user, db=db)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

def test_manager_cross_team_scope_violation(db):
    """Manager of TEAM-001 cannot trigger solver or manage TEAM-002."""
    mgr_user = CurrentUser(
        employee_id="EMP-000001", role=ROLE_MANAGER, team_id="TEAM-001",
        email="mgr1@workforce.local", first_name="Manager", last_name="One", permissions=set()
    )
    req = ScheduleRunRequest(start_date="2026-01-01", end_date="2026-01-14", team_id="TEAM-002")
    with pytest.raises(HTTPException) as exc_info:
        run_schedule_optimizer(req, current_user=mgr_user, db=db)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

def test_employee_ownership_boundary_enforcement(db):
    """Employee A cannot submit leave or access profile for Employee B."""
    emp_a = CurrentUser(
        employee_id="EMP-000014", role=ROLE_EMPLOYEE, team_id="TEAM-001",
        email="emp14@workforce.local", first_name="John", last_name="Doe", permissions=set()
    )
    with pytest.raises(HTTPException) as exc_info:
        verify_ownership(emp_a, "EMP-000015")
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    # Attempting to submit leave for another employee
    leave_req = LeaveSubmitRequest(
        employee_id="EMP-000015", leave_type="ANNUAL",
        start_date="2026-03-01", end_date="2026-03-05"
    )
    with pytest.raises(HTTPException) as exc_info:
        submit_leave_request(leave_req, current_user=emp_a, db=db)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

def test_anti_corruption_prevent_self_approval(db):
    """Managers cannot approve their own leave or shift swaps."""
    mgr_user = CurrentUser(
        employee_id="EMP-000001", role=ROLE_MANAGER, team_id="TEAM-001",
        email="mgr1@workforce.local", first_name="Manager", last_name="One", permissions={"leave.approve", "swap.approve"}
    )
    # 1. Create a dummy leave for the manager
    admin_user = CurrentUser(
        employee_id="EMP-000013", role=ROLE_ADMIN, team_id="ALL",
        email="admin@workforce.local", first_name="Admin", last_name="User", permissions={"*"}
    )
    leave_req = LeaveSubmitRequest(
        employee_id="EMP-000001", leave_type="ANNUAL",
        start_date="2026-04-01", end_date="2026-04-03"
    )
    created = submit_leave_request(leave_req, current_user=admin_user, db=db)
    leave_id = created["leave_id"]

    # 2. Manager attempts to approve own leave
    dec_req = LeaveDecisionRequest(decision="APPROVED", comments="Self approved")
    with pytest.raises(HTTPException) as exc_info:
        decide_leave_request(leave_id, dec_req, current_user=mgr_user, db=db)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

def test_unauthorized_role_for_dataset_generation(db):
    """Frontline employees and HR cannot trigger raw synthetic dataset generation."""
    emp_user = CurrentUser(
        employee_id="EMP-000014", role=ROLE_EMPLOYEE, team_id="TEAM-001",
        email="emp14@workforce.local", first_name="John", last_name="Doe", permissions=set()
    )
    req = DatasetGenerateRequest(profile="STARTER", seed=20261022)
    with pytest.raises(HTTPException) as exc_info:
        generate_synthetic_dataset(req, current_user=emp_user, db=db)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
