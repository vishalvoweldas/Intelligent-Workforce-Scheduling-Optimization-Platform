"""Attendance Tracking & Overtime Reconciliation Endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
from backend.models.database import get_db
from backend.models.entities import AttendanceEvent, ShiftAssignment, Shift, Employee
from backend.schemas.schemas import AttendanceEventCreate
from backend.services.id_generator import IdGenerator
from backend.security.rbac import (
    get_current_user, CurrentUser, verify_ownership, resolve_current_user,
    ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_ADMIN, ROLE_HR_PARTNER
)

router = APIRouter(prefix="/attendance", tags=["Attendance & Overtime"])

@router.get("/events")
def list_attendance_events(
    employee_id: Optional[str] = None,
    limit: int = 100,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user = resolve_current_user(current_user, db)
    query = db.query(AttendanceEvent)

    # Scoping by Role
    if current_user.role == ROLE_EMPLOYEE:
        query = query.filter(AttendanceEvent.employee_id == current_user.employee_id)
    elif current_user.role == ROLE_MANAGER:
        team_emp_ids = [e.employee_id for e in db.query(Employee).filter(Employee.team_id == current_user.team_id).all()]
        if employee_id:
            if employee_id not in team_emp_ids and employee_id != current_user.employee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: Manager cannot view attendance events outside team {current_user.team_id}."
                )
            query = query.filter(AttendanceEvent.employee_id == employee_id)
        else:
            query = query.filter(AttendanceEvent.employee_id.in_(team_emp_ids))
    else:
        if employee_id:
            query = query.filter(AttendanceEvent.employee_id == employee_id)

    events = query.order_by(AttendanceEvent.event_timestamp.desc()).limit(limit).all()

    return [
        {
            "attendance_id": a.attendance_id,
            "employee_id": a.employee_id,
            "assignment_id": a.assignment_id,
            "event_type": a.event_type,
            "event_timestamp": a.event_timestamp.isoformat(),
            "source": a.source,
            "status": a.status
        }
        for a in events
    ]

@router.post("/events")
def record_attendance_event(
    request: AttendanceEventCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user = resolve_current_user(current_user, db)
    # Enforce ownership: frontline employees can only clock in/out for themselves
    verify_ownership(current_user, request.employee_id)

    emp = db.query(Employee).filter(Employee.employee_id == request.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    ts = datetime.fromisoformat(request.event_timestamp) if request.event_timestamp else datetime.utcnow()
    att_id = IdGenerator.attendance(request.employee_id, ts, request.event_type)

    event = AttendanceEvent(
        attendance_id=att_id,
        employee_id=request.employee_id,
        assignment_id=request.assignment_id,
        event_type=request.event_type,
        event_timestamp=ts,
        source=request.source,
        status="ON_TIME"
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return {
        "success": True,
        "message": f"{request.event_type} recorded successfully",
        "attendance_id": event.attendance_id
    }

@router.get("/reconciliation")
def reconcile_attendance(
    team_id: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reconciles scheduled shift assignments against actual clock-in/out records with RBAC scoping."""
    current_user = resolve_current_user(current_user, db)
    assignments = db.query(ShiftAssignment).all()
    shifts_by_id = {s.shift_id: s for s in db.query(Shift).all()}
    employees_by_id = {e.employee_id: e for e in db.query(Employee).all()}

    # Scope filtering based on role
    effective_team_id = team_id
    scoped_employee_id = None
    if current_user.role == ROLE_EMPLOYEE:
        scoped_employee_id = current_user.employee_id
    elif current_user.role == ROLE_MANAGER:
        effective_team_id = current_user.team_id

    # Fetch attendance events
    events = db.query(AttendanceEvent).all()
    asgn_events: dict = {}
    for ev in events:
        if ev.assignment_id:
            asgn_events.setdefault(ev.assignment_id, []).append(ev)

    reconciliation_list = []
    emp_hours: dict = {}

    for asgn in assignments:
        if scoped_employee_id and asgn.employee_id != scoped_employee_id:
            continue

        s = shifts_by_id.get(asgn.shift_id)
        if not s:
            continue
        if effective_team_id and s.team_id != effective_team_id:
            continue

        emp = employees_by_id.get(asgn.employee_id)
        if not emp:
            continue

        scheduled_hours = 8.0  # Standard shift duration
        matched_events = asgn_events.get(asgn.assignment_id, [])

        clock_in = next((ev for ev in matched_events if ev.event_type == "CLOCK_IN"), None)
        clock_out = next((ev for ev in matched_events if ev.event_type == "CLOCK_OUT"), None)

        if clock_in and clock_out:
            worked_hours = max(0.0, round((clock_out.event_timestamp - clock_in.event_timestamp).total_seconds() / 3600.0, 2))
            rec_status = clock_in.status
        elif clock_in and not clock_out:
            worked_hours = scheduled_hours
            rec_status = "MISSED_CLOCK_OUT"
        else:
            worked_hours = 0.0
            rec_status = "ABSENT"

        emp_hours[emp.employee_id] = emp_hours.get(emp.employee_id, 0.0) + worked_hours

        reconciliation_list.append({
            "assignment_id": asgn.assignment_id,
            "employee_id": emp.employee_id,
            "employee_name": f"{emp.first_name} {emp.last_name}",
            "shift_id": s.shift_id,
            "shift_date": s.shift_date.isoformat(),
            "scheduled_hours": scheduled_hours,
            "actual_worked_hours": worked_hours,
            "status": rec_status,
            "clock_in": clock_in.event_timestamp.isoformat() if clock_in else None,
            "clock_out": clock_out.event_timestamp.isoformat() if clock_out else None
        })

    # Summary by employee including overtime
    summary = []
    for emp_id, total_worked in emp_hours.items():
        emp = employees_by_id.get(emp_id)
        contract = emp.contracted_weekly_hours if emp else 40.0
        overtime = max(0.0, round(total_worked - contract, 2))
        summary.append({
            "employee_id": emp_id,
            "employee_name": f"{emp.first_name} {emp.last_name}" if emp else emp_id,
            "contracted_hours": contract,
            "total_worked_hours": total_worked,
            "regular_hours": min(contract, total_worked),
            "overtime_hours": overtime,
            "overtime_cap": emp.overtime_cap_hours if emp else 8.0,
            "cap_exceeded": overtime > (emp.overtime_cap_hours if emp else 8.0)
        })

    return {
        "reconciliation": reconciliation_list[:100],
        "employee_overtime_summary": summary[:50]
    }
