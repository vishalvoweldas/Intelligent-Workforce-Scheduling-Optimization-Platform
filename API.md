# REST API Specification & Endpoint Documentation
## Intelligent Workforce Scheduling & Optimization Platform

**Document Version:** 1.0.0  
**API Prefix:** `/api/v1`  
**Authentication:** Bearer JWT Token (`Authorization: Bearer <token>`)  

---

## 1. Global Conventions

### 1.1 Response Envelope
All API endpoints return standard JSON responses:
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully",
  "meta": {
    "page": 1,
    "limit": 50,
    "total_records": 100
  }
}
```

### 1.2 Error Envelope
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Shift assignment violates minimum 11-hour rest period rule.",
    "details": {
      "field": "start_datetime",
      "required_rest_hours": 11.0,
      "actual_rest_hours": 7.5
    }
  }
}
```

---

## 2. Authentication & Session Endpoints

### 2.1 Login / Token Grant
- **Endpoint:** `POST /api/v1/auth/login`
- **Access:** Public
- **Request Body:**
  ```json
  {
    "email": "alex.miller@workforce.internal",
    "password": "SecurePassword123!"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "data": {
      "access_token": "eyJhbGciOiJIUzI1...",
      "token_type": "bearer",
      "expires_in": 3600,
      "user": {
        "employee_id": "EMP-000001",
        "first_name": "Alex",
        "last_name": "Miller",
        "role": "MANAGER",
        "team_id": "TEAM-001"
      }
    }
  }
  ```

### 2.2 Current User Context
- **Endpoint:** `GET /api/v1/auth/me`
- **Access:** Any authenticated role

---

## 3. Workforce Management Endpoints

### 3.1 List Employees
- **Endpoint:** `GET /api/v1/employees`
- **Access:** All roles (Filtered by team for Employee/Manager)
- **Query Params:** `team_id`, `role`, `status`, `search`, `page`, `limit`

### 3.2 Get Employee Profile
- **Endpoint:** `GET /api/v1/employees/{employee_id}`
- **Access:** Self, Manager of team, HR, Admin

### 3.3 Create Employee
- **Endpoint:** `POST /api/v1/employees`
- **Access:** HR_PARTNER, ADMIN

### 3.4 List Teams & Departments
- **Endpoint:** `GET /api/v1/teams`
- **Access:** All authenticated users

### 3.5 Skills Directory & Proficiency Mappings
- **Endpoint:** `GET /api/v1/skills`
- **Endpoint:** `GET /api/v1/employees/{employee_id}/skills`

---

## 4. Shift & Coverage Endpoints

### 4.1 Shift Templates
- **Endpoint:** `GET /api/v1/shifts/templates`
- **Endpoint:** `POST /api/v1/shifts/templates` (HR_PARTNER, ADMIN)

### 4.2 Query Dated Shifts
- **Endpoint:** `GET /api/v1/shifts`
- **Query Params:** `team_id`, `start_date`, `end_date`, `status`

### 4.3 Shift Assignments
- **Endpoint:** `GET /api/v1/shift-assignments`
- **Query Params:** `shift_id`, `employee_id`, `date`

### 4.4 Coverage Requirements
- **Endpoint:** `GET /api/v1/coverage/requirements`
- **Endpoint:** `POST /api/v1/coverage/requirements` (MANAGER, HR, ADMIN)

---

## 5. Constraint Optimization & Scheduling Engine

### 5.1 Execute Schedule Optimizer
- **Endpoint:** `POST /api/v1/schedules/run`
- **Access:** MANAGER, OPERATIONS, ADMIN
- **Request Body:**
  ```json
  {
    "team_id": "TEAM-001",
    "start_date": "2026-01-01",
    "end_date": "2026-01-14",
    "weights": {
      "unfilled_penalty": 10000,
      "overtime_penalty": 50,
      "fairness_weight": 20,
      "night_penalty": 15,
      "preference_weight": 5
    },
    "timeout_seconds": 30,
    "seed": 20261022
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "data": {
      "schedule_run_id": "RUN-2026-000001",
      "status": "OPTIMAL",
      "solver_time_seconds": 1.42,
      "objective_value": 340.0,
      "total_shifts": 42,
      "assigned_shifts": 42,
      "unfilled_shifts": 0,
      "hard_violations": 0,
      "coverage_rate": 1.0,
      "fairness_hours_stdev": 1.85,
      "gaps": []
    }
  }
  ```

### 5.2 Get Schedule Run Diagnostics
- **Endpoint:** `GET /api/v1/schedules/runs/{run_id}`
- **Endpoint:** `GET /api/v1/schedules/runs/{run_id}/gaps`

---

## 6. Leave Management Endpoints

### 6.1 Submit Leave Request
- **Endpoint:** `POST /api/v1/leave-requests`
- **Access:** Authenticated employee (Self)
- **Request Body:**
  ```json
  {
    "leave_type": "ANNUAL",
    "start_date": "2026-01-05",
    "end_date": "2026-01-08",
    "comments": "Family vacation"
  }
  ```

### 6.2 List Leave Requests
- **Endpoint:** `GET /api/v1/leave-requests`
- **Query Params:** `employee_id`, `status`, `team_id`, `start_date`, `end_date`

### 6.3 Approve / Reject Leave Request
- **Endpoint:** `POST /api/v1/leave-requests/{leave_id}/decide`
- **Access:** MANAGER, HR_PARTNER, ADMIN
- **Request Body:**
  ```json
  {
    "decision": "APPROVED",
    "comments": "Coverage confirmed by team lead"
  }
  ```

