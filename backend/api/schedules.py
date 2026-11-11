"""Constraint Optimization Solver & Schedule Execution Endpoints with RBAC."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import Optional, List
from backend.models.database import get_db
from backend.models.entities import (
    Employee, Shift, ShiftAssignment, CoverageRequirement, EmployeeSkill, LeaveRequest,
    ScheduleRun, ScheduleGap, AuditLog, AttendanceEvent, SwapRequest, SwapApprovalEvent
)
from backend.schemas.schemas import ScheduleRunRequest
from backend.scheduling.optimizer import ScheduleOptimizer
from backend.services.id_generator import IdGenerator
from backend.security.rbac import (
    CurrentUser, get_current_user, resolve_current_user,
    ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_HR_PARTNER, ROLE_OPERATIONS, ROLE_ADMIN,
    verify_team_scope
)

router = APIRouter(prefix="/schedules", tags=["Schedules & Optimizer"])

@router.post("/run")
def run_schedule_optimizer(
    request: ScheduleRunRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Executes Google OR-Tools CP-SAT solver against database constraints.
    
    RBAC Rules:
    - EMPLOYEE: Denied (HTTP 403)
    - MANAGER: Restricted strictly to own team_id
    - OPERATIONS & ADMIN: Unrestricted
    """
    current_user = resolve_current_user(current_user, db)
    # 1. Role Enforcement
    if current_user.role == ROLE_EMPLOYEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Frontline employees are not permitted to trigger shift schedule optimization."
        )

    target_team = request.team_id
    if current_user.role == ROLE_MANAGER:
        if target_team and target_team != current_user.team_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Managers can only optimize shifts for their managed team ({current_user.team_id})."
            )
        target_team = current_user.team_id

    # 2. Fetch relevant shifts
    shift_query = db.query(Shift).filter(
        Shift.shift_date >= date.fromisoformat(request.start_date),
        Shift.shift_date <= date.fromisoformat(request.end_date)
    )
    if target_team:
        shift_query = shift_query.filter(Shift.team_id == target_team)
    shifts = shift_query.all()

    if not shifts:
        raise HTTPException(
            status_code=400,
            detail=f"No shifts found in the specified date range ({request.start_date} to {request.end_date}) for team {target_team or 'ALL'}."
        )

    # 3. Fetch active employees
    emp_query = db.query(Employee).filter(Employee.is_active == True)
    if target_team:
        emp_query = emp_query.filter(Employee.team_id == target_team)
    employees = emp_query.all()

    if not employees:
        raise HTTPException(status_code=400, detail="No active employees found to schedule in the specified scope.")

    # 4. Fetch skills, coverage requirements, and approved leaves
    emp_ids = [e.employee_id for e in employees]
    team_ids = list({s.team_id for s in shifts})

    emp_skills = db.query(EmployeeSkill).filter(EmployeeSkill.employee_id.in_(emp_ids)).all()
    cov_reqs = db.query(CoverageRequirement).filter(CoverageRequirement.team_id.in_(team_ids)).all()
    approved_leaves = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id.in_(emp_ids),
        LeaveRequest.approval_status == "APPROVED"
    ).all()

    # Convert to dicts for solver adapter
    shifts_dicts = [
        {
            "shift_id": s.shift_id,
            "template_id": s.template_id,
            "team_id": s.team_id,
            "shift_date": s.shift_date.isoformat(),
            "start_datetime": s.start_datetime.isoformat(),
            "end_datetime": s.end_datetime.isoformat()
        }
        for s in shifts
    ]

    emp_dicts = [
        {
            "employee_id": e.employee_id,
            "team_id": e.team_id,
            "is_active": e.is_active,
            "employment_status": e.employment_status,
            "contracted_weekly_hours": e.contracted_weekly_hours,
            "max_working_hours": e.max_working_hours,
            "overtime_cap_hours": e.overtime_cap_hours
        }
        for e in employees
    ]

    emp_skills_dicts = [
        {
            "employee_id": es.employee_id,
            "skill_id": es.skill_id,
            "is_certified": es.is_certified
        }
        for es in emp_skills
    ]

    cov_dicts = [
        {
            "team_id": cr.team_id,
            "template_id": cr.template_id,
            "skill_id": cr.skill_id,
            "min_employees": cr.min_employees
        }
        for cr in cov_reqs
    ]

    leaves_dicts = [
        {
            "employee_id": l.employee_id,
            "start_date": l.start_date.isoformat(),
            "end_date": l.end_date.isoformat(),
            "approval_status": l.approval_status
        }
        for l in approved_leaves
    ]

    # Instantiate and execute solver
    optimizer = ScheduleOptimizer(
        employees=emp_dicts,
        shifts=shifts_dicts,
        coverage_requirements=cov_dicts,
        employee_skills=emp_skills_dicts,
        approved_leaves=leaves_dicts,
        weights=request.weights,
        timeout_seconds=request.timeout_seconds,
        seed=request.seed
    )

    result = optimizer.solve()

    # Persist Schedule Run and Gaps in DB
    year = date.fromisoformat(request.start_date).year
    existing_runs = db.query(ScheduleRun.run_id).all()
    max_run_idx = max([int(rid.split("-")[2]) for (rid,) in existing_runs if rid.startswith(f"RUN-{year}-")] or [0])
    run_count = max_run_idx + 1
    run_id = IdGenerator.schedule_run(year, run_count)

    run_record = ScheduleRun(
        run_id=run_id,
        team_id=target_team or "ALL",
        start_date=date.fromisoformat(request.start_date),
        end_date=date.fromisoformat(request.end_date),
        solver_name="Google OR-Tools CP-SAT",
        solver_status=result["status"],
        objective_value=result["objective_value"],
        runtime_seconds=result["runtime_seconds"],
        shifts_assigned=result["assigned_shifts"],
        unfilled_shifts=result["unfilled_shifts"],
        coverage_rate=result["coverage_rate"]
    )
    db.add(run_record)

    # Save gaps
    for idx, gap in enumerate(result.get("gaps", []), start=1):
        db.add(ScheduleGap(
            gap_id=f"GAP-{run_id}-{idx:03d}",
            run_id=run_id,
            shift_id=gap["shift_id"],
            skill_id=gap["skill_id"],
            shortage_count=gap["shortage_count"],
            reason=gap["reason"]
        ))

    # If feasible, apply assignments
    if result["status"] in ("OPTIMAL", "FEASIBLE"):
        shift_ids = [s["shift_id"] for s in shifts_dicts]

        # 1. Collect old assignment IDs for these shifts
        old_asgn_ids = [r[0] for r in db.query(ShiftAssignment.assignment_id).filter(ShiftAssignment.shift_id.in_(shift_ids)).all()]

        if old_asgn_ids:
            # 2. Nullify assignment_id on attendance events to preserve clock-in/out records
            db.query(AttendanceEvent).filter(AttendanceEvent.assignment_id.in_(old_asgn_ids)).update(
                {AttendanceEvent.assignment_id: None}, synchronize_session=False
            )

            # 3. Remove obsolete swap requests and their approval events that reference these assignments
            obsolete_swaps = db.query(SwapRequest).filter(
                (SwapRequest.original_assignment_id.in_(old_asgn_ids)) |
                (SwapRequest.proposed_assignment_id.in_(old_asgn_ids))
            ).all()
            obsolete_swap_ids = [s.swap_id for s in obsolete_swaps]

            if obsolete_swap_ids:
                db.query(SwapApprovalEvent).filter(SwapApprovalEvent.swap_id.in_(obsolete_swap_ids)).delete(synchronize_session=False)
                db.query(SwapRequest).filter(SwapRequest.swap_id.in_(obsolete_swap_ids)).delete(synchronize_session=False)

            # 4. Remove old assignments and clear session identity map
            db.query(ShiftAssignment).filter(ShiftAssignment.shift_id.in_(shift_ids)).delete(synchronize_session=False)
            db.expire_all()

        # 5. Insert newly optimized assignments with monotonic unique IDs
        existing_asgns = db.query(ShiftAssignment.assignment_id).all()
        numeric_indices = [
            int(parts[1])
            for (aid,) in existing_asgns
            for parts in [aid.split("-")]
            if len(parts) > 1 and parts[1].isdigit()
        ]
        max_asgn_idx = max(numeric_indices or [0])
        asgn_count = max_asgn_idx + 1

        new_assignments = []
        for asgn in result["assignments"]:
            new_asgn = ShiftAssignment(
                assignment_id=IdGenerator.assignment(asgn_count),
                shift_id=asgn["shift_id"],
                employee_id=asgn["employee_id"],
                assignment_status="ASSIGNED",
                assignment_source="OPTIMIZER",
                schedule_run_id=run_id
            )
            db.add(new_asgn)
            new_assignments.append(new_asgn)
            asgn_count += 1

        db.flush()

        # 6. Re-link attendance events in-memory where employee matches and event is within the shift timeframe
        shift_dict_by_id = {s.shift_id: s for s in shifts}
        unlinked_events = db.query(AttendanceEvent).filter(
            AttendanceEvent.employee_id.in_(emp_ids),
            AttendanceEvent.assignment_id == None
        ).all()

        for ev in unlinked_events:
            for asgn in new_assignments:
                if asgn.employee_id == ev.employee_id:
                    s = shift_dict_by_id.get(asgn.shift_id)
                    if s and s.start_datetime and s.end_datetime:
                        if (s.start_datetime - timedelta(hours=2)) <= ev.event_timestamp <= (s.end_datetime + timedelta(hours=2)):
                            ev.assignment_id = asgn.assignment_id
                            break

    # Record Audit Log
    db.add(AuditLog(
        log_id=IdGenerator.audit_log(datetime.utcnow(), run_count),
        actor_id=current_user.employee_id,
        actor_role=current_user.role,
        action="RUN_SCHEDULE_OPTIMIZER",
        entity_type="SCHEDULE_RUN",
        entity_id=run_id,
        details_json=f"Scope: {target_team or 'ALL'}, Status: {result['status']}, Assigned: {result['assigned_shifts']}, Unfilled: {result['unfilled_shifts']}"
    ))

    db.commit()

    return {
        "schedule_run_id": run_id,
        "status": result["status"],
        "runtime_seconds": result["runtime_seconds"],
        "objective_value": result["objective_value"],
        "total_shifts": result["total_shifts"],
        "assigned_shifts": result["assigned_shifts"],
        "unfilled_shifts": result["unfilled_shifts"],
        "coverage_rate": result["coverage_rate"],
        "gaps": result.get("gaps", []),
        "solver_info": result.get("solver_info", {})
    }

