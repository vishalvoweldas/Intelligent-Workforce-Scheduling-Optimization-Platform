"""Shift Swap Workflow & Atomic Execution Endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
from backend.models.database import get_db
from backend.models.entities import (
    SwapRequest, SwapApprovalEvent, ShiftAssignment, ShiftAssignmentHistory,
    Shift, Employee, AuditLog, EmployeeSkill, CoverageRequirement
)
from backend.schemas.schemas import SwapSubmitRequest, SwapDecisionRequest, SwapPeerDecisionRequest
from backend.services.id_generator import IdGenerator
from backend.security.rbac import (
    get_current_user, CurrentUser, verify_ownership, resolve_current_user,
    ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_ADMIN, ROLE_HR_PARTNER
)

router = APIRouter(prefix="/swaps", tags=["Shift Swaps"])

@router.get("")
def list_swap_requests(
    employee_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user = resolve_current_user(current_user, db)
    query = db.query(SwapRequest)

    # Scoping by Role
    if current_user.role == ROLE_EMPLOYEE:
        # Frontline employees can only see swaps they are directly involved in
        query = query.filter(
            (SwapRequest.requesting_employee_id == current_user.employee_id) |
            (SwapRequest.receiving_employee_id == current_user.employee_id)
        )
    elif current_user.role == ROLE_MANAGER:
        # Managers can see swaps for employees in their team
        team_emp_ids = [e.employee_id for e in db.query(Employee).filter(Employee.team_id == current_user.team_id).all()]
        query = query.filter(
            (SwapRequest.requesting_employee_id.in_(team_emp_ids)) |
            (SwapRequest.receiving_employee_id.in_(team_emp_ids))
        )
    else:
        # HR, Operations, Admin
        if employee_id:
            query = query.filter(
                (SwapRequest.requesting_employee_id == employee_id) |
                (SwapRequest.receiving_employee_id == employee_id)
            )

    if status_filter:
        query = query.filter(SwapRequest.status == status_filter)

    swaps = query.order_by(SwapRequest.request_timestamp.desc()).limit(limit).all()

    # Pre-fetch employees and shift details for enriched response
    emp_map = {e.employee_id: f"{e.first_name} {e.last_name}" for e in db.query(Employee).all()}
    asgn_map = {a.assignment_id: a for a in db.query(ShiftAssignment).all()}
    shift_map = {s.shift_id: s for s in db.query(Shift).all()}

    results = []
    for sw in swaps:
        orig_asgn = asgn_map.get(sw.original_assignment_id)
        prop_asgn = asgn_map.get(sw.proposed_assignment_id)
        orig_shift = shift_map.get(orig_asgn.shift_id) if orig_asgn else None
        prop_shift = shift_map.get(prop_asgn.shift_id) if prop_asgn else None

        results.append({
            "swap_id": sw.swap_id,
            "requesting_employee_id": sw.requesting_employee_id,
            "requesting_employee_name": emp_map.get(sw.requesting_employee_id, sw.requesting_employee_id),
            "receiving_employee_id": sw.receiving_employee_id,
            "receiving_employee_name": emp_map.get(sw.receiving_employee_id, sw.receiving_employee_id),
            "original_assignment_id": sw.original_assignment_id,
            "original_shift_info": f"{orig_shift.shift_date} ({orig_shift.template_id})" if orig_shift else None,
            "proposed_assignment_id": sw.proposed_assignment_id,
            "proposed_shift_info": f"{prop_shift.shift_date} ({prop_shift.template_id})" if prop_shift else None,
            "request_timestamp": sw.request_timestamp.isoformat(),
            "status": sw.status,
            "manager_approver_id": sw.manager_approver_id,
            "rejection_reason": sw.rejection_reason
        })

    return results

@router.post("")
def create_swap_request(
    request: SwapSubmitRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user = resolve_current_user(current_user, db)
    # Enforce ownership: Caller must be the requesting employee (or admin/manager initiating on behalf)
    verify_ownership(current_user, request.requesting_employee_id)

    if request.requesting_employee_id == request.receiving_employee_id:
        raise HTTPException(status_code=400, detail="Cannot swap shift with yourself")

    # Validate assignments exist
    asgn_orig = db.query(ShiftAssignment).filter(ShiftAssignment.assignment_id == request.original_assignment_id).first()
    asgn_prop = db.query(ShiftAssignment).filter(ShiftAssignment.assignment_id == request.proposed_assignment_id).first()

    if not asgn_orig or not asgn_prop:
        raise HTTPException(status_code=404, detail="One or both shift assignments not found")

    if asgn_orig.employee_id != request.requesting_employee_id:
        raise HTTPException(status_code=400, detail="Original shift assignment does not belong to the requesting employee")

    if asgn_prop.employee_id != request.receiving_employee_id:
        raise HTTPException(status_code=400, detail="Proposed shift assignment does not belong to the receiving employee")

    # Validate skill eligibility (BR-05)
    # Check original shift required skills against receiving employee
    orig_shift = db.query(Shift).filter(Shift.shift_id == asgn_orig.shift_id).first()
    prop_shift = db.query(Shift).filter(Shift.shift_id == asgn_prop.shift_id).first()

    rec_skills = {es.skill_id for es in db.query(EmployeeSkill).filter(EmployeeSkill.employee_id == request.receiving_employee_id).all()}
    req_skills = {es.skill_id for es in db.query(EmployeeSkill).filter(EmployeeSkill.employee_id == request.requesting_employee_id).all()}

    # Check coverage requirements for original and proposed shifts
    if orig_shift:
        orig_reqs = db.query(CoverageRequirement).filter(
            CoverageRequirement.team_id == orig_shift.team_id,
            CoverageRequirement.template_id == orig_shift.template_id
        ).all()
        for r in orig_reqs:
            if r.skill_id not in rec_skills:
                raise HTTPException(
                    status_code=400,
                    detail=f"Receiving employee lacks required skill '{r.skill_id}' for original shift {orig_shift.shift_id}."
                )

    if prop_shift:
        prop_reqs = db.query(CoverageRequirement).filter(
            CoverageRequirement.team_id == prop_shift.team_id,
            CoverageRequirement.template_id == prop_shift.template_id
        ).all()
        for r in prop_reqs:
            if r.skill_id not in req_skills:
                raise HTTPException(
                    status_code=400,
                    detail=f"Requesting employee lacks required skill '{r.skill_id}' for proposed shift {prop_shift.shift_id}."
                )

    # Monotonic ID generation
    existing_swaps = db.query(SwapRequest.swap_id).all()
    max_idx = 0
    year = datetime.utcnow().year
    for (sid,) in existing_swaps:
        parts = sid.split("-")
        if len(parts) >= 3 and parts[-1].isdigit():
            max_idx = max(max_idx, int(parts[-1]))
    swap_id = IdGenerator.swap(year, max_idx + 1)

    # Lifecycle Stage 1: PENDING_PEER_ACCEPTANCE
    swap = SwapRequest(
        swap_id=swap_id,
        requesting_employee_id=request.requesting_employee_id,
        receiving_employee_id=request.receiving_employee_id,
        original_assignment_id=request.original_assignment_id,
        proposed_assignment_id=request.proposed_assignment_id,
        status="PENDING_PEER_ACCEPTANCE",
        request_timestamp=datetime.utcnow()
    )
    db.add(swap)

    db.add(AuditLog(
        log_id=IdGenerator.audit_log(datetime.utcnow(), max_idx + 1),
        actor_id=current_user.employee_id,
        actor_role=current_user.role,
        action="INITIATE_SHIFT_SWAP",
        entity_type="SWAP_REQUEST",
        entity_id=swap_id,
        details_json=f"Swap {request.original_assignment_id} with {request.proposed_assignment_id}. Reason: {request.reason or 'None'}"
    ))

    db.commit()
    db.refresh(swap)
    return {
        "success": True,
        "message": "Shift swap proposed successfully. Awaiting peer acceptance.",
        "swap_id": swap.swap_id,
        "status": swap.status
    }

@router.post("/{swap_id}/peer-decide")
def peer_decide_swap(
    swap_id: str,
    request: SwapPeerDecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Peer acceptance stage: The receiving employee accepts or rejects the proposed swap."""
    current_user = resolve_current_user(current_user, db)
    swap = db.query(SwapRequest).filter(SwapRequest.swap_id == swap_id).first()
    if not swap:
        raise HTTPException(status_code=404, detail="Swap request not found")

    if swap.status not in ("PENDING_PEER_ACCEPTANCE", "REQUESTED"):
        raise HTTPException(status_code=400, detail=f"Cannot respond: Swap is in '{swap.status}' state.")

    # Only receiving employee (or Admin) can accept the peer swap
    if current_user.role != ROLE_ADMIN and current_user.employee_id != swap.receiving_employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only the receiving employee can accept or decline this swap proposal."
        )

    decision = request.decision.upper()
    if decision not in ("ACCEPTED", "REJECTED"):
        raise HTTPException(status_code=400, detail="Decision must be ACCEPTED or REJECTED")

    if decision == "ACCEPTED":
        # Progresses to manager approval stage
        swap.status = "PENDING_MANAGER_APPROVAL"
        msg = "Swap proposal accepted by peer. Awaiting manager approval."
    else:
        swap.status = "REJECTED"
        swap.rejection_reason = request.comments or "Declined by peer employee"
        msg = "Swap proposal declined by peer."

    evt_count = db.query(SwapApprovalEvent).count() + 1
    db.add(SwapApprovalEvent(
        event_id=f"SAE-{evt_count:06d}",
        swap_id=swap.swap_id,
        actor_id=current_user.employee_id,
        decision=f"PEER_{decision}",
        rejection_reason=request.comments
    ))

    db.add(AuditLog(
        log_id=IdGenerator.audit_log(datetime.utcnow(), evt_count),
        actor_id=current_user.employee_id,
        actor_role=current_user.role,
        action=f"SWAP_PEER_{decision}",
        entity_type="SWAP_REQUEST",
        entity_id=swap_id,
        details_json=f"Peer response: {decision}. Comments: {request.comments or ''}"
    ))

    db.commit()
    return {
        "success": True,
        "message": msg,
        "swap_id": swap.swap_id,
        "status": swap.status
    }

