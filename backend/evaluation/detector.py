"""Automated anomaly and exception detector scanning operational data."""
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Set, Tuple

class AnomalyDetector:
    """Scans workforce database/dataset to detect labor violations, conflicts, and unauthorized state changes."""

    def detect_all(self, data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        detected_anomalies = []

        # 1. Detect Double Bookings
        self._detect_double_bookings(data, detected_anomalies)

        # 2. Detect Leave Conflicts
        self._detect_leave_conflicts(data, detected_anomalies)

        # 3. Detect Missing Required Skills
        self._detect_missing_skills(data, detected_anomalies)

        # 4. Detect Overtime Cap Breaches
        self._detect_overtime_exceeded(data, detected_anomalies)

        # 5. Detect Unapproved Swaps
        self._detect_unapproved_swaps(data, detected_anomalies)

        return detected_anomalies

    def _detect_double_bookings(self, data: Dict[str, Any], anomalies: List[Dict[str, Any]]):
        shifts_by_id = {s["shift_id"]: s for s in data.get("shifts", [])}
        emp_assignments: Dict[str, List[Dict[str, Any]]] = {}

        for asgn in data.get("shift_assignments", []):
            emp_assignments.setdefault(asgn["employee_id"], []).append(asgn)

        for emp_id, asgns in emp_assignments.items():
            if len(asgns) < 2:
                continue
            for i in range(len(asgns)):
                asgn1 = asgns[i]
                s1 = shifts_by_id.get(asgn1["shift_id"])
                if not s1:
                    continue
                s1_start = datetime.fromisoformat(s1["start_datetime"])
                s1_end = datetime.fromisoformat(s1["end_datetime"])

                for j in range(i + 1, len(asgns)):
                    asgn2 = asgns[j]
                    s2 = shifts_by_id.get(asgn2["shift_id"])
                    if not s2:
                        continue
                    s2_start = datetime.fromisoformat(s2["start_datetime"])
                    s2_end = datetime.fromisoformat(s2["end_datetime"])

                    # Check overlap
                    if max(s1_start, s2_start) < min(s1_end, s2_end):
                        anomalies.append({
                            "issue_type": "DOUBLE_BOOKING",
                            "entity_type": "SHIFT_ASSIGNMENT",
                            "record_id": asgn2["assignment_id"],
                            "affected_employee": emp_id,
                            "affected_shift": s2["shift_id"],
                            "conflicting_shift": s1["shift_id"],
                            "severity": "CRITICAL",
                            "explanation": f"Employee {emp_id} is double-booked on overlapping shifts {s1['shift_id']} and {s2['shift_id']}",
                            "expected_business_action": "Cancel overlapping shift assignment and notify supervisor"
                        })

    def _detect_leave_conflicts(self, data: Dict[str, Any], anomalies: List[Dict[str, Any]]):
        shifts_by_id = {s["shift_id"]: s for s in data.get("shifts", [])}

        # Index approved leaves
        approved_leaves: Dict[str, List[Tuple[date, date, str]]] = {}
        for l in data.get("leave_requests", []):
            if l.get("approval_status") == "APPROVED":
                s_dt = date.fromisoformat(l["start_date"])
                e_dt = date.fromisoformat(l["end_date"])
                approved_leaves.setdefault(l["employee_id"], []).append((s_dt, e_dt, l["leave_id"]))

        for asgn in data.get("shift_assignments", []):
            emp_id = asgn["employee_id"]
            if emp_id in approved_leaves:
                s = shifts_by_id.get(asgn["shift_id"])
                if not s:
                    continue
                s_date = date.fromisoformat(s["shift_date"])
                for (l_start, l_end, l_id) in approved_leaves[emp_id]:
                    if l_start <= s_date <= l_end:
                        anomalies.append({
                            "issue_type": "LEAVE_CONFLICT",
                            "entity_type": "SHIFT_ASSIGNMENT",
                            "record_id": asgn["assignment_id"],
                            "affected_employee": emp_id,
                            "affected_shift": s["shift_id"],
                            "leave_id": l_id,
                            "severity": "HIGH",
                            "explanation": f"Employee {emp_id} is assigned to shift on {s_date} during approved leave ({l_start} to {l_end})",
                            "expected_business_action": "Revoke assignment and assign available relief staff"
                        })

    def _detect_missing_skills(self, data: Dict[str, Any], anomalies: List[Dict[str, Any]]):
        # Index employee certified skills
        emp_certs: Dict[str, Set[str]] = {}
        for es in data.get("employee_skills", []):
            if es.get("is_certified", False):
                emp_certs.setdefault(es["employee_id"], set()).add(es["skill_id"])

        shifts_by_id = {s["shift_id"]: s for s in data.get("shifts", [])}

        # Build map of (team_id, template_id) -> required skills
        cov_map: Dict[Tuple[str, str], List[str]] = {}
        for cov in data.get("coverage_requirements", []):
            cov_map.setdefault((cov["team_id"], cov["template_id"]), []).append(cov["skill_id"])

        for asgn in data.get("shift_assignments", []):
            s = shifts_by_id.get(asgn["shift_id"])
            if not s:
                continue
            req_skills = cov_map.get((s["team_id"], s["template_id"]), [])
            emp_id = asgn["employee_id"]
            holding_skills = emp_certs.get(emp_id, set())

            for req_sk in req_skills:
                if req_sk not in holding_skills:
                    anomalies.append({
                        "issue_type": "MISSING_SKILL",
                        "entity_type": "SHIFT_ASSIGNMENT",
                        "record_id": asgn["assignment_id"],
                        "affected_employee": emp_id,
                        "affected_shift": s["shift_id"],
                        "missing_skill": req_sk,
                        "severity": "CRITICAL",
                        "explanation": f"Employee {emp_id} lacks mandatory skill certification {req_sk} for shift {s['shift_id']}",
                        "expected_business_action": "Reassign to certified personnel immediately"
                    })

    def _detect_overtime_exceeded(self, data: Dict[str, Any], anomalies: List[Dict[str, Any]]):
        emp_by_id = {e["employee_id"]: e for e in data.get("employees", [])}
        emp_hours: Dict[str, float] = {e_id: 0.0 for e_id in emp_by_id}

        for asgn in data.get("shift_assignments", []):
            emp_hours[asgn["employee_id"]] = emp_hours.get(asgn["employee_id"], 0.0) + 8.0

        # Calculate horizon duration in weeks
        shift_dates = [s["shift_date"] for s in data.get("shifts", [])]
        if shift_dates:
            min_date = min(shift_dates)
            max_date = max(shift_dates)
            from datetime import date
            days_span = max(7, (date.fromisoformat(max_date) - date.fromisoformat(min_date)).days + 1)
            weeks = days_span / 7.0
        else:
            weeks = 1.0

        for emp_id, total_hrs in emp_hours.items():
            emp = emp_by_id.get(emp_id)
            if not emp:
                continue
            contract_hrs = emp.get("contracted_weekly_hours", 40.0)
            ot_cap = emp.get("overtime_cap_hours", 8.0)
            max_legal_cap = (contract_hrs + ot_cap) * weeks

            if total_hrs > max_legal_cap:
                anomalies.append({
                    "issue_type": "OVERTIME_EXCEEDED",
                    "entity_type": "EMPLOYEE",
                    "record_id": emp_id,
                    "affected_employee": emp_id,
                    "scheduled_hours": total_hrs,
                    "cap_hours": max_legal_cap,
                    "severity": "HIGH",
                    "explanation": f"Employee {emp_id} scheduled for {total_hrs}h, exceeding overtime limit of {max_legal_cap}h",
                    "expected_business_action": "Unschedule excess shifts to comply with labor laws"
                })

    def _detect_unapproved_swaps(self, data: Dict[str, Any], anomalies: List[Dict[str, Any]]):
        for swp in data.get("swap_requests", []):
            if swp.get("status") == "APPLIED" and not swp.get("manager_approver_id"):
                anomalies.append({
                    "issue_type": "UNAPPROVED_SWAP",
                    "entity_type": "SWAP_REQUEST",
                    "record_id": swp["swap_id"],
                    "affected_employee": swp["requesting_employee_id"],
                    "receiving_employee": swp["receiving_employee_id"],
                    "severity": "HIGH",
                    "explanation": f"Swap {swp['swap_id']} was applied without manager authorization",
                    "expected_business_action": "Revert shift assignments and flag security compliance"
                })

