# Database Architecture & Complete Data Dictionary
## Intelligent Workforce Scheduling & Optimization Platform

**Document Version:** 1.0.0  
**Storage Engine:** SQLite 3 (WAL mode) / PostgreSQL Compatible  
**ORM:** SQLAlchemy 2.0 (Async/Sync Declarative)  

---

## 1. Relational Integrity & Global Rules

1. **Foreign Key Enforcement:** Foreign key constraints are strictly enabled (`PRAGMA foreign_keys = ON;` in SQLite). Child records cannot exist without corresponding parent rows.
2. **Deterministic Identifiers:** Primary keys are immutable string identifiers with standardized prefixes (`EMP-XXXXXX`, `TEAM-XXX`, `SHIFT-YYYY-MM-DD-X`, `LVE-YYYY-XXXXXX`, `SWP-YYYY-XXXXXX`, `ATT-EMP-TIMESTAMP`).
3. **Audit Immutability:** Historical event tables (`audit_logs`, `leave_approval_events`, `swap_approval_events`, `shift_assignment_history`) are append-only.
4. **Timezone Standardization:** All timestamps are stored in UTC ISO-8601 (`YYYY-MM-DDTHH:MM:SS.sssZ`).

---

## 2. Core Entities Data Dictionary

### 2.1 `employees`
Stores master employee workforce profiles.
- `employee_id` (VARCHAR(32), PK): Deterministic ID `EMP-XXXXXX`. Unique, Not Null.
- `team_id` (VARCHAR(32), FK -> `teams.team_id`): Required.
- `first_name` (VARCHAR(64)): Required.
- `last_name` (VARCHAR(64)): Required.
- `email` (VARCHAR(128)): Unique, Valid email format. Not Null.
- `password_hash` (VARCHAR(256)): Bcrypt hash. Not Null.
- `role` (VARCHAR(32)): Enum `['EMPLOYEE', 'MANAGER', 'HR_PARTNER', 'OPERATIONS', 'ADMIN']`. Not Null.
- `employment_type` (VARCHAR(32)): Enum `['FULL_TIME', 'PART_TIME', 'CONTRACTOR']`. Not Null.
- `employment_status` (VARCHAR(32)): Enum `['ACTIVE', 'ON_LEAVE', 'TERMINATED']`. Default `'ACTIVE'`.
- `hire_date` (DATE): Format `YYYY-MM-DD`. Not Null.
- `work_zone` (VARCHAR(64)): Location/region (e.g., `'ZONE-A'`, `'HEADQUARTERS'`).
- `contracted_weekly_hours` (FLOAT): Non-negative (e.g. 40.0 for full-time, 20.0 for part-time).
- `max_working_hours` (FLOAT): Maximum legal weekly hours limit (e.g., 48.0).
- `overtime_cap_hours` (FLOAT): Maximum allowed weekly overtime (e.g., 8.0).
- `is_active` (BOOLEAN): Default True.
- `created_at` (DATETIME): UTC timestamp.
- `updated_at` (DATETIME): UTC timestamp.

### 2.2 `teams`
Organizational departments and operational groupings.
- `team_id` (VARCHAR(32), PK): Deterministic ID `TEAM-XXX`. Unique, Not Null.
- `team_name` (VARCHAR(128)): Unique, Not Null.
- `department` (VARCHAR(128)): Department name (e.g., `'Emergency Services'`, `'Logistics'`).
- `location` (VARCHAR(128)): Site location or city.
- `manager_id` (VARCHAR(32), FK -> `employees.employee_id`, Optional).
- `is_active` (BOOLEAN): Default True.
- `created_at` (DATETIME): UTC timestamp.

### 2.3 `skills`
Catalog of operational and technical skills.
- `skill_id` (VARCHAR(32), PK): Deterministic ID `SKL-XXX`. Unique, Not Null.
- `skill_name` (VARCHAR(128)): Unique, Not Null.
- `category` (VARCHAR(64)): Category (e.g., `'CLINICAL'`, `'HEAVY_MACHINERY'`, `'SUPPORT'`).
- `description` (TEXT): Description.
- `is_active` (BOOLEAN): Default True.

### 2.4 `employee_skills`
Many-to-many mapping between employees and skills with proficiency & certification.
- `id` (VARCHAR(64), PK): ID `ESK-XXXXXX`.
- `employee_id` (VARCHAR(32), FK -> `employees.employee_id`): Not Null.
- `skill_id` (VARCHAR(32), FK -> `skills.skill_id`): Not Null.
- `proficiency_level` (VARCHAR(32)): Enum `['BEGINNER', 'INTERMEDIATE', 'EXPERT']`.
- `is_certified` (BOOLEAN): True if certified.
- `certification_expiry_date` (DATE, Optional): Expiration date.
- `effective_start_date` (DATE): Start date.
- `effective_end_date` (DATE, Optional): End date.
- **Constraint:** Unique(`employee_id`, `skill_id`).

