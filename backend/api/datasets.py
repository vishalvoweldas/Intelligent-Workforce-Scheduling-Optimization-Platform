"""Synthetic Data Generation & Dataset Management Endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import json
import os
from backend.models.database import get_db
from backend.models.entities import (
    Employee, Team, Skill, EmployeeSkill, ShiftTemplate, Shift, ShiftAssignment,
    LeaveRequest, HolidayCalendar, AttendanceEvent, CoverageRequirement, SwapRequest,
    DatasetRun, AnomalyRecord, AuditLog, EvaluationRun
)
from backend.schemas.schemas import DatasetGenerateRequest, SwitchProfileRequest
from backend.models.profile_manager import (
    PROFILE_STARTER, PROFILE_FULL, PROFILE_METADATA,
    get_active_profile, set_active_profile, is_profile_generated,
    get_profile_statistics, ensure_profile_database
)
from data_engine.generators.synthetic_dataset import SyntheticDataGenerator
from data_engine.anomaly_injection.injector import AnomalyInjector
from data_engine.validators.integrity_validator import IntegrityValidator
from data_engine.ground_truth.vault import GroundTruthVault
from data_engine.exporters.dataset_exporter import DatasetExporter
from data_engine.reproducibility import ReproducibilityVerifier
from backend.services.id_generator import IdGenerator

from backend.security.rbac import get_current_user, require_role, resolve_current_user, CurrentUser, ROLE_OPERATIONS, ROLE_ADMIN, status

router = APIRouter(prefix="/datasets", tags=["Synthetic Data Engine"])

@router.get("/profiles")
def list_dataset_profiles():
    """Lists available dataset profiles, their configuration, record counts, and active status."""
    active = get_active_profile()
    profiles = []
    for pid in [PROFILE_STARTER, PROFILE_FULL]:
        meta = PROFILE_METADATA[pid]
        generated = is_profile_generated(pid)
        stats = get_profile_statistics(pid) if generated else None
        profiles.append({
            "id": pid,
            "name": meta["name"],
            "badge_label": meta["badge_label"],
            "employees_count": meta["employees_count"],
            "teams_count": meta["teams_count"],
            "horizon_days": meta["horizon_days"],
            "start_date": meta["start_date"],
            "end_date": meta["end_date"],
            "leaves_count": meta["leaves_count"],
            "is_active": pid == active,
            "is_generated": generated,
            "counts": stats["counts"] if stats else None
        })
    return {
        "active_profile": active,
        "profiles": profiles
    }

@router.get("/active-profile")
def get_current_active_profile():
    """Returns metadata and statistics for the currently active dataset profile."""
    active = get_active_profile()
    return get_profile_statistics(active)

@router.post("/switch-profile")
def switch_active_dataset_profile(
    request: SwitchProfileRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Activates the requested dataset profile (STARTER or FULL), guaranteeing database integrity."""
    prof = request.profile.upper().strip()
    if prof not in PROFILE_METADATA:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid profile '{prof}'. Valid options: {list(PROFILE_METADATA.keys())}"
        )

    new_active = set_active_profile(prof)
    stats = get_profile_statistics(new_active)

    return {
        "success": True,
        "active_profile": new_active,
        "badge_label": stats["badge_label"],
        "message": f"Successfully switched active dataset profile to {stats['name']}",
        "stats": stats
    }

@router.post("/generate")
def generate_synthetic_dataset(
    request: DatasetGenerateRequest,
    current_user: CurrentUser = Depends(require_role(ROLE_OPERATIONS, ROLE_ADMIN)),
    db: Session = Depends(get_db)
):
    """Triggers end-to-end deterministic dataset generation with anomaly injection and exports."""
    current_user = resolve_current_user(current_user, db)
    if current_user.role not in (ROLE_OPERATIONS, ROLE_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only Operations and Administrators can generate synthetic datasets."
        )
    # 1. Generate Baseline Dataset
    generator = SyntheticDataGenerator(profile_name=request.profile, seed=request.seed)
    baseline_data = generator.generate_all()

    # 2. Validate Baseline Relational Integrity
    validator = IntegrityValidator()
    val_report = validator.validate_dataset(baseline_data)

    # 3. Inject Labelled Edge Cases (Anomalies)
    anomaly_records = []
    ground_truth = []
    if request.inject_anomalies:
        injector = AnomalyInjector(seed=request.seed)
        active_data, anomaly_records, ground_truth = injector.inject_anomalies(baseline_data)
    else:
        active_data = baseline_data

    # 4. Save Isolated Ground Truth Vault
    vault = GroundTruthVault(base_dir="datasets/ground_truth")
    vault.save_ground_truth(ground_truth)

    # 5. Export Datasets (CSV, JSON, SQL seed, manifest)
    export_dir = f"datasets/{request.profile.lower()}"
    exporter = DatasetExporter(output_dir=export_dir)
    manifest = exporter.export_all(
        data=active_data,
        profile_name=request.profile,
        seed=request.seed,
        validation_report=val_report,
        ground_truth=ground_truth,
        anomaly_records=anomaly_records
    )

    # 6. Seed Operational Database with Generated Data
    _seed_database(db, active_data, anomaly_records)

    # 7. Record Dataset Run in DB
    run_id = f"DSR-2026-{db.query(DatasetRun).count() + 1:06d}"
    db.add(DatasetRun(
        run_id=run_id,
        profile=request.profile,
        seed=request.seed,
        row_counts_json=json.dumps(manifest["record_counts"]),
        checksum=manifest["file_checksums_sha256"].get("dataset.json", "")
    ))
    db.commit()

    return {
        "success": True,
        "message": f"Successfully generated and seeded {request.profile} dataset",
        "dataset_run_id": run_id,
        "profile": request.profile,
        "seed": request.seed,
        "record_counts": manifest["record_counts"],
        "validation_status": manifest["validation_status"],
        "anomalies_injected": len(anomaly_records),
        "exported_files_count": len(manifest["file_checksums_sha256"])
    }

