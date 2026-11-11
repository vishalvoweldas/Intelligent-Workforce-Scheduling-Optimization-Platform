"""SQLAlchemy 2.0 ORM Entity Definitions."""
from datetime import datetime, date, time
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Date, DateTime, Time, Text, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from backend.models.database import Base

class Employee(Base):
    __tablename__ = "employees"

    employee_id = Column(String(32), primary_key=True, index=True)  # EMP-XXXXXX
    team_id = Column(String(32), ForeignKey("teams.team_id"), nullable=False, index=True)
    first_name = Column(String(64), nullable=False)
    last_name = Column(String(64), nullable=False)
    email = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False, default="")
    role = Column(String(32), nullable=False, default="EMPLOYEE")  # EMPLOYEE, MANAGER, HR_PARTNER, OPERATIONS, ADMIN
    employment_type = Column(String(32), nullable=False, default="FULL_TIME")  # FULL_TIME, PART_TIME, CONTRACTOR
    employment_status = Column(String(32), nullable=False, default="ACTIVE")  # ACTIVE, ON_LEAVE, TERMINATED
    hire_date = Column(Date, nullable=False, default=date.today)
    work_zone = Column(String(64), nullable=False, default="ZONE-A")
    contracted_weekly_hours = Column(Float, nullable=False, default=40.0)
    max_working_hours = Column(Float, nullable=False, default=48.0)
    overtime_cap_hours = Column(Float, nullable=False, default=8.0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    team = relationship("Team", foreign_keys=[team_id], back_populates="members")
    skills = relationship("EmployeeSkill", back_populates="employee", cascade="all, delete-orphan")
    assignments = relationship("ShiftAssignment", back_populates="employee")
    leave_requests = relationship("LeaveRequest", foreign_keys="LeaveRequest.employee_id", back_populates="employee")
    attendance_events = relationship("AttendanceEvent", back_populates="employee")

class Team(Base):
    __tablename__ = "teams"

    team_id = Column(String(32), primary_key=True, index=True)  # TEAM-XXX
    team_name = Column(String(128), unique=True, nullable=False)
    department = Column(String(128), nullable=False)
    location = Column(String(128), nullable=False)
    manager_id = Column(String(32), nullable=True)  # EMP-XXXXXX
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    members = relationship("Employee", foreign_keys="Employee.team_id", back_populates="team")
    shifts = relationship("Shift", back_populates="team")
    coverage_requirements = relationship("CoverageRequirement", back_populates="team")

class Skill(Base):
    __tablename__ = "skills"

    skill_id = Column(String(32), primary_key=True, index=True)  # SKL-XXX
    skill_name = Column(String(128), unique=True, nullable=False)
    category = Column(String(64), nullable=False)  # CLINICAL, HEAVY_MACHINERY, SUPPORT, SAFETY
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    employee_skills = relationship("EmployeeSkill", back_populates="skill")
    coverage_requirements = relationship("CoverageRequirement", back_populates="skill")

class EmployeeSkill(Base):
    __tablename__ = "employee_skills"

    id = Column(String(64), primary_key=True)  # ESK-XXXXXX
    employee_id = Column(String(32), ForeignKey("employees.employee_id"), nullable=False, index=True)
    skill_id = Column(String(32), ForeignKey("skills.skill_id"), nullable=False, index=True)
    proficiency_level = Column(String(32), nullable=False, default="INTERMEDIATE")  # BEGINNER, INTERMEDIATE, EXPERT
    is_certified = Column(Boolean, nullable=False, default=True)
    certification_expiry_date = Column(Date, nullable=True)
    effective_start_date = Column(Date, nullable=False, default=date.today)
    effective_end_date = Column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("employee_id", "skill_id", name="uq_emp_skill"),
    )

    # Relationships
    employee = relationship("Employee", back_populates="skills")
    skill = relationship("Skill", back_populates="employee_skills")