### 2.5 `shift_templates`
Standard shift archetypes.
- `template_id` (VARCHAR(32), PK): Deterministic ID `TMPL-XXX`.
- `template_name` (VARCHAR(64)): (e.g., `'Morning Shift'`, `'Night Shift'`).
- `start_time` (VARCHAR(8)): Format `HH:MM` (e.g., `'08:00'`).
- `end_time` (VARCHAR(8)): Format `HH:MM` (e.g., `'16:30'`).
- `break_duration_hours` (FLOAT): Unpaid break time in hours (e.g., 0.5 for 30m).
- `category` (VARCHAR(32)): Enum `['MORNING', 'AFTERNOON', 'NIGHT', 'WEEKEND']`.
- `duration_hours` (FLOAT): Total elapsed hours minus break.
- `is_overnight` (BOOLEAN): True if shift crosses midnight.
- `applicable_days` (VARCHAR(64)): Comma-separated days (e.g. `'MON,TUE,WED,THU,FRI'`).
- `is_active` (BOOLEAN): Default True.

### 2.6 `shifts`
Dated instances of shift templates.
- `shift_id` (VARCHAR(64), PK): Format `SHIFT-YYYY-MM-DD-X`. Unique.
- `template_id` (VARCHAR(32), FK -> `shift_templates.template_id`): Not Null.
- `team_id` (VARCHAR(32), FK -> `teams.team_id`): Not Null.
- `shift_date` (DATE): Date of shift start.
- `start_datetime` (DATETIME): Exact UTC timestamp of shift start.
- `end_datetime` (DATETIME): Exact UTC timestamp of shift end (accounting for overnight).
- `timezone` (VARCHAR(32)): Default `'UTC'`.
- `status` (VARCHAR(32)): Enum `['PLANNED', 'SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']`.

### 2.7 `shift_assignments`
Allocation of an employee to a shift.
- `assignment_id` (VARCHAR(64), PK): ID `ASGN-XXXXXX`. Unique.
- `shift_id` (VARCHAR(64), FK -> `shifts.shift_id`): Not Null.
- `employee_id` (VARCHAR(32), FK -> `employees.employee_id`): Not Null.
- `assignment_status` (VARCHAR(32)): Enum `['ASSIGNED', 'CONFIRMED', 'SWAPPED', 'CANCELLED']`.
- `assignment_source` (VARCHAR(32)): Enum `['OPTIMIZER', 'MANUAL', 'SWAP']`.
- `schedule_run_id` (VARCHAR(64), FK -> `schedule_runs.run_id`, Optional).
- `assigned_at` (DATETIME): UTC timestamp.

### 2.8 `leave_requests`
Employee leave and time-off bookings.
- `leave_id` (VARCHAR(64), PK): ID `LVE-YYYY-XXXXXX`. Unique.
- `employee_id` (VARCHAR(32), FK -> `employees.employee_id`): Not Null.
- `leave_type` (VARCHAR(32)): Enum `['ANNUAL', 'SICK', 'UNPAID', 'PARENTAL']`.
- `start_date` (DATE): Start date inclusive.
- `end_date` (DATE): End date inclusive.
- `request_date` (DATETIME): Timestamp when request was submitted.
- `approval_status` (VARCHAR(32)): Enum `['SUBMITTED', 'PENDING', 'APPROVED', 'REJECTED', 'CANCELLED']`.
- `approver_id` (VARCHAR(32), FK -> `employees.employee_id`, Optional).
- `approval_timestamp` (DATETIME, Optional).
- `rejection_reason` (TEXT, Optional).

### 2.9 `coverage_requirements`
Minimum headcount and skill requirements per team and shift.
- `requirement_id` (VARCHAR(64), PK): ID `COV-XXXXXX`.
- `team_id` (VARCHAR(32), FK -> `teams.team_id`): Not Null.
- `template_id` (VARCHAR(32), FK -> `shift_templates.template_id`): Not Null.
- `skill_id` (VARCHAR(32), FK -> `skills.skill_id`): Not Null.
- `min_employees` (INTEGER): Minimum count required (>= 1).
- `effective_start_date` (DATE): Start date.
- `effective_end_date` (DATE, Optional): End date.

### 2.10 `swap_requests`
Shift swap requests between employees.
- `swap_id` (VARCHAR(64), PK): ID `SWP-YYYY-XXXXXX`. Unique.
- `requesting_employee_id` (VARCHAR(32), FK -> `employees.employee_id`): Not Null.
- `receiving_employee_id` (VARCHAR(32), FK -> `employees.employee_id`): Not Null.
- `original_assignment_id` (VARCHAR(64), FK -> `shift_assignments.assignment_id`): Not Null.
- `proposed_assignment_id` (VARCHAR(64), FK -> `shift_assignments.assignment_id`): Not Null.
- `request_timestamp` (DATETIME): UTC timestamp.
- `status` (VARCHAR(32)): Enum `['REQUESTED', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'CANCELLED', 'APPLIED']`.
- `manager_approver_id` (VARCHAR(32), FK -> `employees.employee_id`, Optional).
- `approval_timestamp` (DATETIME, Optional).
- `rejection_reason` (TEXT, Optional).

