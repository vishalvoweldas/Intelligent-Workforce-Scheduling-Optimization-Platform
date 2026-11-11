"""Integration tests for platform REST route handlers and database workflows."""
import pytest
from backend.models.database import SessionLocal
from backend.api.workforce import list_employees, list_teams, list_skills
from backend.api.shifts import list_shifts, list_shift_templates
from backend.api.leave import submit_leave_request, decide_leave_request, list_leave_requests
from backend.api.swaps import create_swap_request, peer_decide_swap, decide_swap_request, list_swap_requests
from backend.api.attendance import reconcile_attendance, record_attendance_event
from backend.api.evaluations import run_evaluation
from backend.api.datasets import generate_synthetic_dataset
from backend.schemas.schemas import (
    LeaveSubmitRequest, LeaveDecisionRequest, SwapSubmitRequest,
    SwapPeerDecisionRequest, SwapDecisionRequest, AttendanceEventCreate, DatasetGenerateRequest
)
from backend.security.rbac import CurrentUser, ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_MANAGER

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_workforce_api_integration(db):
    res_emp = list_employees(limit=10, offset=0, db=db)
    assert res_emp["total"] > 0
    assert len(res_emp["items"]) > 0

    teams = list_teams(db=db)
    assert len(teams) >= 10

    skills = list_skills(db=db)
    assert len(skills) >= 8

def test_shifts_api_integration(db):
    templates = list_shift_templates(db=db)
    assert len(templates) >= 3

    shifts_res = list_shifts(limit=10, offset=0, db=db)
    assert shifts_res["total"] > 0
    assert len(shifts_res["items"]) > 0

def test_leave_workflow_submit_and_decide(db):
    admin_user = CurrentUser(
        employee_id="EMP-000013", role=ROLE_ADMIN, team_id="ALL",
        email="admin@workforce.local", first_name="System", last_name="Admin", permissions={"*"}
    )
    req = LeaveSubmitRequest(
        employee_id="EMP-000014",
        leave_type="ANNUAL",
        start_date="2026-02-01",
        end_date="2026-02-03",
        comments="Planned winter leave"
    )
    submit_res = submit_leave_request(req, current_user=admin_user, db=db)
    assert submit_res["success"] is True
    assert submit_res["status"] == "PENDING"
    leave_id = submit_res["leave_id"]

    # Decide
    decide_req = LeaveDecisionRequest(decision="APPROVED", comments="Approved by Lead")
    decide_res = decide_leave_request(leave_id, decide_req, current_user=admin_user, db=db)
    assert decide_res["success"] is True
    assert decide_res["status"] == "APPROVED"

def test_shift_swap_workflow(db):
    from backend.models.entities import ShiftAssignment, Shift, EmployeeSkill
    asgns = (
        db.query(ShiftAssignment)
        .join(Shift, ShiftAssignment.shift_id == Shift.shift_id)
        .filter(Shift.team_id == "TEAM-001")
        .all()
    )
    assert len(asgns) >= 2
    asgn1 = asgns[0]
    asgn2 = next(a for a in asgns[1:] if a.employee_id != asgn1.employee_id)

    emp1 = asgn1.employee_id
    emp2 = asgn2.employee_id

    # Guarantee skill certification reciprocity for swap test
    for s_id in ["SKL-001", "SKL-002", "SKL-003", "SKL-004"]:
        if not db.query(EmployeeSkill).filter(EmployeeSkill.employee_id == emp1, EmployeeSkill.skill_id == s_id).first():
            db.add(EmployeeSkill(id=f"ESK-{emp1}-{s_id}", employee_id=emp1, skill_id=s_id, is_certified=True))
        if not db.query(EmployeeSkill).filter(EmployeeSkill.employee_id == emp2, EmployeeSkill.skill_id == s_id).first():
            db.add(EmployeeSkill(id=f"ESK-{emp2}-{s_id}", employee_id=emp2, skill_id=s_id, is_certified=True))
    db.commit()

    admin_user = CurrentUser(
        employee_id="EMP-000013", role=ROLE_ADMIN, team_id="ALL",
        email="admin@workforce.local", first_name="System", last_name="Admin", permissions={"*"}
    )

    swap_req = SwapSubmitRequest(
        requesting_employee_id=emp1,
        receiving_employee_id=emp2,
        original_assignment_id=asgn1.assignment_id,
        proposed_assignment_id=asgn2.assignment_id,
        reason="Family event"
    )
    create_res = create_swap_request(swap_req, current_user=admin_user, db=db)
    assert create_res["success"] is True
    swap_id = create_res["swap_id"]
    assert create_res["status"] == "PENDING_PEER_ACCEPTANCE"

    # Peer acceptance stage
    peer_res = peer_decide_swap(swap_id, SwapPeerDecisionRequest(decision="ACCEPTED"), current_user=admin_user, db=db)
    assert peer_res["success"] is True
    assert peer_res["status"] == "PENDING_MANAGER_APPROVAL"

    # Manager approve stage
    decide_req = SwapDecisionRequest(decision="APPROVED")
    decide_res = decide_swap_request(swap_id, decide_req, current_user=admin_user, db=db)
    assert decide_res["success"] is True
    assert decide_res["status"] == "APPLIED"

def test_attendance_and_reconciliation(db):
    att_req = AttendanceEventCreate(
        employee_id="EMP-000001",
        event_type="CLOCK_IN",
        source="BIOMETRIC"
    )
    rec_res = record_attendance_event(att_req, db=db)
    assert rec_res["success"] is True

    recon = reconcile_attendance(db=db)
    assert "reconciliation" in recon
    assert "employee_overtime_summary" in recon

def test_evaluation_benchmark_run(db):
    # Seed with labelled anomalies
    gen_req = DatasetGenerateRequest(profile="STARTER", seed=20261022, inject_anomalies=True)
    generate_synthetic_dataset(gen_req, db=db)

    eval_res = run_evaluation(db=db)
    assert "confusion_matrix" in eval_res
    assert "overall_metrics" in eval_res
    assert eval_res["overall_metrics"]["recall"] >= 0.80
    assert eval_res["overall_metrics"]["precision"] >= 0.20
    assert eval_res["overall_metrics"]["f1_score"] >= 0.30
