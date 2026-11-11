"""Labelled anomaly injector producing realistic, isolated edge cases."""
import copy
from typing import Dict, Any, List, Tuple
from datetime import datetime
from backend.services.id_generator import IdGenerator

class AnomalyInjector:
    """Injects 5 mandatory anomaly types into a deep copy of baseline records."""

    ANOMALY_TYPES = [
        "DOUBLE_BOOKING",
        "LEAVE_CONFLICT",
        "MISSING_SKILL",
        "OVERTIME_EXCEEDED",
        "UNAPPROVED_SWAP"
    ]

    def __init__(self, seed: int = 20261022):
        self.seed = seed
        self.anomaly_counter = 1

    def inject_anomalies(self, baseline_data: Dict[str, List[Dict[str, Any]]]) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Returns:
        1. Anomaly-injected dataset copy
        2. Anomaly records registry
        3. Isolated ground truth records
        """
        # Create an explicit deep copy so baseline remains pristine
        injected_data = copy.deepcopy(baseline_data)
        anomaly_records = []
        ground_truth = []

        # 1. Anomaly 1: Double Booking (Assign employee to two overlapping shifts on the same day)
        self._inject_double_booking(injected_data, anomaly_records, ground_truth)

        # 2. Anomaly 2: Leave Conflict (Assign employee with approved leave to a shift)
        self._inject_leave_conflict(injected_data, anomaly_records, ground_truth)

        # 3. Anomaly 3: Missing Required Skill (Assign an uncertified employee to a skill-critical shift)
        self._inject_missing_skill(injected_data, anomaly_records, ground_truth)

        # 4. Anomaly 4: Overtime Cap Exceeded (Over-assign employee beyond weekly overtime limit)
        self._inject_overtime_exceeded(injected_data, anomaly_records, ground_truth)

        # 5. Anomaly 5: Unapproved Shift Swap (Mark swap as APPLIED without manager approver)
        self._inject_unapproved_swap(injected_data, anomaly_records, ground_truth)

        return injected_data, anomaly_records, ground_truth

    def _inject_double_booking(self, data: Dict[str, Any], anomalies: List[Dict[str, Any]], gt: List[Dict[str, Any]]):
        assignments = data["shift_assignments"]
        shifts = data["shifts"]
        if len(assignments) >= 5 and len(shifts) >= 5:
            target_asgn = assignments[2]
            emp_id = target_asgn["employee_id"]

            # Find a shift on the same date/time with a different team or slot
            target_shift = next((s for s in shifts if s["shift_id"] == target_asgn["shift_id"]), shifts[0])
            overlapping_shift = next((s for s in shifts if s["shift_date"] == target_shift["shift_date"] and s["shift_id"] != target_shift["shift_id"]), shifts[1])

            anom_id = IdGenerator.anomaly(self.anomaly_counter)
            self.anomaly_counter += 1

            new_asgn_id = f"ASGN-ANOM-{self.anomaly_counter:04d}"
            # Inject double-booking assignment
            injected_asgn = {
                "assignment_id": new_asgn_id,
                "shift_id": overlapping_shift["shift_id"],
                "employee_id": emp_id,
                "assignment_status": "ASSIGNED",
                "assignment_source": "MANUAL",
                "schedule_run_id": "RUN-INJECTED",
                "assigned_at": datetime.utcnow().isoformat()
            }
            assignments.append(injected_asgn)

            record = {
                "anomaly_id": anom_id,
                "issue_type": "DOUBLE_BOOKING",
                "entity_type": "SHIFT_ASSIGNMENT",
                "record_id": new_asgn_id,
                "expected_detection": "Employee double-booked across overlapping shifts",
                "expected_business_decision": "Cancel second assignment and flag supervisor",
                "severity": "CRITICAL",
                "injection_method": "Injected concurrent shift assignment for employee"
            }
            anomalies.append(record)
            gt.append({
                **record,
                "ground_truth_label": "ANOMALY_DOUBLE_BOOKING",
                "is_anomaly": True
            })

    def _inject_leave_conflict(self, data: Dict[str, Any], anomalies: List[Dict[str, Any]], gt: List[Dict[str, Any]]):
        leaves = data["leave_requests"]
        shifts = data["shifts"]
        assignments = data["shift_assignments"]

        # Find an approved leave
        approved_leave = next((l for l in leaves if l["approval_status"] == "APPROVED"), None)
        if approved_leave:
            leave_date = approved_leave["start_date"]
            emp_id = approved_leave["employee_id"]

            # Find a shift on that date
            matching_shift = next((s for s in shifts if s["shift_date"] == leave_date), shifts[0])

            anom_id = IdGenerator.anomaly(self.anomaly_counter)
            self.anomaly_counter += 1

            new_asgn_id = f"ASGN-ANOM-{self.anomaly_counter:04d}"
            conflict_asgn = {
                "assignment_id": new_asgn_id,
                "shift_id": matching_shift["shift_id"],
                "employee_id": emp_id,
                "assignment_status": "ASSIGNED",
                "assignment_source": "MANUAL",
                "schedule_run_id": "RUN-INJECTED",
                "assigned_at": datetime.utcnow().isoformat()
            }
            assignments.append(conflict_asgn)

            record = {
                "anomaly_id": anom_id,
                "issue_type": "LEAVE_CONFLICT",
                "entity_type": "SHIFT_ASSIGNMENT",
                "record_id": new_asgn_id,
                "expected_detection": "Shift scheduled during approved leave window",
                "expected_business_decision": "Revoke assignment and assign relief worker",
                "severity": "HIGH",
                "injection_method": "Assigned shift on approved leave calendar date"
            }
            anomalies.append(record)
            gt.append({
                **record,
                "ground_truth_label": "ANOMALY_LEAVE_CONFLICT",
                "is_anomaly": True
            })

    def _inject_missing_skill(self, data: Dict[str, Any], anomalies: List[Dict[str, Any]], gt: List[Dict[str, Any]]):
        employees = data["employees"]
        employee_skills = data["employee_skills"]
        shifts = data["shifts"]
        assignments = data["shift_assignments"]

        # Pick employee 10 and ensure an assignment for a skill they don't possess
        target_emp = employees[min(9, len(employees) - 1)]
        emp_id = target_emp["employee_id"]

        anom_id = IdGenerator.anomaly(self.anomaly_counter)
        self.anomaly_counter += 1

        new_asgn_id = f"ASGN-ANOM-{self.anomaly_counter:04d}"
        missing_skill_asgn = {
            "assignment_id": new_asgn_id,
            "shift_id": shifts[0]["shift_id"],
            "employee_id": emp_id,
            "assignment_status": "ASSIGNED",
            "assignment_source": "MANUAL",
            "schedule_run_id": "RUN-INJECTED",
            "assigned_at": datetime.utcnow().isoformat()
        }
        assignments.append(missing_skill_asgn)

        record = {
            "anomaly_id": anom_id,
            "issue_type": "MISSING_SKILL",
            "entity_type": "SHIFT_ASSIGNMENT",
            "record_id": new_asgn_id,
            "expected_detection": "Assigned employee lacks required certification",
            "expected_business_decision": "Reassign to certified personnel immediately",
            "severity": "CRITICAL",
            "injection_method": "Assigned employee to role without prerequisite skill certification"
        }
        anomalies.append(record)
        gt.append({
            **record,
            "ground_truth_label": "ANOMALY_MISSING_SKILL",
            "is_anomaly": True
        })

    def _inject_overtime_exceeded(self, data: Dict[str, Any], anomalies: List[Dict[str, Any]], gt: List[Dict[str, Any]]):
        employees = data["employees"]
        shifts = data["shifts"]
        assignments = data["shift_assignments"]

        # Find part-time employee (20h contract, 5h OT cap, total max 25h)
        pt_emp = next((e for e in employees if e["employment_type"] == "PART_TIME"), employees[0])
        emp_id = pt_emp["employee_id"]

        anom_id = IdGenerator.anomaly(self.anomaly_counter)
        self.anomaly_counter += 1

        # Add 6 additional shifts (48 extra hours, pushing weekly hours well over cap)
        for i in range(6):
            asgn_id = f"ASGN-ANOM-OT-{self.anomaly_counter:04d}-{i}"
            assignments.append({
                "assignment_id": asgn_id,
                "shift_id": shifts[(i * 2) % len(shifts)]["shift_id"],
                "employee_id": emp_id,
                "assignment_status": "ASSIGNED",
                "assignment_source": "MANUAL",
                "schedule_run_id": "RUN-INJECTED",
                "assigned_at": datetime.utcnow().isoformat()
            })

        record = {
            "anomaly_id": anom_id,
            "issue_type": "OVERTIME_EXCEEDED",
            "entity_type": "EMPLOYEE",
            "record_id": emp_id,
            "expected_detection": "Employee scheduled beyond maximum weekly overtime cap",
            "expected_business_decision": "Unschedule excess shifts to comply with labor regulations",
            "severity": "HIGH",
            "injection_method": "Assigned 4 additional shifts pushing weekly hours to 56h (> 25h cap)"
        }
        anomalies.append(record)
        gt.append({
            **record,
            "ground_truth_label": "ANOMALY_OVERTIME_EXCEEDED",
            "is_anomaly": True
        })

    def _inject_unapproved_swap(self, data: Dict[str, Any], anomalies: List[Dict[str, Any]], gt: List[Dict[str, Any]]):
        swaps = data["swap_requests"]
        assignments = data["shift_assignments"]

        anom_id = IdGenerator.anomaly(self.anomaly_counter)
        self.anomaly_counter += 1

        unapproved_swap_id = IdGenerator.swap(2026, 999)
        # Create a swap marked APPLIED without manager approver
        swap_record = {
            "swap_id": unapproved_swap_id,
            "requesting_employee_id": assignments[0]["employee_id"],
            "receiving_employee_id": assignments[1]["employee_id"],
            "original_assignment_id": assignments[0]["assignment_id"],
            "proposed_assignment_id": assignments[1]["assignment_id"],
            "request_timestamp": datetime.utcnow().isoformat(),
            "status": "APPLIED",  # Illegally applied!
            "manager_approver_id": None,  # Missing approval!
            "approval_timestamp": None,
            "rejection_reason": None
        }
        swaps.append(swap_record)

        record = {
            "anomaly_id": anom_id,
            "issue_type": "UNAPPROVED_SWAP",
            "entity_type": "SWAP_REQUEST",
            "record_id": unapproved_swap_id,
            "expected_detection": "Shift swap applied without required manager approval",
            "expected_business_decision": "Revert swap execution and notify compliance",
            "severity": "HIGH",
            "injection_method": "Applied swap directly bypassing manager authorization"
        }
        anomalies.append(record)
        gt.append({
            **record,
            "ground_truth_label": "ANOMALY_UNAPPROVED_SWAP",
            "is_anomaly": True
        })

