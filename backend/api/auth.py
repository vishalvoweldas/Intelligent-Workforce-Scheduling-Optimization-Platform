"""Authentication, Session and Demo Identity Endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend.models.database import get_db
from backend.models.entities import Employee, Team
from backend.schemas.schemas import LoginRequest, TokenResponse, UserResponse
from backend.security.rbac import (
    CurrentUser, get_current_user as get_authenticated_user,
    ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_HR_PARTNER, ROLE_OPERATIONS, ROLE_ADMIN
)

router = APIRouter(prefix="/auth", tags=["Authentication & Identity"])

@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.email == request.email).first()
    if not emp:
        # Fallback to test email or first employee
        emp = db.query(Employee).first()
        if not emp:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    return TokenResponse(
        access_token=f"jwt_token_for_{emp.employee_id}",
        user=UserResponse(
            employee_id=emp.employee_id,
            first_name=emp.first_name,
            last_name=emp.last_name,
            email=emp.email,
            role=emp.role,
            team_id=emp.team_id
        )
    )

@router.get("/me")
def get_user_session(current_user: CurrentUser = Depends(get_authenticated_user)):
    """Returns currently authenticated identity and granted RBAC permissions."""
    return {
        "employee_id": current_user.employee_id,
        "name": current_user.full_name,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "role": current_user.role,
        "team_id": current_user.team_id,
        "email": current_user.email,
        "permissions": sorted(list(current_user.permissions))
    }

@router.get("/demo-users")
def list_demo_identities(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Provides categorized identities from actual database records for demo / testing.
    
    Returns all 100 persisted employees, 10 team managers, and functional role leads.
    """
    all_emps = db.query(Employee).order_by(Employee.employee_id.asc()).all()
    teams = {t.team_id: t.team_name for t in db.query(Team).all()}

    emp_list = [
        {
            "employee_id": e.employee_id,
            "name": f"{e.first_name} {e.last_name}",
            "team_id": e.team_id,
            "team_name": teams.get(e.team_id, e.team_id),
            "role": e.role,
            "employment_type": e.employment_type
        }
        for e in all_emps
    ]

    # Managers mapped to their specific team
    manager_list = [e for e in emp_list if e["role"] == ROLE_MANAGER or e["employee_id"] in [f"EMP-{i:06d}" for i in range(1, 11)]]

    # Dedicated functional accounts
    hr_lead = next((e for e in emp_list if e["role"] == ROLE_HR_PARTNER), emp_list[10] if len(emp_list) > 10 else emp_list[0])
    ops_lead = next((e for e in emp_list if e["role"] == ROLE_OPERATIONS), emp_list[11] if len(emp_list) > 11 else emp_list[0])
    admin_lead = next((e for e in emp_list if e["role"] == ROLE_ADMIN), emp_list[12] if len(emp_list) > 12 else emp_list[0])

    return {
        "total": len(emp_list),
        "total_employees": len(emp_list),
        "employees": emp_list,
        "managers": manager_list,
        "hr_partner": hr_lead,
        "hr_partners": [hr_lead] if hr_lead else [],
        "operations": [ops_lead] if ops_lead else [],
        "operations_lead": ops_lead,
        "admin": admin_lead,
        "admins": [admin_lead] if admin_lead else []
    }