class ShiftTemplate(Base):
    __tablename__ = "shift_templates"

    template_id = Column(String(32), primary_key=True, index=True)  # TMPL-XXX
    template_name = Column(String(64), nullable=False)
    start_time = Column(String(8), nullable=False)  # "08:00"
    end_time = Column(String(8), nullable=False)    # "16:30"
    break_duration_hours = Column(Float, nullable=False, default=0.5)
    category = Column(String(32), nullable=False)  # MORNING, AFTERNOON, NIGHT, WEEKEND
    duration_hours = Column(Float, nullable=False, default=8.0)
    is_overnight = Column(Boolean, nullable=False, default=False)
    applicable_days = Column(String(64), nullable=False, default="MON,TUE,WED,THU,FRI")
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    shifts = relationship("Shift", back_populates="template")
    coverage_requirements = relationship("CoverageRequirement", back_populates="template")

class Shift(Base):
    __tablename__ = "shifts"

    shift_id = Column(String(64), primary_key=True, index=True)  # SHIFT-YYYY-MM-DD-X
    template_id = Column(String(32), ForeignKey("shift_templates.template_id"), nullable=False, index=True)
    team_id = Column(String(32), ForeignKey("teams.team_id"), nullable=False, index=True)
    shift_date = Column(Date, nullable=False, index=True)
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    timezone = Column(String(32), nullable=False, default="UTC")
    status = Column(String(32), nullable=False, default="SCHEDULED")  # PLANNED, SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED

    __table_args__ = (
        Index("idx_shift_team_date", "team_id", "shift_date"),
    )

    # Relationships
    template = relationship("ShiftTemplate", back_populates="shifts")
    team = relationship("Team", back_populates="shifts")
    assignments = relationship("ShiftAssignment", back_populates="shift", cascade="all, delete-orphan")

class ShiftAssignment(Base):
    __tablename__ = "shift_assignments"

    assignment_id = Column(String(64), primary_key=True, index=True)  # ASGN-XXXXXX
    shift_id = Column(String(64), ForeignKey("shifts.shift_id"), nullable=False, index=True)
    employee_id = Column(String(32), ForeignKey("employees.employee_id"), nullable=False, index=True)
    assignment_status = Column(String(32), nullable=False, default="ASSIGNED")  # ASSIGNED, CONFIRMED, SWAPPED, CANCELLED
    assignment_source = Column(String(32), nullable=False, default="OPTIMIZER")  # OPTIMIZER, MANUAL, SWAP
    schedule_run_id = Column(String(64), nullable=True)
    assigned_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    shift = relationship("Shift", back_populates="assignments")
    employee = relationship("Employee", back_populates="assignments")
    attendance_events = relationship("AttendanceEvent", back_populates="assignment")

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    leave_id = Column(String(64), primary_key=True, index=True)  # LVE-YYYY-XXXXXX
    employee_id = Column(String(32), ForeignKey("employees.employee_id"), nullable=False, index=True)
    leave_type = Column(String(32), nullable=False, default="ANNUAL")  # ANNUAL, SICK, UNPAID, PARENTAL
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    request_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    approval_status = Column(String(32), nullable=False, default="PENDING")  # SUBMITTED, PENDING, APPROVED, REJECTED, CANCELLED
    approver_id = Column(String(32), ForeignKey("employees.employee_id"), nullable=True)
    approval_timestamp = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id], back_populates="leave_requests")
    approver = relationship("Employee", foreign_keys=[approver_id])
    approval_events = relationship("LeaveApprovalEvent", back_populates="leave_request", cascade="all, delete-orphan")

class HolidayCalendar(Base):
    __tablename__ = "holiday_calendar"

    holiday_id = Column(String(32), primary_key=True)  # HOL-XXXX
    holiday_name = Column(String(128), nullable=False)
    holiday_date = Column(Date, nullable=False, index=True)
    applicable_location = Column(String(128), nullable=False, default="GLOBAL")
    applicable_team_id = Column(String(32), nullable=True)
    holiday_category = Column(String(64), nullable=False, default="PUBLIC")