@router.post("/publish")
def publish_schedule(
    start_date: str,
    end_date: str,
    team_id: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Publishes shift assignments for a horizon, making them official.
    
    Restricted to MANAGER (for own team) and ADMIN.
    """
    current_user = resolve_current_user(current_user, db)
    if current_user.role == ROLE_EMPLOYEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Frontline employees cannot publish schedules."
        )

    target_team = team_id
    if current_user.role == ROLE_MANAGER:
        if target_team and target_team != current_user.team_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Managers can only publish schedules for their managed team ({current_user.team_id})."
            )
        target_team = current_user.team_id

    query = db.query(Shift).filter(
        Shift.shift_date >= date.fromisoformat(start_date),
        Shift.shift_date <= date.fromisoformat(end_date)
    )
    if target_team:
        query = query.filter(Shift.team_id == target_team)

    shifts = query.all()
    for s in shifts:
        s.status = "PUBLISHED"

    db.add(AuditLog(
        log_id=IdGenerator.audit_log(datetime.utcnow(), 1),
        actor_id=current_user.employee_id,
        actor_role=current_user.role,
        action="PUBLISH_SCHEDULE",
        entity_type="SCHEDULE",
        entity_id=f"{start_date}_{end_date}",
        details_json=f"Published {len(shifts)} shifts for team {target_team or 'ALL'}"
    ))
    db.commit()

    return {
        "success": True,
        "message": f"Successfully published {len(shifts)} shifts for {start_date} to {end_date}."
    }

@router.get("/my")
def get_my_schedule(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns shift assignments personal to the currently logged in employee."""
    current_user = resolve_current_user(current_user, db)
    assignments = db.query(ShiftAssignment).filter(
        ShiftAssignment.employee_id == current_user.employee_id
    ).all()

    shift_ids = [a.shift_id for a in assignments]
    shifts = {s.shift_id: s for s in db.query(Shift).filter(Shift.shift_id.in_(shift_ids)).all()}

    return [
        {
            "assignment_id": a.assignment_id,
            "shift_id": a.shift_id,
            "shift_date": shifts[a.shift_id].shift_date.isoformat() if a.shift_id in shifts else "",
            "start_datetime": shifts[a.shift_id].start_datetime.isoformat() if a.shift_id in shifts else "",
            "end_datetime": shifts[a.shift_id].end_datetime.isoformat() if a.shift_id in shifts else "",
            "template_id": shifts[a.shift_id].template_id if a.shift_id in shifts else "",
            "team_id": shifts[a.shift_id].team_id if a.shift_id in shifts else "",
            "assignment_status": a.assignment_status,
            "assigned_at": a.assigned_at.isoformat()
        }
        for a in assignments
    ]

@router.get("/runs")
def list_schedule_runs(
    limit: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ScheduleRun)
    if current_user.role == ROLE_MANAGER:
        query = query.filter((ScheduleRun.team_id == current_user.team_id) | (ScheduleRun.team_id == "ALL"))
    runs = query.order_by(ScheduleRun.created_at.desc()).limit(limit).all()
    return [
        {
            "run_id": r.run_id,
            "team_id": r.team_id,
            "start_date": r.start_date.isoformat(),
            "end_date": r.end_date.isoformat(),
            "solver_status": r.solver_status,
            "runtime_seconds": r.runtime_seconds,
            "shifts_assigned": r.shifts_assigned,
            "unfilled_shifts": r.unfilled_shifts,
            "coverage_rate": r.coverage_rate,
            "created_at": r.created_at.isoformat()
        }
        for r in runs
    ]