@router.get("/reproducibility")
def verify_reproducibility(profile: str = "STARTER", seed: int = 20261022):
    """Executes dual deterministic runs to verify 100% hash and record equality."""
    return ReproducibilityVerifier.verify(profile_name=profile, seed=seed)

def _seed_database(db: Session, data: dict, anomaly_records: list):
    """Populates relational tables with synthetic records."""
    from backend.models.entities import LeaveApprovalEvent, SwapApprovalEvent, ShiftAssignmentHistory, ScheduleGap, ScheduleRun
    # Clear existing operational tables in proper foreign-key cascade order
    db.query(EvaluationRun).delete()
    db.query(DatasetRun).delete()
    db.query(AuditLog).delete()
    db.query(LeaveApprovalEvent).delete()
    db.query(SwapApprovalEvent).delete()
    db.query(ShiftAssignmentHistory).delete()
    db.query(ScheduleGap).delete()
    db.query(ScheduleRun).delete()
    db.query(AnomalyRecord).delete()
    db.query(AttendanceEvent).delete()
    db.query(SwapRequest).delete()
    db.query(ShiftAssignment).delete()
    db.query(LeaveRequest).delete()
    db.query(Shift).delete()
    db.query(CoverageRequirement).delete()
    db.query(EmployeeSkill).delete()
    db.query(Employee).delete()
    db.query(Team).delete()
    db.query(Skill).delete()
    db.query(ShiftTemplate).delete()
    db.query(HolidayCalendar).delete()
    db.commit()

    # 1. Teams
    db.add(Team(
        team_id="ALL",
        team_name="Enterprise All Teams",
        department="ENTERPRISE",
        location="HQ-GLOBAL",
        manager_id=None,
        is_active=True
    ))
    for t in data.get("teams", []):
        db.add(Team(
            team_id=t["team_id"],
            team_name=t["team_name"],
            department=t["department"],
            location=t["location"],
            manager_id=t.get("manager_id"),
            is_active=t["is_active"]
        ))
    db.commit()

    # 2. Skills
    for s in data.get("skills", []):
        db.add(Skill(
            skill_id=s["skill_id"],
            skill_name=s["skill_name"],
            category=s["category"],
            description=s["description"],
            is_active=s["is_active"]
        ))
    db.commit()

    # 3. Shift Templates
    for tmpl in data.get("shift_templates", []):
        db.add(ShiftTemplate(
            template_id=tmpl["template_id"],
            template_name=tmpl["template_name"],
            start_time=tmpl["start_time"],
            end_time=tmpl["end_time"],
            break_duration_hours=tmpl["break_duration_hours"],
            category=tmpl["category"],
            duration_hours=tmpl["duration_hours"],
            is_overnight=tmpl["is_overnight"],
            applicable_days=tmpl["applicable_days"],
            is_active=tmpl["is_active"]
        ))
    db.commit()

    # 4. Employees
    for e in data.get("employees", []):
        from datetime import date
        db.add(Employee(
            employee_id=e["employee_id"],
            team_id=e["team_id"],
            first_name=e["first_name"],
            last_name=e["last_name"],
            email=e["email"],
            password_hash=e["password_hash"],
            role=e["role"],
            employment_type=e["employment_type"],
            employment_status=e["employment_status"],
            hire_date=date.fromisoformat(e["hire_date"]),
            work_zone=e["work_zone"],
            contracted_weekly_hours=e["contracted_weekly_hours"],
            max_working_hours=e["max_working_hours"],
            overtime_cap_hours=e["overtime_cap_hours"],
            is_active=e["is_active"]
        ))
    db.commit()

    # 5. Employee Skills
    for es in data.get("employee_skills", []):
        from datetime import date
        exp = date.fromisoformat(es["certification_expiry_date"]) if es.get("certification_expiry_date") else None
        db.add(EmployeeSkill(
            id=es["id"],
            employee_id=es["employee_id"],
            skill_id=es["skill_id"],
            proficiency_level=es["proficiency_level"],
            is_certified=es["is_certified"],
            certification_expiry_date=exp,
            effective_start_date=date.fromisoformat(es["effective_start_date"])
        ))
    db.commit()

    # 6. Coverage Requirements
    for cov in data.get("coverage_requirements", []):
        from datetime import date
        db.add(CoverageRequirement(
            requirement_id=cov["requirement_id"],
            team_id=cov["team_id"],
            template_id=cov["template_id"],
            skill_id=cov["skill_id"],
            min_employees=cov["min_employees"],
            effective_start_date=date.fromisoformat(cov["effective_start_date"])
        ))
    db.commit()

    # 7. Holiday Calendar
    for hol in data.get("holiday_calendar", []):
        from datetime import date
        db.add(HolidayCalendar(
            holiday_id=hol["holiday_id"],
            holiday_name=hol["holiday_name"],
            holiday_date=date.fromisoformat(hol["holiday_date"]),
            applicable_location=hol["applicable_location"],
            holiday_category=hol["holiday_category"]
        ))
    db.commit()

    # 8. Shifts
    for s in data.get("shifts", []):
        from datetime import date, datetime
        db.add(Shift(
            shift_id=s["shift_id"],
            template_id=s["template_id"],
            team_id=s["team_id"],
            shift_date=date.fromisoformat(s["shift_date"]),
            start_datetime=datetime.fromisoformat(s["start_datetime"]),
            end_datetime=datetime.fromisoformat(s["end_datetime"]),
            timezone=s["timezone"],
            status=s["status"]
        ))
    db.commit()

    # 9. Shift Assignments
    for a in data.get("shift_assignments", []):
        db.add(ShiftAssignment(
            assignment_id=a["assignment_id"],
            shift_id=a["shift_id"],
            employee_id=a["employee_id"],
            assignment_status=a["assignment_status"],
            assignment_source=a["assignment_source"],
            schedule_run_id=a.get("schedule_run_id")
        ))
    db.commit()

    # 10. Leave Requests
    for l in data.get("leave_requests", []):
        from datetime import date, datetime
        appr_ts = datetime.fromisoformat(l["approval_timestamp"]) if l.get("approval_timestamp") else None
        db.add(LeaveRequest(
            leave_id=l["leave_id"],
            employee_id=l["employee_id"],
            leave_type=l["leave_type"],
            start_date=date.fromisoformat(l["start_date"]),
            end_date=date.fromisoformat(l["end_date"]),
            request_date=datetime.fromisoformat(l["request_date"]),
            approval_status=l["approval_status"],
            approver_id=l.get("approver_id"),
            approval_timestamp=appr_ts,
            rejection_reason=l.get("rejection_reason")
        ))
    db.commit()

    # 11. Attendance Events
    for att in data.get("attendance_events", []):
        from datetime import datetime
        db.add(AttendanceEvent(
            attendance_id=att["attendance_id"],
            employee_id=att["employee_id"],
            assignment_id=att.get("assignment_id"),
            event_type=att["event_type"],
            event_timestamp=datetime.fromisoformat(att["event_timestamp"]),
            source=att["source"],
            status=att["status"]
        ))
    db.commit()

    # 12. Swap Requests
    for sw in data.get("swap_requests", []):
        from datetime import datetime
        appr_ts = datetime.fromisoformat(sw["approval_timestamp"]) if sw.get("approval_timestamp") else None
        db.add(SwapRequest(
            swap_id=sw["swap_id"],
            requesting_employee_id=sw["requesting_employee_id"],
            receiving_employee_id=sw["receiving_employee_id"],
            original_assignment_id=sw["original_assignment_id"],
            proposed_assignment_id=sw["proposed_assignment_id"],
            request_timestamp=datetime.fromisoformat(sw["request_timestamp"]),
            status=sw["status"],
            manager_approver_id=sw.get("manager_approver_id"),
            approval_timestamp=appr_ts,
            rejection_reason=sw.get("rejection_reason")
        ))
    db.commit()

    # 13. Anomaly Records Registry
    for anom in anomaly_records:
        db.add(AnomalyRecord(
            anomaly_id=anom["anomaly_id"],
            issue_type=anom["issue_type"],
            entity_type=anom["entity_type"],
            record_id=anom["record_id"],
            expected_detection=anom["expected_detection"],
            expected_business_decision=anom["expected_business_decision"],
            severity=anom["severity"],
            injection_method=anom["injection_method"]
        ))
    db.commit()

