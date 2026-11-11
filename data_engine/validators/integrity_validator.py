"""Data quality and integrity validator."""
from typing import Dict, Any, List
from datetime import datetime, date

class IntegrityValidator:
    """Validates relational consistency, foreign keys, enums, and dates."""

    def validate_dataset(self, data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        report = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "summary": {
                "tables_checked": len(data),
                "total_records": sum(len(records) for records in data.values()),
                "checks_passed": 0,
                "checks_failed": 0
            }
        }

        # 1. Primary Key Uniqueness
        self._check_pk_uniqueness(data, report)

        # 2. Foreign Key Integrity
        self._check_foreign_keys(data, report)

        # 3. Date Ordering
        self._check_date_ordering(data, report)

        # 4. Enum Consistency
        self._check_enum_consistency(data, report)

        report["is_valid"] = len(report["errors"]) == 0
        return report

    def _check_pk_uniqueness(self, data: Dict[str, Any], report: Dict[str, Any]):
        pk_fields = {
            "employees": "employee_id",
            "teams": "team_id",
            "skills": "skill_id",
            "employee_skills": "id",
            "shift_templates": "template_id",
            "shifts": "shift_id",
            "shift_assignments": "assignment_id",
            "leave_requests": "leave_id",
            "coverage_requirements": "requirement_id",
            "swap_requests": "swap_id",
            "attendance_events": "attendance_id"
        }

        for table, pk in pk_fields.items():
            records = data.get(table, [])
            seen = set()
            duplicates = []
            for r in records:
                val = r.get(pk)
                if val in seen:
                    duplicates.append(val)
                seen.add(val)

            if duplicates:
                report["errors"].append(f"Table '{table}' has duplicate PK values: {duplicates[:5]}")
                report["summary"]["checks_failed"] += 1
            else:
                report["summary"]["checks_passed"] += 1

    def _check_foreign_keys(self, data: Dict[str, Any], report: Dict[str, Any]):
        # Collect parent ID sets
        employee_ids = {e["employee_id"] for e in data.get("employees", [])}
        team_ids = {t["team_id"] for t in data.get("teams", [])}
        skill_ids = {s["skill_id"] for s in data.get("skills", [])}
        template_ids = {tmpl["template_id"] for tmpl in data.get("shift_templates", [])}
        shift_ids = {s["shift_id"] for s in data.get("shifts", [])}
        asgn_ids = {a["assignment_id"] for a in data.get("shift_assignments", [])}

        # Check employees -> teams
        for e in data.get("employees", []):
            if e["team_id"] not in team_ids:
                report["errors"].append(f"Employee {e['employee_id']} references nonexistent team {e['team_id']}")
                report["summary"]["checks_failed"] += 1
                return

        # Check shifts -> teams, templates
        for s in data.get("shifts", []):
            if s["team_id"] not in team_ids:
                report["errors"].append(f"Shift {s['shift_id']} references nonexistent team {s['team_id']}")
                report["summary"]["checks_failed"] += 1
                return
            if s["template_id"] not in template_ids:
                report["errors"].append(f"Shift {s['shift_id']} references nonexistent template {s['template_id']}")
                report["summary"]["checks_failed"] += 1
                return

        # Check assignments -> shifts, employees
        for a in data.get("shift_assignments", []):
            if a["shift_id"] not in shift_ids:
                report["errors"].append(f"Assignment {a['assignment_id']} references nonexistent shift {a['shift_id']}")
                report["summary"]["checks_failed"] += 1
                return
            if a["employee_id"] not in employee_ids:
                report["errors"].append(f"Assignment {a['assignment_id']} references nonexistent employee {a['employee_id']}")
                report["summary"]["checks_failed"] += 1
                return

        report["summary"]["checks_passed"] += 1

    def _check_date_ordering(self, data: Dict[str, Any], report: Dict[str, Any]):
        for l in data.get("leave_requests", []):
            s = l["start_date"]
            e = l["end_date"]
            if s > e:
                report["errors"].append(f"Leave {l['leave_id']} has start_date {s} > end_date {e}")
                report["summary"]["checks_failed"] += 1
                return
        report["summary"]["checks_passed"] += 1

    def _check_enum_consistency(self, data: Dict[str, Any], report: Dict[str, Any]):
        valid_leave_types = {"ANNUAL", "SICK", "UNPAID", "PARENTAL"}
        valid_leave_statuses = {"SUBMITTED", "PENDING", "APPROVED", "REJECTED", "CANCELLED"}

        for l in data.get("leave_requests", []):
            if l["leave_type"] not in valid_leave_types:
                report["errors"].append(f"Leave {l['leave_id']} has invalid type {l['leave_type']}")
                report["summary"]["checks_failed"] += 1
                return
            if l["approval_status"] not in valid_leave_statuses:
                report["errors"].append(f"Leave {l['leave_id']} has invalid status {l['approval_status']}")
                report["summary"]["checks_failed"] += 1
                return
        report["summary"]["checks_passed"] += 1