@router.post("/{swap_id}/accept")
def peer_accept_swap(
    swap_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Convenience endpoint for peer acceptance."""
    return peer_decide_swap(swap_id, SwapPeerDecisionRequest(decision="ACCEPTED"), current_user, db)

@router.post("/{swap_id}/decide")
def decide_swap_request(
    swap_id: str,
    request: SwapDecisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manager approval & atomic application stage."""
    current_user = resolve_current_user(current_user, db)
    # Role Authorization: Managers and Admins only
    if current_user.role not in (ROLE_MANAGER, ROLE_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only Managers or Administrators can approve shift swaps."
        )

    swap = db.query(SwapRequest).filter(SwapRequest.swap_id == swap_id).first()
    if not swap:
        raise HTTPException(status_code=404, detail="Swap request not found")

    if request.decision not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=400, detail="Decision must be APPROVED or REJECTED")

    # Anti-Corruption: Managers cannot approve swaps where they are requester or receiver
    if current_user.employee_id in (swap.requesting_employee_id, swap.receiving_employee_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conflict of Interest: Managers cannot approve or reject their own shift swaps."
        )

    # Scoping: If manager, ensure at least one participant belongs to manager's team
    if current_user.role == ROLE_MANAGER:
        req_emp = db.query(Employee).filter(Employee.employee_id == swap.requesting_employee_id).first()
        rec_emp = db.query(Employee).filter(Employee.employee_id == swap.receiving_employee_id).first()
        if (not req_emp or req_emp.team_id != current_user.team_id) and (not rec_emp or rec_emp.team_id != current_user.team_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Manager cannot approve swaps between employees outside team {current_user.team_id}."
            )

    approver_id = current_user.employee_id

    if request.decision == "APPROVED":
        # ATOMIC EXECUTION: Swap employee assignments
        asgn_orig = db.query(ShiftAssignment).filter(ShiftAssignment.assignment_id == swap.original_assignment_id).first()
        asgn_prop = db.query(ShiftAssignment).filter(ShiftAssignment.assignment_id == swap.proposed_assignment_id).first()

        if not asgn_orig or not asgn_prop:
            raise HTTPException(status_code=400, detail="Cannot apply swap: assignments no longer exist")

        emp_a = asgn_orig.employee_id
        emp_b = asgn_prop.employee_id

        # Swap employees atomically
        asgn_orig.employee_id = emp_b
        asgn_orig.assignment_source = "SWAP"
        asgn_prop.employee_id = emp_a
        asgn_prop.assignment_source = "SWAP"

        # Record assignment histories
        hist_count = db.query(ShiftAssignmentHistory).count() + 1
        db.add(ShiftAssignmentHistory(
            history_id=f"SAH-{hist_count:06d}",
            assignment_id=asgn_orig.assignment_id,
            previous_employee_id=emp_a,
            new_employee_id=emp_b,
            change_reason="SWAP_APPROVED",
            changed_by=approver_id
        ))
        db.add(ShiftAssignmentHistory(
            history_id=f"SAH-{hist_count + 1:06d}",
            assignment_id=asgn_prop.assignment_id,
            previous_employee_id=emp_b,
            new_employee_id=emp_a,
            change_reason="SWAP_APPROVED",
            changed_by=approver_id
        ))

        swap.status = "APPLIED"
        swap.manager_approver_id = approver_id
        swap.approval_timestamp = datetime.utcnow()
    else:
        swap.status = "REJECTED"
        swap.manager_approver_id = approver_id
        swap.approval_timestamp = datetime.utcnow()
        swap.rejection_reason = request.rejection_reason or "Staffing policy violation"

    # Add approval event
    evt_count = db.query(SwapApprovalEvent).count() + 1
    db.add(SwapApprovalEvent(
        event_id=f"SAE-{evt_count:06d}",
        swap_id=swap.swap_id,
        actor_id=approver_id,
        decision=request.decision,
        rejection_reason=request.rejection_reason
    ))

    db.add(AuditLog(
        log_id=IdGenerator.audit_log(datetime.utcnow(), evt_count),
        actor_id=approver_id,
        actor_role=current_user.role,
        action=f"SWAP_{request.decision}",
        entity_type="SWAP_REQUEST",
        entity_id=swap_id,
        details_json=f"Decision: {request.decision}, Rejection Reason: {request.rejection_reason}"
    ))

    db.commit()
    return {
        "success": True,
        "message": f"Swap request {request.decision.lower()} and applied atomically",
        "swap_id": swap.swap_id,
        "status": swap.status
    }
