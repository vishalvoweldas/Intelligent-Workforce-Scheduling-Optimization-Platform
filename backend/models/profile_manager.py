"""Dataset Profile Management and Multi-Database Session Coordination."""
import os
import shutil
import json
import csv
from datetime import datetime, date
from typing import Dict, Any, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

PROFILE_STARTER = "STARTER"
PROFILE_FULL = "FULL"

PROFILE_METADATA = {
    PROFILE_STARTER: {
        "id": PROFILE_STARTER,
        "name": "Starter Profile (100 Employees)",
        "employees_count": 100,
        "teams_count": 10,
        "horizon_days": 14,
        "start_date": "2026-01-01",
        "end_date": "2026-01-14",
        "leaves_count": 250,
        "badge_label": "Simulation: STARTER (100 Employees | 10 Teams | 14 Days)",
        "db_filename": "workforce_starter.db"
    },
    PROFILE_FULL: {
        "id": PROFILE_FULL,
        "name": "Full Profile Volume (2,000 Employees)",
        "employees_count": 2000,
        "teams_count": 100,
        "horizon_days": 90,
        "start_date": "2026-01-01",
        "end_date": "2026-03-31",
        "leaves_count": 5000,
        "badge_label": "Simulation: FULL PROFILE (2,000 Employees | 100 Teams | 90 Days)",
        "db_filename": "workforce_full.db"
    }
}

_active_profile: str = os.getenv("WORKFORCE_PROFILE", PROFILE_STARTER)
_engines: Dict[str, Any] = {}
_session_makers: Dict[str, Any] = {}

Base = declarative_base()


def get_active_profile() -> str:
    """Returns the identifier of the currently active profile."""
    return _active_profile


def set_active_profile(profile_name: str) -> str:
    """Switches the active dataset profile and guarantees its database exists."""
    global _active_profile
    profile = profile_name.upper().strip()
    if profile not in PROFILE_METADATA:
        raise ValueError(f"Unknown profile '{profile}'. Allowed profiles: {list(PROFILE_METADATA.keys())}")
    
    # Ensure database is generated/seeded before activating
    ensure_profile_database(profile)
    _active_profile = profile
    return _active_profile


def get_db_path_for_profile(profile_name: str) -> str:
    """Returns the SQLite file path for a profile."""
    prof = profile_name.upper().strip()
    return PROFILE_METADATA.get(prof, {}).get("db_filename", f"workforce_{prof.lower()}.db")


def create_profile_engine(profile_name: str):
    """Creates a configured SQLAlchemy engine for a dataset profile."""
    db_file = get_db_path_for_profile(profile_name)
    url = f"sqlite:///./{db_file}"
    eng = create_engine(
        url,
        connect_args={"check_same_thread": False},
        echo=False,
        future=True
    )

    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return eng


def get_engine_for_profile(profile_name: str):
    """Gets or initializes the engine for a given profile."""
    prof = profile_name.upper().strip()
    if prof not in _engines:
        _engines[prof] = create_profile_engine(prof)
        _session_makers[prof] = sessionmaker(autocommit=False, autoflush=False, bind=_engines[prof])
    return _engines[prof]


def get_session_factory(profile_name: Optional[str] = None):
    """Gets or initializes the sessionmaker for a given profile (defaulting to active)."""
    prof = (profile_name or _active_profile).upper().strip()
    if prof not in _session_makers:
        get_engine_for_profile(prof)
    return _session_makers[prof]


def is_profile_generated(profile_name: str) -> bool:
    """Checks whether the profile database exists and contains employees."""
    prof = profile_name.upper().strip()
    db_file = get_db_path_for_profile(prof)
    if not os.path.exists(db_file):
        return False
    try:
        eng = get_engine_for_profile(prof)
        with eng.connect() as conn:
            res = conn.execute(text("SELECT count(*) FROM employees;")).scalar()
            expected = PROFILE_METADATA[prof]["employees_count"]
            return res is not None and res >= expected
    except Exception:
        return False