### 2.11 `attendance_events`
Clock-in/out attendance logs.
- `attendance_id` (VARCHAR(64), PK): ID `ATT-<employee_id>-<timestamp>`.
- `employee_id` (VARCHAR(32), FK -> `employees.employee_id`): Not Null.
- `assignment_id` (VARCHAR(64), FK -> `shift_assignments.assignment_id`, Optional).
- `event_type` (VARCHAR(32)): Enum `['CLOCK_IN', 'CLOCK_OUT']`.
- `event_timestamp` (DATETIME): UTC timestamp.
- `source` (VARCHAR(32)): Enum `['BIOMETRIC', 'WEB', 'MOBILE', 'MANUAL']`.
- `status` (VARCHAR(32)): Enum `['ON_TIME', 'LATE', 'EARLY_DEPARTURE', 'MISSED']`.

---

## 3. Supporting & Audit Tables

- `schedule_runs`: Stores solver execution metadata (`run_id`, `team_id`, `start_date`, `end_date`, `solver_status`, `objective_value`, `runtime_seconds`, `shifts_assigned`, `gaps_count`, `weights_json`, `created_at`).
- `schedule_gaps`: Stores uncovered shifts and root cause explanations (`gap_id`, `run_id`, `shift_id`, `skill_id`, `shortage_count`, `reason`).
- `audit_logs`: Immutable audit trail (`log_id`, `actor_id`, `actor_role`, `action`, `entity_type`, `entity_id`, `details_json`, `ip_address`, `timestamp`).
- `leave_approval_events`: Immutable log of leave decisions (`event_id`, `leave_id`, `actor_id`, `decision`, `comments`, `timestamp`).
- `swap_approval_events`: Immutable log of swap decisions (`event_id`, `swap_id`, `actor_id`, `decision`, `rejection_reason`, `timestamp`).
- `shift_assignment_history`: Lifecycle history of assignments (`history_id`, `assignment_id`, `previous_employee_id`, `new_employee_id`, `reason`, `timestamp`).
- `dataset_runs`: Metadata on synthetic data generation (`run_id`, `profile`, `seed`, `row_counts_json`, `checksum`, `created_at`).
- `anomaly_records`: Track of deliberately injected or detected anomalies (`anomaly_id`, `issue_type`, `entity_type`, `record_id`, `severity`, `description`, `injection_method`, `detected_at`).
- `evaluation_runs`: Results of benchmark evaluations (`eval_id`, `dataset_run_id`, `confusion_matrix_json`, `precision`, `recall`, `f1_score`, `metrics_by_category_json`, `created_at`).

---

## 4. Database Indexes for High-Performance Queries

```sql
CREATE INDEX idx_emp_team ON employees(team_id);
CREATE INDEX idx_emp_email ON employees(email);
CREATE INDEX idx_shift_team_date ON shifts(team_id, shift_date);
CREATE INDEX idx_asgn_shift ON shift_assignments(shift_id);
CREATE INDEX idx_asgn_emp ON shift_assignments(employee_id);
CREATE INDEX idx_leave_emp_dates ON leave_requests(employee_id, start_date, end_date);
CREATE INDEX idx_att_emp_time ON attendance_events(employee_id, event_timestamp);
CREATE INDEX idx_audit_time ON audit_logs(timestamp);
CREATE INDEX idx_cov_team ON coverage_requirements(team_id);
```

---

## 5. Multi-Database Profile Architecture (Zero-Leakage Isolation)

To support rapid switching between development and full-scale enterprise simulation without destructive data overwriting, the platform operates dual isolated database files managed by `backend/models/profile_manager.py`:

| Database File | Profile | Employees | Teams | Horizon | Shifts | Leaves | Attendance | Purpose |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `workforce_starter.db` | `STARTER` | 100 | 10 | 14 Days | 420 | 251 | 348 | Fast development, unit testing, and demonstration |
| `workforce_full.db` | `FULL` | 2,000 | 100 | 90 Days | 27,000 | 5,000 | 53,473 | Enterprise-scale stress testing, OR-Tools validation |

### Dynamic Session Routing Mechanics:
1. `backend/models/database.py` defines `DynamicSessionLocal` and `DynamicEngineProxy`.
2. When an API request or test executes, `get_db()` inspects the current active profile via `get_active_profile()`.
3. The session factory dynamically binds to the active profile's SQLite connection pool.
4. Foreign key integrity (`PRAGMA foreign_keys = ON;`) and Write-Ahead Logging (`PRAGMA journal_mode = WAL;`) are enforced independently on each database file.
5. Ground-truth evaluation files are stored separately (`datasets/ground_truth/ground_truth.json` and `datasets/full/ground_truth.json`), guaranteeing zero operational database leakage.

