"""Leave Management & Approval Workflow Endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import Optional, List
from backend.models.database import get_db
from backend.models.entities import (
    LeaveRequest, LeaveApprovalEvent, Employee, AuditLog,
    ShiftAssignment, Shift, AttendanceEvent, SwapRequest, ShiftAssignmentHistory
)
from backend.schemas.schemas import LeaveSubmitRequest, LeaveDecisionRequest
from backend.services.id_generator import IdGenerator
from backend.security.rbac import (
    get_current_user, CurrentUser, verify_ownership, resolve_current_user,
    ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_ADMIN, ROLE_HR_PARTNER
)

router = APIRouter(prefix="/leave-requests", tags=["Leave Management"])

@router.get("")
def list_leave_requests(
    employee_id: Optional[str] = None,
    team_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user = resolve_current_user(current_user, db)
    query = db.query(LeaveRequest)

    # RBAC Data Scoping
    if current_user.role == ROLE_EMPLOYEE:
        # Frontline employees can only see their own leave requests
        query = query.filter(LeaveRequest.employee_id == current_user.employee_id)
    elif current_user.role == ROLE_MANAGER:
        # Managers can see their own team's requests or their own requests
        if employee_id:
            target_emp = db.query(Employee).filter(Employee.employee_id == employee_id).first()
            if target_emp and target_emp.team_id != current_user.team_id and employee_id != current_user.employee_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Forbidden: Manager cannot view leave requests for employee outside team {current_user.team_id}."
                )
            query = query.filter(LeaveRequest.employee_id == employee_id)
        else:
            query = query.join(Employee, LeaveRequest.employee_id == Employee.employee_id).filter(
                (Employee.team_id == current_user.team_id) | (LeaveRequest.employee_id == current_user.employee_id)
            )
    else:
        # HR, Operations, Admin
        if employee_id:
            query = query.filter(LeaveRequest.employee_id == employee_id)
        if team_id:
            query = query.join(Employee, LeaveRequest.employee_id == Employee.employee_id).filter(Employee.team_id == team_id)

    if status_filter:
        query = query.filter(LeaveRequest.approval_status == status_filter)

    total = query.count()
    leaves = query.order_by(LeaveRequest.request_date.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "leave_id": l.leave_id,
                "employee_id": l.employee_id,
                "employee_name": f"{l.employee.first_name} {l.employee.last_name}" if l.employee else l.employee_id,
                "leave_type": l.leave_type,
                "start_date": l.start_date.isoformat(),
                "end_date": l.end_date.isoformat(),
                "request_date": l.request_date.isoformat(),
                "approval_status": l.approval_status,
                "approver_id": l.approver_id,
                "rejection_reason": l.rejection_reason
            }
            for l in leaves
        ]
    }

@router.post("")
def submit_leave_request(
    request: LeaveSubmitRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user = resolve_current_user(current_user, db)
    # Enforce ownership: frontline employees cannot submit on behalf of others
    verify_ownership(current_user, request.employee_id)

    # Validate employee exists
    emp = db.query(Employee).filter(Employee.employee_id == request.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    s_dt = date.fromisoformat(request.start_date)
    e_dt = date.fromisoformat(request.end_date)
    if s_dt > e_dt:
        raise HTTPException(status_code=400, detail="Start date cannot be after end date")

    # Monotonic ID generation
    existing_leaves = db.query(LeaveRequest.leave_id).all()
    max_idx = 0
    year = s_dt.year or 2026
    for (lid,) in existing_leaves:
        parts = lid.split("-")
        if len(parts) >= 3 and parts[-1].isdigit():
            max_idx = max(max_idx, int(parts[-1]))
    leave_id = IdGenerator.leave(year, max_idx + 1)

    leave = LeaveRequest(
        leave_id=leave_id,
        employee_id=request.employee_id,
        leave_type=request.leave_type,
        start_date=s_dt,
        end_date=e_dt,
        approval_status="PENDING",
        request_date=datetime.utcnow()
    )
    db.add(leave)

    db.add(AuditLog(
        log_id=IdGenerator.audit_log(datetime.utcnow(), max_idx + 1),
        actor_id=current_user.employee_id,
        actor_role=current_user.role,
        action="SUBMIT_LEAVE_REQUEST",
        entity_type="LEAVE_REQUEST",
        entity_id=leave_id,
        details_json=f"Type: {request.leave_type}, Dates: {request.start_date} to {request.end_date}"
    ))

    db.commit()
    db.refresh(leave)

    return {
        "success": True,
        "message": "Leave request submitted successfully",
        "leave_id": leave.leave_id,
        "status": leave.approval_status
    }

@router.post("/{leave_id}/decide")
def decide_leave_request(
    leave_id: str,
    request: LeaveDecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user = resolve_current_user(current_user, db)
    # Role authorization
    if current_user.role not in (ROLE_MANAGER, ROLE_ADMIN, ROLE_HR_PARTNER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only Managers, HR, or Administrators can approve/reject leave requests."
        )

    leave = db.query(LeaveRequest).filter(LeaveRequest.leave_id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    if request.decision not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=400, detail="Decision must be APPROVED or REJECTED")

    # Anti-Corruption: Prevent self-approval
    if leave.employee_id == current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conflict of Interest: Users cannot approve or reject their own leave requests."
        )

    # Scoping: Managers can only decide for employees within their assigned team
    emp = db.query(Employee).filter(Employee.employee_id == leave.employee_id).first()
    if current_user.role == ROLE_MANAGER:
        if not emp or emp.team_id != current_user.team_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Manager cannot decide leave requests for employee outside assigned team {current_user.team_id}."
            )

    leave.approval_status = request.decision
    leave.approver_id = current_user.employee_id
    leave.approval_timestamp = datetime.utcnow()
    if request.decision == "REJECTED":
        leave.rejection_reason = request.comments or "Operational staffing shortage"

    # Schedule Reconciliation: On Approval, vacate conflicting shift assignments
    conflicts_vacated = 0
    if request.decision == "APPROVED":
        conflicting_assignments = (
            db.query(ShiftAssignment)
            .join(Shift, ShiftAssignment.shift_id == Shift.shift_id)
            .filter(
                ShiftAssignment.employee_id == leave.employee_id,
                Shift.shift_date >= leave.start_date,
                Shift.shift_date <= leave.end_date
            )
            .all()
        )

        for asgn in conflicting_assignments:
            # 1. Nullify foreign key reference in attendance_events
            db.query(AttendanceEvent).filter(AttendanceEvent.assignment_id == asgn.assignment_id).update({"assignment_id": None})

            # 2. Delete or reject swap requests referencing this assignment
            db.query(SwapRequest).filter(
                (SwapRequest.original_assignment_id == asgn.assignment_id) |
                (SwapRequest.proposed_assignment_id == asgn.assignment_id)
            ).delete(synchronize_session=False)

            # 3. Record history audit
            hist_count = db.query(ShiftAssignmentHistory).count() + 1
            db.add(ShiftAssignmentHistory(
                history_id=f"SAH-{hist_count:06d}",
                assignment_id=asgn.assignment_id,
                previous_employee_id=asgn.employee_id,
                new_employee_id="UNASSIGNED",
                change_reason="LEAVE_APPROVED_VACATED",
                changed_by=current_user.employee_id
            ))

            # 4. Remove assignment so shift becomes open/unassigned
            db.delete(asgn)
            conflicts_vacated += 1

    # Add audit event
    evt_count = db.query(LeaveApprovalEvent).count() + 1
    db.add(LeaveApprovalEvent(
        event_id=f"LAE-{evt_count:06d}",
        leave_id=leave.leave_id,
        actor_id=current_user.employee_id,
        decision=request.decision,
        comments=request.comments
    ))

    db.add(AuditLog(
        log_id=IdGenerator.audit_log(datetime.utcnow(), evt_count),
        actor_id=current_user.employee_id,
        actor_role=current_user.role,
        action=f"LEAVE_{request.decision}",
        entity_type="LEAVE_REQUEST",
        entity_id=leave_id,
        details_json=f"Decision: {request.decision}, Vacated Shifts: {conflicts_vacated}, Comments: {request.comments}"
    ))

    db.commit()
    return {
        "success": True,
        "message": f"Leave request {request.decision.lower()} successfully" + (f" ({conflicts_vacated} conflicting shifts vacated)" if conflicts_vacated else ""),
        "leave_id": leave.leave_id,
        "status": leave.approval_status,
        "conflicts_vacated": conflicts_vacated
    }