---

## 7. Shift Swap Endpoints

### 7.1 Initiate Shift Swap
- **Endpoint:** `POST /api/v1/swaps`
- **Access:** EMPLOYEE (Owner of original assignment)
- **Request Body:**
  ```json
  {
    "original_assignment_id": "ASGN-000012",
    "receiving_employee_id": "EMP-000018",
    "proposed_assignment_id": "ASGN-000025",
    "reason": "Personal appointment"
  }
  ```

### 7.2 Feasibility Pre-Check
- **Endpoint:** `POST /api/v1/swaps/validate`
- **Returns:** Real-time validation object for Skill eligibility, Rest period compliance, and Overtime caps for both employees.

### 7.3 Manager Approval & Atomic Execution
- **Endpoint:** `POST /api/v1/swaps/{swap_id}/decide`
- **Access:** MANAGER, ADMIN
- **Request Body:**
  ```json
  {
    "decision": "APPROVED",
    "rejection_reason": null
  }
  ```

---

## 8. Attendance & Overtime Endpoints

### 8.1 Ingest Attendance Event
- **Endpoint:** `POST /api/v1/attendance/events`
- **Request Body:**
  ```json
  {
    "employee_id": "EMP-000005",
    "assignment_id": "ASGN-000012",
    "event_type": "CLOCK_IN",
    "event_timestamp": "2026-01-01T07:58:30Z",
    "source": "BIOMETRIC"
  }
  ```

### 8.2 Attendance Reconciliation & Hours Summary
- **Endpoint:** `GET /api/v1/attendance/reconciliation`
- **Query Params:** `team_id`, `date`, `discrepancy_only`

---

## 9. Analytics & Reporting Endpoints

- `GET /api/v1/analytics/coverage`: Detailed fill-rates and gap analysis.
- `GET /api/v1/analytics/fairness`: Gini coefficient, hours standard deviation, and weekend/night rotation equity.
- `GET /api/v1/analytics/overtime`: Team and employee overtime utilization.
- `GET /api/v1/analytics/export`: Download report in Markdown, JSON, or CSV.

---

## 10. Synthetic Data Engine & Benchmark Evaluation

### 10.1 List Dataset Profiles
- **Endpoint:** `GET /api/v1/datasets/profiles`
- **Access:** All Roles
- **Response:**
  ```json
  {
    "active_profile": "STARTER",
    "profiles": [
      {
        "id": "STARTER",
        "name": "Starter Profile (100 Employees)",
        "badge_label": "Simulation: STARTER (100 Employees | 10 Teams | 14 Days)",
        "employees_count": 100,
        "teams_count": 10,
        "horizon_days": 14,
        "start_date": "2026-01-01",
        "end_date": "2026-01-14",
        "leaves_count": 250,
        "is_active": true,
        "is_generated": true
      },
      {
        "id": "FULL",
        "name": "Full Profile Volume (2,000 Employees)",
        "badge_label": "Simulation: FULL PROFILE (2,000 Employees | 100 Teams | 90 Days)",
        "employees_count": 2000,
        "teams_count": 100,
        "horizon_days": 90,
        "start_date": "2026-01-01",
        "end_date": "2026-03-31",
        "leaves_count": 5000,
        "is_active": false,
        "is_generated": true
      }
    ]
  }
  ```

### 10.2 Get Active Profile Metadata
- **Endpoint:** `GET /api/v1/datasets/active-profile`
- **Access:** All Roles
- **Response:** Returns live table counts and date horizons for the active database.

### 10.3 Switch Dataset Profile
- **Endpoint:** `POST /api/v1/datasets/switch-profile`
- **Access:** All Roles (authenticated)
- **Request Body:**
  ```json
  {
    "profile": "FULL"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "active_profile": "FULL",
    "badge_label": "Simulation: FULL PROFILE (2,000 Employees | 100 Teams | 90 Days)",
    "message": "Successfully switched active dataset profile to Full Profile Volume (2,000 Employees)",
    "stats": { ... }
  }
  ```

### 10.4 Trigger Synthetic Generation
- **Endpoint:** `POST /api/v1/datasets/generate`
- **Access:** OPERATIONS, ADMIN
- **Request Body:**
  ```json
  {
    "profile": "STARTER",
    "seed": 20261022,
    "inject_anomalies": true
  }
  ```

### 10.5 Run Anomaly Detection & Ground Truth Benchmark
- **Endpoint:** `POST /api/v1/evaluations/run`
- **Access:** OPERATIONS, ADMIN
- **Response:**
  ```json
  {
    "evaluation_id": "EVAL-20261111-001",
    "confusion_matrix": {
      "true_positives": 25,
      "false_positives": 1,
      "true_negatives": 1200,
      "false_negatives": 0
    },
    "metrics": {
      "precision": 0.9615,
      "recall": 1.0,
      "f1_score": 0.9804
    },
    "by_category": {
      "DOUBLE_BOOKING": { "precision": 1.0, "recall": 1.0, "f1": 1.0 },
      "LEAVE_CONFLICT": { "precision": 1.0, "recall": 1.0, "f1": 1.0 },
      "MISSING_SKILL": { "precision": 1.0, "recall": 1.0, "f1": 1.0 },
      "OVERTIME_EXCEEDED": { "precision": 1.0, "recall": 1.0, "f1": 1.0 },
      "UNAPPROVED_SWAP": { "precision": 0.833, "recall": 1.0, "f1": 0.909 }
    }
  }
  ```

