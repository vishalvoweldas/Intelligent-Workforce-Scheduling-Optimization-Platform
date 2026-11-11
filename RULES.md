# Development Rules, Standards & Engineering Protocols
## Intelligent Workforce Scheduling & Optimization Platform

**Document Version:** 1.0.0  
**Status:** Mandatory Engineering Protocols  
**Enforcement:** Automated Linting, Type Checking, and CI/CD Audits  

---

## 1. General Principles & Non-Negotiables

1. **No Mock or Dummy Business Logic:**
   - Optimization, constraint validation, attendance reconciliation, and anomaly detection must execute genuine mathematical or algorithmic routines. No fake delays with hardcoded return values.
2. **Deterministic Reproducibility:**
   - Any synthetic generation or stochastic solver behavior must be keyed to a deterministic seed (`20261022` by default). Two runs with identical configuration must produce bit-for-bit identical datasets and results.
3. **Strict Ground-Truth Isolation:**
   - Ground-truth files (`ground_truth.csv`, `ground_truth.json`) must never be imported or read by the scheduling algorithm, constraint engine, or production API endpoints. They are exclusively accessible to the evaluation test harness.
4. **Zero Silent Constraint Violations:**
   - Hard labor constraints must never be bypassed to achieve 100% coverage or higher fairness. Uncovered shifts must be reported as explicit gaps with diagnostic reasons.
5. **Historical Immutability:**
   - Never mutate historical business events (e.g. past approved leaves, past clock-in events, previously executed schedule versions). Corrections are made via new compensating events with audit log traces.

---

## 2. Naming Conventions & Identifiers

### 2.1 Entity Identifiers (Deterministic & Prefixed)
All primary keys and entity identifiers must adhere to strict deterministic patterns:
- **Employee:** `EMP-XXXXXX` (e.g., `EMP-000001`, `EMP-000142`)
- **Team:** `TEAM-XXX` (e.g., `TEAM-001`, `TEAM-012`)
- **Skill:** `SKL-XXX` (e.g., `SKL-001`, `SKL-010`)
- **Shift Template:** `TMPL-XXX` (e.g., `TMPL-MORN`, `TMPL-AFTN`, `TMPL-NGHT`)
- **Shift Instance:** `SHIFT-YYYY-MM-DD-X` (e.g., `SHIFT-2026-01-01-A`)
- **Shift Assignment:** `ASGN-XXXXXX` (e.g., `ASGN-000001`)
- **Leave Request:** `LVE-YYYY-XXXXXX` (e.g., `LVE-2026-000001`)
- **Shift Swap:** `SWP-YYYY-XXXXXX` (e.g., `SWP-2026-000001`)
- **Attendance Event:** `ATT-<EMP_ID>-<YYYYMMDDHHMMSS>` (e.g., `ATT-EMP-000001-20260101080000`)
- **Coverage Requirement:** `COV-XXXXXX` (e.g., `COV-000001`)
- **Schedule Run:** `RUN-YYYY-XXXXXX` (e.g., `RUN-2026-000001`)
- **Anomaly Record:** `ANOM-XXXXXX` (e.g., `ANOM-000001`)

### 2.2 Code & File Conventions
- **Python Backend:**
  - Files & Modules: `snake_case.py` (e.g., `constraint_builder.py`, `attendance_service.py`)
  - Classes: `PascalCase` (e.g., `EmployeeRepository`, `OrToolsScheduleOptimizer`)
  - Functions & Variables: `snake_case` (e.g., `calculate_overtime_hours`, `team_id`)
  - Constants & Enums: `UPPER_SNAKE_CASE` (e.g., `MAX_WEEKLY_HOURS`, `ShiftCategory.NIGHT`)
- **TypeScript / React Frontend:**
  - Component Files: `PascalCase.tsx` (e.g., `ScheduleCalendar.tsx`, `LeaveRequestModal.tsx`)
  - Utility & Service Files: `camelCase.ts` (e.g., `apiClient.ts`, `dateUtils.ts`)
  - Interfaces & Types: `PascalCase` with descriptive nouns (e.g., `ShiftAssignment`, `EmployeeProfile`)
  - Hooks: `camelCase` starting with `use` (e.g., `useScheduleRoster`, `useAuthSession`)

---

## 3. Backend Development Rules (Python & FastAPI)

1. **Type Annotations Everywhere:**
   - Every function signature must have complete Python type hints (Python 3.13 syntax).
   - Use Pydantic v2 schemas for all incoming API request payloads and outgoing API responses.
2. **Layered Architecture:**
   - `api/`: Route handlers only. Validate input via Pydantic, check RBAC permissions, delegate to domain service, format HTTP response.
   - `services/`: Business logic, workflow transitions, coordination between repositories, solver calls.
   - `repositories/`: Direct database queries and mutations via SQLAlchemy. No raw string SQL unless necessary for bulk copy.
   - `scheduling/`: Mathematical constraint formulation and Google OR-Tools integration.
3. **Database Transactions:**
   - Operations that mutate multiple entities (such as approving a shift swap, publishing a schedule, or generating a batch) must execute inside an explicit atomic database transaction (`with session.begin():`).
4. **Error Handling & Standard Responses:**
   - Standardized error format:
     ```json
     {
       "error": {
         "code": "VALIDATION_FAILED",
         "message": "Employee EMP-000001 violates minimum 11-hour rest period rule.",
         "details": { "shift_id": "SHIFT-2026-01-02-A", "rest_hours": 7.5 }
       }
     }
     ```
   - Never leak raw Python tracebacks or internal database errors to HTTP clients.

---

## 4. Frontend Architecture & React Rules

1. **Component Modularity:**
   - Keep components focused and under 300 lines of code. Extract sub-components (e.g. `RosterCell`, `CoverageBar`, `AnomalyBadge`).
2. **No Undefined or Silent Failures:**
   - Handle loading, empty, and error states gracefully in every view.
   - Use notification toasts for user action feedback (e.g., "Shift Swap Approved", "Schedule Run Completed").
3. **Role-Based Rendering:**
   - Use role guards to show/hide actionable controls based on active user role (`EMPLOYEE`, `MANAGER`, `HR_PARTNER`, `OPERATIONS`, `ADMIN`), but always rely on backend validation as the authoritative security check.
4. **Time & Date Handling:**
   - All datetime strings exchanged with the backend must use ISO-8601 (`YYYY-MM-DDTHH:mm:ssZ`).
   - Use UTC consistently for comparison, and display localized formats in the user interface.

---

## 5. Testing & Verification Standards

1. **Test Coverage Thresholds:**
   - Minimum 85% unit test coverage on core scheduling, constraint checking, attendance reconciliation, and anomaly detection modules.
2. **Automated Testing Suite Structure:**
   - `tests/unit/`: Test individual functions (ID generation, overtime math, rest period calculations).
   - `tests/scheduling/`: Test CP-SAT solver against edge cases (leave conflicts, skill shortages, infeasible setups).
   - `tests/data_quality/`: Test dataset integrity, FK validation, fixed-seed reproducibility, and ground-truth separation.
   - `tests/integration/`: Test complete FastAPI endpoints with test database.
3. **Reproducibility Test:**
   - Continuous test asserting that running the synthetic data generator twice with seed `20261022` produces identical hashes and counts.