class AttendanceEvent(Base):
    __tablename__ = "attendance_events"

    attendance_id = Column(String(64), primary_key=True, index=True)  # ATT-EMP-TIMESTAMP
    employee_id = Column(String(32), ForeignKey("employees.employee_id"), nullable=False, index=True)
    assignment_id = Column(String(64), ForeignKey("shift_assignments.assignment_id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(32), nullable=False)  # CLOCK_IN, CLOCK_OUT
    event_timestamp = Column(DateTime, nullable=False, index=True)
    source = Column(String(32), nullable=False, default="BIOMETRIC")  # BIOMETRIC, WEB, MOBILE
    status = Column(String(32), nullable=False, default="ON_TIME")  # ON_TIME, LATE, EARLY_DEPARTURE, MISSED

    # Relationships
    employee = relationship("Employee", back_populates="attendance_events")
    assignment = relationship("ShiftAssignment", back_populates="attendance_events")

class CoverageRequirement(Base):
    __tablename__ = "coverage_requirements"

    requirement_id = Column(String(64), primary_key=True, index=True)  # COV-XXXXXX
    team_id = Column(String(32), ForeignKey("teams.team_id"), nullable=False, index=True)
    template_id = Column(String(32), ForeignKey("shift_templates.template_id"), nullable=False, index=True)
    skill_id = Column(String(32), ForeignKey("skills.skill_id"), nullable=False, index=True)
    min_employees = Column(Integer, nullable=False, default=1)
    effective_start_date = Column(Date, nullable=False, default=date.today)
    effective_end_date = Column(Date, nullable=True)

    # Relationships
    team = relationship("Team", back_populates="coverage_requirements")
    template = relationship("ShiftTemplate", back_populates="coverage_requirements")
    skill = relationship("Skill", back_populates="coverage_requirements")

class SwapRequest(Base):
    __tablename__ = "swap_requests"

    swap_id = Column(String(64), primary_key=True, index=True)  # SWP-YYYY-XXXXXX
    requesting_employee_id = Column(String(32), ForeignKey("employees.employee_id"), nullable=False)
    receiving_employee_id = Column(String(32), ForeignKey("employees.employee_id"), nullable=False)
    original_assignment_id = Column(String(64), ForeignKey("shift_assignments.assignment_id", ondelete="CASCADE"), nullable=False)
    proposed_assignment_id = Column(String(64), ForeignKey("shift_assignments.assignment_id", ondelete="CASCADE"), nullable=False)
    request_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String(32), nullable=False, default="PENDING_APPROVAL")  # REQUESTED, PENDING_APPROVAL, APPROVED, REJECTED, CANCELLED, APPLIED
    manager_approver_id = Column(String(32), ForeignKey("employees.employee_id"), nullable=True)
    approval_timestamp = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Relationships
    requesting_employee = relationship("Employee", foreign_keys=[requesting_employee_id])
    receiving_employee = relationship("Employee", foreign_keys=[receiving_employee_id])
    original_assignment = relationship("ShiftAssignment", foreign_keys=[original_assignment_id])
    proposed_assignment = relationship("ShiftAssignment", foreign_keys=[proposed_assignment_id])
    approver = relationship("Employee", foreign_keys=[manager_approver_id])
    approval_events = relationship("SwapApprovalEvent", back_populates="swap_request", cascade="all, delete-orphan")

# Supporting & Audit Tables

class LeaveApprovalEvent(Base):
    __tablename__ = "leave_approval_events"

    event_id = Column(String(64), primary_key=True)  # LAE-XXXXXX
    leave_id = Column(String(64), ForeignKey("leave_requests.leave_id"), nullable=False, index=True)
    actor_id = Column(String(32), ForeignKey("employees.employee_id"), nullable=False)
    decision = Column(String(32), nullable=False)  # APPROVED, REJECTED, CANCELLED
    comments = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    leave_request = relationship("LeaveRequest", back_populates="approval_events")
    actor = relationship("Employee")

class SwapApprovalEvent(Base):
    __tablename__ = "swap_approval_events"

    event_id = Column(String(64), primary_key=True)  # SAE-XXXXXX
    swap_id = Column(String(64), ForeignKey("swap_requests.swap_id"), nullable=False, index=True)
    actor_id = Column(String(32), ForeignKey("employees.employee_id"), nullable=False)
    decision = Column(String(32), nullable=False)  # APPROVED, REJECTED
    rejection_reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    swap_request = relationship("SwapRequest", back_populates="approval_events")
    actor = relationship("Employee")

class ShiftAssignmentHistory(Base):
    __tablename__ = "shift_assignment_history"

    history_id = Column(String(64), primary_key=True)  # SAH-XXXXXX
    assignment_id = Column(String(64), nullable=False, index=True)
    previous_employee_id = Column(String(32), nullable=True)
    new_employee_id = Column(String(32), nullable=False)
    change_reason = Column(String(128), nullable=False)  # OPTIMIZER_RUN, SWAP_APPROVED, MANUAL_OVERRIDE
    changed_by = Column(String(32), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

class ScheduleRun(Base):
    __tablename__ = "schedule_runs"

    run_id = Column(String(64), primary_key=True, index=True)  # RUN-YYYY-XXXXXX
    team_id = Column(String(32), ForeignKey("teams.team_id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    solver_name = Column(String(64), nullable=False, default="Google OR-Tools CP-SAT")
    solver_status = Column(String(32), nullable=False)  # OPTIMAL, FEASIBLE, INFEASIBLE, FAILED
    objective_value = Column(Float, nullable=True)
    runtime_seconds = Column(Float, nullable=False)
    shifts_assigned = Column(Integer, nullable=False, default=0)
    unfilled_shifts = Column(Integer, nullable=False, default=0)
    coverage_rate = Column(Float, nullable=False, default=1.0)
    fairness_hours_stdev = Column(Float, nullable=True)
    weights_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    gaps = relationship("ScheduleGap", back_populates="schedule_run", cascade="all, delete-orphan")

class ScheduleGap(Base):
    __tablename__ = "schedule_gaps"

    gap_id = Column(String(64), primary_key=True)  # GAP-XXXXXX
    run_id = Column(String(64), ForeignKey("schedule_runs.run_id"), nullable=False, index=True)
    shift_id = Column(String(64), ForeignKey("shifts.shift_id"), nullable=False)
    skill_id = Column(String(32), ForeignKey("skills.skill_id"), nullable=False)
    shortage_count = Column(Integer, nullable=False, default=1)
    reason = Column(Text, nullable=False)

    schedule_run = relationship("ScheduleRun", back_populates="gaps")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(String(64), primary_key=True)  # AUD-YYYYMMDD-XXXXXX
    actor_id = Column(String(32), nullable=False, index=True)
    actor_role = Column(String(32), nullable=False)
    action = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=False)
    details_json = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=False, default="127.0.0.1")
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

class DatasetRun(Base):
    __tablename__ = "dataset_runs"

    run_id = Column(String(64), primary_key=True)  # DSR-YYYY-XXXXXX
    profile = Column(String(32), nullable=False)   # STARTER, FULL
    seed = Column(Integer, nullable=False)
    row_counts_json = Column(Text, nullable=False)
    checksum = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class AnomalyRecord(Base):
    __tablename__ = "anomaly_records"

    anomaly_id = Column(String(64), primary_key=True, index=True)  # ANOM-XXXXXX
    issue_type = Column(String(64), nullable=False, index=True)   # DOUBLE_BOOKING, LEAVE_CONFLICT, MISSING_SKILL, OVERTIME_EXCEEDED, UNAPPROVED_SWAP
    entity_type = Column(String(64), nullable=False)
    record_id = Column(String(64), nullable=False)
    expected_detection = Column(String(128), nullable=False)
    expected_business_decision = Column(String(128), nullable=False)
    severity = Column(String(32), nullable=False, default="HIGH")  # CRITICAL, HIGH, MEDIUM, LOW
    injection_method = Column(String(128), nullable=False)
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    eval_id = Column(String(64), primary_key=True, index=True)  # EVAL-YYYYMMDD-XXXXXX
    dataset_run_id = Column(String(64), nullable=True)
    confusion_matrix_json = Column(Text, nullable=False)
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    f1_score = Column(Float, nullable=False)
    metrics_by_category_json = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