def seed_database_from_dataset(db_file: str, dataset_dir: str, profile_name: str):
    """Seeds a SQLite database from exported JSON and CSV files using high-speed bulk inserts."""
    from backend.models.entities import (
        Employee, Team, Skill, EmployeeSkill, ShiftTemplate, Shift, ShiftAssignment,
        LeaveRequest, HolidayCalendar, AttendanceEvent, CoverageRequirement, SwapRequest,
        DatasetRun, AnomalyRecord
    )

    print(f"[ProfileManager] Seeding {profile_name} from {dataset_dir} into {db_file}...")
    dataset_json_path = os.path.join(dataset_dir, "dataset.json")
    anomalies_csv_path = os.path.join(dataset_dir, "anomaly_records.csv")

    if not os.path.exists(dataset_json_path):
        raise FileNotFoundError(f"Missing dataset.json at {dataset_json_path}")

    with open(dataset_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    anomalies = []
    if os.path.exists(anomalies_csv_path):
        with open(anomalies_csv_path, "r", encoding="utf-8") as f:
            anomalies = list(csv.DictReader(f))

    # Fast bulk insertion engine
    fast_engine = create_engine(f"sqlite:///./{db_file}", connect_args={"check_same_thread": False})
    @event.listens_for(fast_engine, "connect")
    def fast_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=OFF")
        cursor.close()

    # Create tables
    Base.metadata.create_all(bind=fast_engine)
    FastSession = sessionmaker(bind=fast_engine)
    session = FastSession()

    try:
        # 1. Teams
        teams = [
            {
                "team_id": "ALL",
                "team_name": "Enterprise All Teams",
                "department": "ENTERPRISE",
                "location": "HQ-GLOBAL",
                "manager_id": None,
                "is_active": True
            }
        ] + [
            {
                "team_id": t["team_id"],
                "team_name": t["team_name"],
                "department": t["department"],
                "location": t["location"],
                "manager_id": t.get("manager_id"),
                "is_active": t["is_active"]
            }
            for t in data["teams"]
        ]
        session.bulk_insert_mappings(Team, teams)

        # 2. Skills
        session.bulk_insert_mappings(Skill, [
            {
                "skill_id": s["skill_id"],
                "skill_name": s["skill_name"],
                "category": s["category"],
                "description": s["description"],
                "is_active": s["is_active"]
            }
            for s in data["skills"]
        ])

        # 3. Shift Templates
        session.bulk_insert_mappings(ShiftTemplate, [
            {
                "template_id": tmpl["template_id"],
                "template_name": tmpl["template_name"],
                "start_time": tmpl["start_time"],
                "end_time": tmpl["end_time"],
                "break_duration_hours": tmpl["break_duration_hours"],
                "category": tmpl["category"],
                "duration_hours": tmpl["duration_hours"],
                "is_overnight": tmpl["is_overnight"],
                "applicable_days": tmpl["applicable_days"],
                "is_active": tmpl["is_active"]
            }
            for tmpl in data["shift_templates"]
        ])

        # 4. Employees
        session.bulk_insert_mappings(Employee, [
            {
                "employee_id": e["employee_id"],
                "team_id": e["team_id"],
                "first_name": e["first_name"],
                "last_name": e["last_name"],
                "email": e["email"],
                "password_hash": e["password_hash"],
                "role": e["role"],
                "employment_type": e["employment_type"],
                "employment_status": e["employment_status"],
                "hire_date": date.fromisoformat(e["hire_date"]),
                "work_zone": e["work_zone"],
                "contracted_weekly_hours": e["contracted_weekly_hours"],
                "max_working_hours": e["max_working_hours"],
                "overtime_cap_hours": e["overtime_cap_hours"],
                "is_active": e["is_active"]
            }
            for e in data["employees"]
        ])

        # 5. Employee Skills
        session.bulk_insert_mappings(EmployeeSkill, [
            {
                "id": es["id"],
                "employee_id": es["employee_id"],
                "skill_id": es["skill_id"],
                "proficiency_level": es["proficiency_level"],
                "is_certified": es["is_certified"],
                "certification_expiry_date": date.fromisoformat(es["certification_expiry_date"]) if es.get("certification_expiry_date") else None,
                "effective_start_date": date.fromisoformat(es["effective_start_date"])
            }
            for es in data["employee_skills"]
        ])

        # 6. Coverage Requirements
        session.bulk_insert_mappings(CoverageRequirement, [
            {
                "requirement_id": cov["requirement_id"],
                "team_id": cov["team_id"],
                "template_id": cov["template_id"],
                "skill_id": cov["skill_id"],
                "min_employees": cov["min_employees"],
                "effective_start_date": date.fromisoformat(cov["effective_start_date"])
            }
            for cov in data["coverage_requirements"]
        ])

        # 7. Holiday Calendar
        session.bulk_insert_mappings(HolidayCalendar, [
            {
                "holiday_id": hol["holiday_id"],
                "holiday_name": hol["holiday_name"],
                "holiday_date": date.fromisoformat(hol["holiday_date"]),
                "applicable_location": hol["applicable_location"],
                "holiday_category": hol["holiday_category"]
            }
            for hol in data["holiday_calendar"]
        ])

        # 8. Shifts
        session.bulk_insert_mappings(Shift, [
            {
                "shift_id": s["shift_id"],
                "template_id": s["template_id"],
                "team_id": s["team_id"],
                "shift_date": date.fromisoformat(s["shift_date"]),
                "start_datetime": datetime.fromisoformat(s["start_datetime"]),
                "end_datetime": datetime.fromisoformat(s["end_datetime"]),
                "timezone": s["timezone"],
                "status": s["status"]
            }
            for s in data["shifts"]
        ])

        # 9. Shift Assignments
        session.bulk_insert_mappings(ShiftAssignment, [
            {
                "assignment_id": a["assignment_id"],
                "shift_id": a["shift_id"],
                "employee_id": a["employee_id"],
                "assignment_status": a["assignment_status"],
                "assignment_source": a["assignment_source"],
                "schedule_run_id": a.get("schedule_run_id")
            }
            for a in data["shift_assignments"]
        ])

        # 10. Leave Requests
        session.bulk_insert_mappings(LeaveRequest, [
            {
                "leave_id": l["leave_id"],
                "employee_id": l["employee_id"],
                "leave_type": l["leave_type"],
                "start_date": date.fromisoformat(l["start_date"]),
                "end_date": date.fromisoformat(l["end_date"]),
                "request_date": datetime.fromisoformat(l["request_date"]),
                "approval_status": l["approval_status"],
                "approver_id": l.get("approver_id"),
                "approval_timestamp": datetime.fromisoformat(l["approval_timestamp"]) if l.get("approval_timestamp") else None,
                "rejection_reason": l.get("rejection_reason")
            }
            for l in data["leave_requests"]
        ])

        # 11. Attendance Events
        session.bulk_insert_mappings(AttendanceEvent, [
            {
                "attendance_id": att["attendance_id"],
                "employee_id": att["employee_id"],
                "assignment_id": att.get("assignment_id"),
                "event_type": att["event_type"],
                "event_timestamp": datetime.fromisoformat(att["event_timestamp"]),
                "source": att["source"],
                "status": att["status"]
            }
            for att in data["attendance_events"]
        ])

        # 12. Swap Requests
        session.bulk_insert_mappings(SwapRequest, [
            {
                "swap_id": sw["swap_id"],
                "requesting_employee_id": sw["requesting_employee_id"],
                "receiving_employee_id": sw["receiving_employee_id"],
                "original_assignment_id": sw["original_assignment_id"],
                "proposed_assignment_id": sw["proposed_assignment_id"],
                "request_timestamp": datetime.fromisoformat(sw["request_timestamp"]),
                "status": sw["status"],
                "manager_approver_id": sw.get("manager_approver_id"),
                "approval_timestamp": datetime.fromisoformat(sw["approval_timestamp"]) if sw.get("approval_timestamp") else None,
                "rejection_reason": sw.get("rejection_reason")
            }
            for sw in data["swap_requests"]
        ])

        # 13. Anomaly Records
        session.bulk_insert_mappings(AnomalyRecord, [
            {
                "anomaly_id": anom["anomaly_id"],
                "issue_type": anom["issue_type"],
                "entity_type": anom["entity_type"],
                "record_id": anom["record_id"],
                "expected_detection": anom["expected_detection"],
                "expected_business_decision": anom["expected_business_decision"],
                "severity": anom["severity"],
                "injection_method": anom["injection_method"]
            }
            for anom in anomalies
        ])

        # 14. DatasetRun
        session.add(DatasetRun(
            run_id=f"DSR-2026-PROFILE-{profile_name}",
            profile=profile_name,
            seed=20261022,
            row_counts_json=json.dumps({
                "employees": len(data["employees"]),
                "teams": len(data["teams"]),
                "shifts": len(data["shifts"]),
                "assignments": len(data["shift_assignments"]),
                "leaves": len(data["leave_requests"]),
                "attendance": len(data["attendance_events"])
            }),
            checksum="DETERMINISTIC_SEED_20261022"
        ))

        session.commit()
        print(f"[ProfileManager] Successfully seeded {profile_name} into {db_file}!")
    finally:
        session.close()
        fast_engine.dispose()


def ensure_profile_database(profile_name: str) -> None:
    """Ensures the SQLite database for the requested profile exists and is populated."""
    prof = profile_name.upper().strip()
    db_file = get_db_path_for_profile(prof)

    if prof == PROFILE_STARTER:
        if not os.path.exists(db_file):
            if os.path.exists("workforce.db"):
                print(f"[ProfileManager] Initializing {db_file} from existing workforce.db...")
                shutil.copyfile("workforce.db", db_file)
            else:
                seed_database_from_dataset(db_file, "datasets/starter", PROFILE_STARTER)
    elif prof == PROFILE_FULL:
        if not is_profile_generated(PROFILE_FULL):
            print(f"[ProfileManager] Generating and seeding FULL profile database...")
            # If dataset.json does not exist, synthesize it
            if not os.path.exists("datasets/full/dataset.json"):
                from data_engine.generators.synthetic_dataset import SyntheticDataGenerator
                from data_engine.anomaly_injection.injector import AnomalyInjector
                from data_engine.ground_truth.vault import GroundTruthVault
                from data_engine.exporters.dataset_exporter import DatasetExporter
                from data_engine.validators.integrity_validator import IntegrityValidator

                gen = SyntheticDataGenerator(profile_name="FULL", seed=20261022)
                baseline = gen.generate_all()
                validator = IntegrityValidator()
                val_report = validator.validate_dataset(baseline)
                injector = AnomalyInjector(seed=20261022)
                active_data, anom_recs, gt = injector.inject_anomalies(baseline)
                vault = GroundTruthVault(base_dir="datasets/ground_truth")
                vault.save_ground_truth(gt)
                exporter = DatasetExporter(output_dir="datasets/full")
                exporter.export_all(active_data, "FULL", 20261022, val_report, gt, anom_recs)

            seed_database_from_dataset(db_file, "datasets/full", PROFILE_FULL)


def get_profile_statistics(profile_name: str) -> Dict[str, Any]:
    """Retrieves live record counts from the profile's active database."""
    prof = profile_name.upper().strip()
    ensure_profile_database(prof)
    eng = get_engine_for_profile(prof)
    meta = PROFILE_METADATA.get(prof, {})
    
    with eng.connect() as conn:
        def cnt(table: str) -> int:
            try:
                res = conn.execute(text(f"SELECT count(*) FROM {table};")).scalar()
                return int(res or 0)
            except Exception:
                return 0

        return {
            "profile": prof,
            "name": meta.get("name", prof),
            "badge_label": meta.get("badge_label", ""),
            "horizon_days": meta.get("horizon_days", 14),
            "start_date": meta.get("start_date", "2026-01-01"),
            "end_date": meta.get("end_date", "2026-01-14"),
            "is_active": prof == _active_profile,
            "counts": {
                "employees": cnt("employees"),
                "teams": cnt("teams"),
                "skills": cnt("skills"),
                "shift_templates": cnt("shift_templates"),
                "shifts": cnt("shifts"),
                "shift_assignments": cnt("shift_assignments"),
                "leave_requests": cnt("leave_requests"),
                "attendance_events": cnt("attendance_events"),
                "swap_requests": cnt("swap_requests"),
                "coverage_requirements": cnt("coverage_requirements"),
                "anomaly_records": cnt("anomaly_records")
            }
        }

