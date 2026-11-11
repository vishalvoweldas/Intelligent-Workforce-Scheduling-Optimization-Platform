"""Workforce Directory: Employees, Teams, and Skills with RBAC Scope Enforcement."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List
from backend.models.database import get_db
from backend.models.entities import Employee, Team, Skill, EmployeeSkill
from backend.security.rbac import (
    CurrentUser, get_current_user, require_role,
    verify_ownership, verify_team_scope, resolve_current_user,
    ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_HR_PARTNER, ROLE_OPERATIONS, ROLE_ADMIN
)

router = APIRouter(prefix="/workforce", tags=["Workforce Directory"])

@router.get("/employees")
def list_employees(
    team_id: Optional[str] = None,
    role: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists employees with role-aware scoping and search.
    
    - EMPLOYEE: Can view members within own team or search directory.
    - MANAGER: Restricted to managed team unless searching for swap peers.
    - HR_PARTNER & ADMIN: Full organization directory.
    """
    current_user = resolve_current_user(current_user, db)
    query = db.query(Employee)

    # Scoping by role
    if current_user.role == ROLE_MANAGER and not current_user.has_permission("employee.read.all"):
        if team_id:
            verify_team_scope(current_user, team_id)
            query = query.filter(Employee.team_id == team_id)
        else:
            # Default to manager's managed team
            query = query.filter(Employee.team_id == current_user.team_id)
    elif team_id:
        query = query.filter(Employee.team_id == team_id)

    if role:
        query = query.filter(Employee.role == role)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            (Employee.employee_id.ilike(search_pattern)) |
            (Employee.first_name.ilike(search_pattern)) |
            (Employee.last_name.ilike(search_pattern)) |
            (Employee.email.ilike(search_pattern))
        )

    total = query.count()
    employees = query.offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "employee_id": e.employee_id,
                "first_name": e.first_name,
                "last_name": e.last_name,
                "name": f"{e.first_name} {e.last_name}",
                "email": e.email,
                "team_id": e.team_id,
                "role": e.role,
                "employment_type": e.employment_type,
                "employment_status": e.employment_status,
                "contracted_weekly_hours": e.contracted_weekly_hours,
                "max_working_hours": e.max_working_hours,
                "overtime_cap_hours": e.overtime_cap_hours,
                "work_zone": e.work_zone,
                "is_active": e.is_active
            }
            for e in employees
        ]
    }

@router.get("/employees/{employee_id}")
def get_employee_profile(
    employee_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches employee profile with confidentiality boundaries."""
    current_user = resolve_current_user(current_user, db)
    # Frontline employees can only access their own full confidential profile
    if current_user.role == ROLE_EMPLOYEE and current_user.employee_id != employee_id:
        # Check if same team
        target = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not target or target.team_id != current_user.team_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Cannot access confidential profile of employee {employee_id}."
            )

    emp = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    return {
        "employee_id": emp.employee_id,
        "first_name": emp.first_name,
        "last_name": emp.last_name,
        "name": f"{emp.first_name} {emp.last_name}",
        "email": emp.email,
        "team_id": emp.team_id,
        "role": emp.role,
        "employment_type": emp.employment_type,
        "employment_status": emp.employment_status,
        "contracted_weekly_hours": emp.contracted_weekly_hours,
        "max_working_hours": emp.max_working_hours,
        "overtime_cap_hours": emp.overtime_cap_hours,
        "work_zone": emp.work_zone,
        "is_active": emp.is_active
    }

@router.get("/teams")
def list_teams(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    teams = db.query(Team).filter(Team.team_id != "ALL").all()
    return [
        {
            "team_id": t.team_id,
            "team_name": t.team_name,
            "department": t.department,
            "location": t.location,
            "manager_id": t.manager_id,
            "is_active": t.is_active
        }
        for t in teams
    ]

@router.get("/skills")
def list_skills(db: Session = Depends(get_db)):
    skills = db.query(Skill).all()
    return [
        {
            "skill_id": s.skill_id,
            "skill_name": s.skill_name,
            "category": s.category,
            "description": s.description,
            "is_active": s.is_active
        }
        for s in skills
    ]

@router.get("/employees/{employee_id}/skills")
def get_employee_skills(
    employee_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    emp_skills = db.query(EmployeeSkill).filter(EmployeeSkill.employee_id == employee_id).all()
    return [
        {
            "id": es.id,
            "skill_id": es.skill_id,
            "skill_name": es.skill.skill_name if es.skill else "",
            "proficiency_level": es.proficiency_level,
            "is_certified": es.is_certified,
            "certification_expiry_date": es.certification_expiry_date.isoformat() if es.certification_expiry_date else None
        }
        for es in emp_skills
    ]
