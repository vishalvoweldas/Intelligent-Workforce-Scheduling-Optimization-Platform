"""Integration tests for Starter and Full Dataset Profile Switcher."""
import pytest
from backend.models.database import SessionLocal, set_active_profile, get_active_profile
from backend.models.profile_manager import PROFILE_STARTER, PROFILE_FULL
from backend.api.datasets import list_dataset_profiles, get_current_active_profile, switch_active_dataset_profile
from backend.api.auth import list_demo_identities
from backend.api.schedules import run_schedule_optimizer
from backend.schemas.schemas import SwitchProfileRequest, ScheduleRunRequest
from backend.security.rbac import CurrentUser, ROLE_ADMIN, ROLE_EMPLOYEE, ROLE_MANAGER
from fastapi import HTTPException

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(autouse=True)
def ensure_clean_profile():
    """Ensure tests start and end with STARTER profile active."""
    set_active_profile("STARTER")
    yield
    set_active_profile("STARTER")


def test_list_profiles_endpoint():
    """Verifies that both STARTER and FULL profiles are reported with correct metadata."""
    data = list_dataset_profiles()
    assert "active_profile" in data
    assert "profiles" in data
    assert len(data["profiles"]) == 2

    starter = next(p for p in data["profiles"] if p["id"] == "STARTER")
    assert starter["employees_count"] == 100
    assert starter["teams_count"] == 10
    assert starter["horizon_days"] == 14
    assert starter["is_generated"] is True

    full = next(p for p in data["profiles"] if p["id"] == "FULL")
    assert full["employees_count"] == 2000
    assert full["teams_count"] == 100
    assert full["horizon_days"] == 90
    assert full["is_generated"] is True


def test_active_profile_metadata_and_counts():
    """Verifies that active profile reflects live database row counts."""
    data = get_current_active_profile()
    assert data["profile"] == "STARTER"
    assert data["horizon_days"] == 14
    assert data["counts"]["employees"] == 100
    assert data["counts"]["teams"] >= 10


def test_full_profile_switching_and_verification(db):
    """Tests switching to FULL profile and verifies exact 2,000 employees, 100 teams, and 90-day horizon."""
    admin_user = CurrentUser(
        employee_id="EMP-000013",
        role=ROLE_ADMIN,
        team_id="TEAM-003",
        first_name="Casey",
        last_name="Clark",
        email="casey.clark@workforce.internal",
        permissions={"*"}
    )

    # 1. Switch to FULL
    switch_res = switch_active_dataset_profile(
        request=SwitchProfileRequest(profile="FULL"),
        current_user=admin_user,
        db=db
    )
    assert switch_res["success"] is True
    assert switch_res["active_profile"] == "FULL"
    assert "2,000 Employees" in switch_res["badge_label"]

    # 2. Check active profile endpoint
    active_data = get_current_active_profile()
    assert active_data["profile"] == "FULL"
    assert active_data["horizon_days"] == 90
    assert active_data["start_date"] == "2026-01-01"
    assert active_data["end_date"] == "2026-03-31"
    assert active_data["counts"]["employees"] == 2000
    assert active_data["counts"]["teams"] >= 100
    assert active_data["counts"]["shifts"] == 27000
    assert active_data["counts"]["leave_requests"] == 5000

    # 3. Verify demo-users endpoint reflects FULL volume
    session_full = SessionLocal()
    demo_data = list_demo_identities(db=session_full)
    session_full.close()

    assert demo_data["total"] == 2000
    assert len(demo_data["managers"]) == 100
    assert demo_data["hr_partner"]["employee_id"] == "EMP-000101"
    assert demo_data["operations_lead"]["employee_id"] == "EMP-000102"
    assert demo_data["admin"]["employee_id"] == "EMP-000103"

    # 4. Switch back to STARTER
    session_back = SessionLocal()
    back_res = switch_active_dataset_profile(
        request=SwitchProfileRequest(profile="STARTER"),
        current_user=admin_user,
        db=session_back
    )
    session_back.close()
    assert back_res["active_profile"] == "STARTER"

    # 5. Verify STARTER state restored
    restored_data = get_current_active_profile()
    assert restored_data["profile"] == "STARTER"
    assert restored_data["counts"]["employees"] == 100


def test_rbac_and_scoping_in_full_profile(db):
    """Ensures RBAC permissions and team boundaries remain strictly enforced in FULL profile."""
    # Switch to FULL
    set_active_profile("FULL")
    full_db = SessionLocal()

    # Frontline employee in FULL profile cannot run optimizer
    emp_user = CurrentUser(
        employee_id="EMP-000104",
        role=ROLE_EMPLOYEE,
        team_id="TEAM-004",
        first_name="Drew",
        last_name="Taylor",
        email="drew.taylor@workforce.internal",
        permissions=set()
    )
    with pytest.raises(HTTPException) as exc_info:
        run_schedule_optimizer(
            request=ScheduleRunRequest(team_id="TEAM-001", start_date="2026-01-01", end_date="2026-01-14"),
            current_user=emp_user,
            db=full_db
        )
    assert exc_info.value.status_code == 403

    # Manager of TEAM-001 cannot optimize TEAM-002
    mgr_user = CurrentUser(
        employee_id="EMP-000001",
        role=ROLE_MANAGER,
        team_id="TEAM-001",
        first_name="Cameron",
        last_name="Lee",
        email="cameron.lee@workforce.internal",
        permissions={"schedule.generate"}
    )
    with pytest.raises(HTTPException) as exc_info2:
        run_schedule_optimizer(
            request=ScheduleRunRequest(team_id="TEAM-002", start_date="2026-01-01", end_date="2026-01-14"),
            current_user=mgr_user,
            db=full_db
        )
    assert exc_info2.value.status_code == 403

    # Manager of TEAM-001 CAN optimize TEAM-001
    res_valid = run_schedule_optimizer(
        request=ScheduleRunRequest(team_id="TEAM-001", start_date="2026-01-01", end_date="2026-01-07", timeout_seconds=10),
        current_user=mgr_user,
        db=full_db
    )
    assert res_valid["status"] in ("OPTIMAL", "FEASIBLE")

    full_db.close()
    set_active_profile("STARTER")
