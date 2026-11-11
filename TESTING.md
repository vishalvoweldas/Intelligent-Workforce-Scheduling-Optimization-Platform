# Automated Testing Strategy & Verification Protocols
## Intelligent Workforce Scheduling & Optimization Platform

**Document Version:** 1.0.0  
**Test Harness:** Pytest 9.1+, Pytest-Asyncio, HTTPX, Vitest  
**Coverage Objective:** Minimum 85% branch coverage on core logic  

---

## 1. Test Suite Architecture

The test suite is structured into clear test categories under `tests/`:

```
tests/
├── unit/                  # Fast deterministic business logic & calculation tests
│   ├── test_id_generator.py
│   ├── test_shift_duration.py
│   ├── test_overtime_math.py
│   ├── test_fairness_metrics.py
│   └── test_rest_periods.py
├── scheduling/            # Constraint satisfaction & OR-Tools CP-SAT solver tests
│   ├── test_hard_constraints.py
│   ├── test_soft_objectives.py
│   ├── test_leave_protection.py
│   ├── test_skill_eligibility.py
│   ├── test_infeasible_scenarios.py
│   └── test_overnight_shifts.py
├── data_quality/          # Synthetic data, relational integrity & anomaly checks
│   ├── test_reproducibility.py
│   ├── test_referential_integrity.py
│   ├── test_anomaly_injection.py
│   └── test_ground_truth_separation.py
├── integration/           # Workflow & database transaction tests
│   ├── test_leave_workflow.py
│   ├── test_swap_atomic_flow.py
│   ├── test_attendance_reconciliation.py
│   └── test_api_endpoints.py
└── e2e/                   # Complete end-to-end user journeys
    └── test_full_system_lifecycle.py
```

---

## 2. Requirement-to-Test Traceability Matrix (P0 Mapping)

| Req ID | Requirement Description | Test File | Test Method |
| :--- | :--- | :--- | :--- |
| **FR-008** | CP-SAT Solver Integration | `tests/scheduling/test_hard_constraints.py` | `test_cpsat_solver_feasible_output()` |
| **FR-009** | Double Booking Prevention | `tests/scheduling/test_hard_constraints.py` | `test_solver_zero_double_booking()` |
| **FR-010** | Approved Leave Protection | `tests/scheduling/test_leave_protection.py` | `test_employee_on_leave_not_assigned()` |
| **FR-011** | Skill Eligibility Enforcement| `tests/scheduling/test_skill_eligibility.py` | `test_unskilled_employee_not_assigned()` |
| **FR-012** | Max Hours & Overtime Cap | `tests/scheduling/test_hard_constraints.py` | `test_weekly_hour_cap_strictly_enforced()`|
| **FR-013** | Minimum 11h Rest Period | `tests/scheduling/test_rest_periods.py` | `test_rest_interval_violations_zero()` |
| **FR-014** | Max 6 Consecutive Days | `tests/scheduling/test_hard_constraints.py` | `test_max_consecutive_days_enforced()` |
| **FR-019** | Explainable Coverage Gaps | `tests/scheduling/test_infeasible_scenarios.py`| `test_infeasible_generates_gap_records()` |
| **FR-021** | Leave Approval Workflow | `tests/integration/test_leave_workflow.py` | `test_leave_approval_creates_audit_event()`|
| **FR-025** | Atomic Shift Swap | `tests/integration/test_swap_atomic_flow.py` | `test_swap_applied_atomically_with_audit()`|
| **FR-027** | Attendance Reconciliation| `tests/integration/test_attendance_reconciliation.py`| `test_reconciliation_classifies_late_absent()`|
| **FR-030** | Fixed Seed Reproducibility| `tests/data_quality/test_reproducibility.py`| `test_dual_generation_identical_hashes()` |
| **FR-032** | 5 Anomaly Injections | `tests/data_quality/test_anomaly_injection.py`| `test_all_five_anomalies_injected_properly()`|
| **FR-033** | Ground Truth Isolation | `tests/data_quality/test_ground_truth_separation.py`| `test_ground_truth_not_imported_in_solver()`|
| **FR-037** | Confusion Matrix & F1 | `tests/integration/test_evaluation.py` | `test_evaluation_calculates_precision_recall_f1()`|

---

## 3. How to Execute Test Suites

### Run All Tests
```powershell
pytest tests/ -v
```

### Run Scheduling Solver Tests Only
```powershell
pytest tests/scheduling/ -v -s
```

### Run Data Quality & Reproducibility Tests Only
```powershell
pytest tests/data_quality/ -v
```

### Generate Coverage Report
```powershell
pytest --cov=backend --cov=data_engine --cov-report=term-missing tests/
```

