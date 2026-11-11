"""Shift Templates, Dated Shifts, and Assignments Endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
from backend.models.database import get_db
from backend.models.entities import Shift, ShiftTemplate, ShiftAssignment, CoverageRequirement, Employee

router = APIRouter(prefix="/shifts", tags=["Shifts"])

@router.get("/templates")
def list_shift_templates(db: Session = Depends(get_db)):
    templates = db.query(ShiftTemplate).all()
    return [
        {
            "template_id": t.template_id,
            "template_name": t.template_name,
            "start_time": t.start_time,
            "end_time": t.end_time,
            "break_duration_hours": t.break_duration_hours,
            "category": t.category,
            "duration_hours": t.duration_hours,
            "is_overnight": t.is_overnight,
            "applicable_days": t.applicable_days
        }
        for t in templates
    ]

@router.get("")
def list_shifts(
    team_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(Shift)
    if team_id:
        query = query.filter(Shift.team_id == team_id)
    if start_date:
        query = query.filter(Shift.shift_date >= date.fromisoformat(start_date))
    if end_date:
        query = query.filter(Shift.shift_date <= date.fromisoformat(end_date))

    total = query.count()
    shifts = query.order_by(Shift.shift_date, Shift.start_datetime).offset(offset).limit(limit).all()

    # Pre-fetch assignments for these shifts
    shift_ids = [s.shift_id for s in shifts]
    assignments = db.query(ShiftAssignment).filter(ShiftAssignment.shift_id.in_(shift_ids)).all()
    asgn_map = {}
    for a in assignments:
        asgn_map.setdefault(a.shift_id, []).append({
            "assignment_id": a.assignment_id,
            "employee_id": a.employee_id,
            "employee_name": f"{a.employee.first_name} {a.employee.last_name}" if a.employee else a.employee_id,
            "status": a.assignment_status,
            "source": a.assignment_source
        })

    return {
        "total": total,
        "items": [
            {
                "shift_id": s.shift_id,
                "template_id": s.template_id,
                "team_id": s.team_id,
                "shift_date": s.shift_date.isoformat(),
                "start_datetime": s.start_datetime.isoformat(),
                "end_datetime": s.end_datetime.isoformat(),
                "status": s.status,
                "assignments": asgn_map.get(s.shift_id, [])
            }
            for s in shifts
        ]
    }

@router.get("/coverage-requirements")
def list_coverage_requirements(team_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(CoverageRequirement)
    if team_id:
        query = query.filter(CoverageRequirement.team_id == team_id)
    reqs = query.all()
    return [
        {
            "requirement_id": r.requirement_id,
            "team_id": r.team_id,
            "template_id": r.template_id,
            "skill_id": r.skill_id,
            "min_employees": r.min_employees
        }
        for r in reqs
    ]

