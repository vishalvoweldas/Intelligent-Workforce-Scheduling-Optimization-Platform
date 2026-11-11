"""Security & Authorization Package."""
from backend.security.rbac import (
    ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_HR_PARTNER, ROLE_OPERATIONS, ROLE_ADMIN,
    CANONICAL_ROLES, ROLE_PERMISSIONS, CurrentUser,
    get_current_user, require_role, require_permission,
    verify_ownership, verify_team_scope
)

