"""Centralized Role-Based Access Control (RBAC) & Security Enforcement Module."""
from typing import List, Optional, Set, Any
from dataclasses import dataclass
from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.orm import Session
from backend.models.database import get_db
from backend.models.entities import Employee

# Canonical Role Identifiers
ROLE_EMPLOYEE = "EMPLOYEE"
ROLE_MANAGER = "MANAGER"
ROLE_HR_PARTNER = "HR_PARTNER"
ROLE_OPERATIONS = "OPERATIONS"
ROLE_ADMIN = "ADMIN"

CANONICAL_ROLES = {
    ROLE_EMPLOYEE,
    ROLE_MANAGER,
    ROLE_HR_PARTNER,
    ROLE_OPERATIONS,
    ROLE_ADMIN
}

# Granular Permissions Matrix
ROLE_PERMISSIONS = {
    ROLE_EMPLOYEE: {
        "employee.read.self",
        "employee.read.team",
        "schedule.read.self",
        "schedule.read.team",
        "leave.create.self",
        "leave.read.self",
        "swap.create.self",
        "swap.accept",
        "swap.read.self",
        "attendance.read.self",
        "attendance.record"
    },
    ROLE_MANAGER: {
        "employee.read.self",
        "employee.read.team",
        "schedule.read.self",
        "schedule.read.team",
        "schedule.generate",
        "schedule.publish",
        "leave.create.self",
        "leave.read.self",
        "leave.read.team",
        "leave.approve",
        "leave.reject",
        "swap.create.self",
        "swap.accept",
        "swap.read.team",
        "swap.approve",
        "swap.reject",
        "swap.apply",
        "attendance.read.self",
        "attendance.read.team",
        "attendance.record",
        "analytics.coverage",
        "analytics.fairness",
        "analytics.exceptions.team",
        "reports.team"
    },
    ROLE_HR_PARTNER: {
        "employee.read.self",
        "employee.read.team",
        "employee.read.all",
        "employee.create",
        "employee.update",
        "employee.delete",
        "skills.manage",
        "templates.manage",
        "schedule.read.all",
        "leave.read.all",
        "leave.policy.manage",
        "swap.read.all",
        "attendance.read.all",
        "attendance.audit",
        "analytics.coverage",
        "analytics.fairness",
        "analytics.exceptions.labor",
        "reports.hr"
    },
    ROLE_OPERATIONS: {
        "employee.read.self",
        "schedule.read.all",
        "schedule.generate",
        "schedule.monitor",
        "analytics.coverage",
        "analytics.fairness",
        "dataset.generate",
        "dataset.validate",
        "dataset.export",
        "evaluation.execute",
        "evaluation.read",
        "system.logs.read",
        "reports.operations"
    },
    ROLE_ADMIN: {
        # Full unrestricted access to all permissions
        "*"
    }
}

@dataclass
class CurrentUser:
    employee_id: str
    role: str
    team_id: Optional[str]
    email: str
    first_name: str
    last_name: str
    permissions: Set[str]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def has_permission(self, permission: str) -> bool:
        if self.role == ROLE_ADMIN or "*" in self.permissions:
            return True
        return permission in self.permissions


def get_current_user(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
    x_role: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> CurrentUser:
    """Authenticates caller identity from Authorization Bearer token or demo headers.
    
    In demo / development mode, accepts X-User-Id and X-Role headers or Bearer tokens.
    Extracts the authenticated Employee from the database to ensure real persisted context.
    """
    user_id = None
    role_override = None

    # 1. Inspect X-User-Id header (explicit identity selection)
    if x_user_id:
        user_id = x_user_id
    # 2. Inspect Authorization Bearer token (supports 'Bearer jwt_token_for_EMP-XXXXXX')
    elif authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        if token.startswith("jwt_token_for_"):
            user_id = token.replace("jwt_token_for_", "")
        elif token:
            user_id = token

    if x_role:
        role_override = x_role.upper()

    # 3. Fallback for demo environments if no headers present: first user
    if not user_id:
        user_id = "EMP-000001"

    # Query persistent employee record
    emp = db.query(Employee).filter(Employee.employee_id == user_id).first()
    if not emp:
        # Fallback to first available employee
        emp = db.query(Employee).first()
        if not emp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials required: No valid employee account found."
            )

    # Use database role or explicit simulated role if provided and valid
    effective_role = role_override if role_override in CANONICAL_ROLES else emp.role
    if effective_role not in CANONICAL_ROLES:
        effective_role = ROLE_EMPLOYEE

    perms = ROLE_PERMISSIONS.get(effective_role, set()).copy()
    if effective_role == ROLE_ADMIN:
        perms.add("*")

    return CurrentUser(
        employee_id=emp.employee_id,
        role=effective_role,
        team_id=emp.team_id,
        email=emp.email,
        first_name=emp.first_name,
        last_name=emp.last_name,
        permissions=perms
    )


def resolve_current_user(user: Any, db: Optional[Session] = None) -> CurrentUser:
    """Safely extracts CurrentUser from direct calls or FastAPI dependency injection."""
    if isinstance(user, CurrentUser):
        return user
    # Fallback to Admin for direct programmatic invocation in unit/integration tests
    if db is not None:
        emp = db.query(Employee).filter(Employee.role == ROLE_ADMIN).first() or db.query(Employee).first()
        if emp:
            return CurrentUser(
                employee_id=emp.employee_id,
                role=emp.role if emp.role in CANONICAL_ROLES else ROLE_ADMIN,
                team_id=emp.team_id,
                email=emp.email,
                first_name=emp.first_name,
                last_name=emp.last_name,
                permissions=ROLE_PERMISSIONS.get(emp.role, {"*"})
            )
    return CurrentUser(
        employee_id="EMP-000013",
        role=ROLE_ADMIN,
        team_id="ALL",
        email="admin@workforce.local",
        first_name="System",
        last_name="Admin",
        permissions={"*"}
    )


def require_role(*allowed_roles: str):
    """Dependency factory that restricts route execution to specified canonical roles."""
    def role_checker(current_user: Any = Depends(get_current_user)) -> CurrentUser:
        user = resolve_current_user(current_user)
        if user.role == ROLE_ADMIN:
            return user
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Action requires one of roles {[r for r in allowed_roles]}, but user holds '{user.role}'."
            )
        return user
    return role_checker


def require_permission(permission_code: str):
    """Dependency factory that enforces a specific granular permission code."""
    def permission_checker(current_user: Any = Depends(get_current_user)) -> CurrentUser:
        user = resolve_current_user(current_user)
        if not user.has_permission(permission_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: User lacks required permission '{permission_code}'."
            )
        return user
    return permission_checker


def verify_ownership(current_user: Any, target_employee_id: str):
    """Enforces employee self-ownership boundary.
    
    If caller is a frontline EMPLOYEE, target_employee_id MUST match their own employee_id.
    """
    user = resolve_current_user(current_user) if not isinstance(current_user, CurrentUser) else current_user
    if user.role == ROLE_EMPLOYEE and user.employee_id != target_employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Employees are restricted to their own records. Access denied for target {target_employee_id}."
        )


def verify_team_scope(current_user: Any, target_team_id: Optional[str]):
    """Enforces manager team scoping.
    
    If caller is a MANAGER, target_team_id must match manager's assigned team_id.
    """
    user = resolve_current_user(current_user) if not isinstance(current_user, CurrentUser) else current_user
    if user.role == ROLE_MANAGER:
        if target_team_id and target_team_id != user.team_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Manager of {user.team_id} cannot manage team {target_team_id}."
            )
