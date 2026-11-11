"""Master synthetic workforce data generator."""
from datetime import date, datetime, timedelta, time
from typing import Dict, Any, List, Tuple
import hashlib
import json

from backend.services.id_generator import IdGenerator
from data_engine.distributions.samplers import DistributionSampler

# Config profiles
PROFILES = {
    "STARTER": {
        "num_employees": 100,
        "num_teams": 10,
        "horizon_days": 14,
        "num_leaves": 250,
        "start_date": date(2026, 1, 1),
    },
    "FULL": {
        "num_employees": 2000,
        "num_teams": 100,
        "horizon_days": 90,
        "num_leaves": 5000,
        "start_date": date(2026, 1, 1),
    }
}

FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Sam", "Dakota", "Jamie",
    "Cameron", "Reese", "Rowan", "Hayden", "Logan", "Parker", "Emerson", "Finley", "Skyler", "Jesse",
    "Chris", "Pat", "Drew", "Robin", "Kendall", "Peyton", "Adrian", "Elliot", "Harper", "Quinn"
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"
]

SKILL_CATALOG = [
    ("Critical Clinical Care", "CLINICAL", "Emergency trauma & critical care administration"),
    ("Heavy Equipment Operation", "MACHINERY", "Forklift, crane & specialized heavy gear"),
    ("Safety & Environmental Compliance", "SAFETY", "OSHA & workplace hazard protocols"),
    ("Quality Assurance & Inspection", "QUALITY", "Product precision inspection and standards audit"),
    ("Logistics & Dispatch Coordination", "LOGISTICS", "Fleet routing and warehouse dispatch"),
    ("Customer Resolution Support", "SUPPORT", "Complex incident escalation and customer handling"),
    ("Systems & Infrastructure Reliability", "IT_OPS", "Mission-critical systems & telemetry monitoring"),
    ("Hazardous Materials Protocol", "SAFETY", "Hazmat containment, storage & transport")
]

class SyntheticDataGenerator:
    """Deterministic synthetic data generator produces valid baseline datasets."""

    def __init__(self, profile_name: str = "STARTER", seed: int = 20261022):
        if profile_name not in PROFILES:
            raise ValueError(f"Unknown profile '{profile_name}'. Must be one of {list(PROFILES.keys())}")
        self.profile_name = profile_name
        self.config = PROFILES[profile_name]
        self.seed = seed
        self.sampler = DistributionSampler(seed=seed)
        self.rng = self.sampler.rng

    def generate_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generates all master and dependent tables in relational order."""
        # 1. Master Data
        teams = self._generate_teams()
        skills = self._generate_skills()
        templates = self._generate_shift_templates()
        employees = self._generate_employees(teams)
        employee_skills = self._generate_employee_skills(employees, skills)
        coverage_reqs = self._generate_coverage_requirements(teams, templates, skills)
        holidays = self._generate_holidays()

        # 2. Dependent Data
        shifts = self._generate_dated_shifts(teams, templates)
        leaves = self._generate_leave_requests(employees)
        assignments = self._generate_baseline_assignments(employees, shifts, coverage_reqs, employee_skills, leaves)
        attendance = self._generate_attendance_events(assignments, shifts)
        swaps = self._generate_swap_requests(employees, assignments)

        # 3. Derived Metrics
        derived_metrics = self._calculate_derived_metrics(employees, shifts, assignments, attendance)

        return {
            "teams": teams,
            "skills": skills,
            "shift_templates": templates,
            "employees": employees,
            "employee_skills": employee_skills,
            "coverage_requirements": coverage_reqs,
            "holiday_calendar": holidays,
            "shifts": shifts,
            "leave_requests": leaves,
            "shift_assignments": assignments,
            "attendance_events": attendance,
            "swap_requests": swaps,
            "derived_metrics": derived_metrics
        }

    def _generate_teams(self) -> List[Dict[str, Any]]:
        num_teams = self.config["num_teams"]
        departments = ["Operations", "Clinical", "Logistics", "Manufacturing", "Customer Care", "Field Ops"]
        locations = ["Chicago Hub", "Austin Facility", "Seattle Depot", "Denver Center", "Atlanta Station"]

        teams = []
        for i in range(1, num_teams + 1):
            t_id = IdGenerator.team(i)
            dept = departments[(i - 1) % len(departments)]
            loc = locations[(i - 1) % len(locations)]
            teams.append({
                "team_id": t_id,
                "team_name": f"{dept} Team {i:02d}",
                "department": dept,
                "location": loc,
                "manager_id": None,  # Will link after employees
                "is_active": True,
                "created_at": datetime(2026, 1, 1, 0, 0, 0).isoformat()
            })
        return teams

    def _generate_skills(self) -> List[Dict[str, Any]]:
        skills = []
        for i, (name, cat, desc) in enumerate(SKILL_CATALOG, start=1):
            skills.append({
                "skill_id": IdGenerator.skill(i),
                "skill_name": name,
                "category": cat,
                "description": desc,
                "is_active": True
            })
        return skills

    def _generate_shift_templates(self) -> List[Dict[str, Any]]:
        templates = [
            {
                "template_id": IdGenerator.shift_template("MORN"),
                "template_name": "Morning Shift",
                "start_time": "08:00",
                "end_time": "16:30",
                "break_duration_hours": 0.5,
                "category": "MORNING",
                "duration_hours": 8.0,
                "is_overnight": False,
                "applicable_days": "MON,TUE,WED,THU,FRI,SAT,SUN",
                "is_active": True
            },
            {
                "template_id": IdGenerator.shift_template("AFTN"),
                "template_name": "Afternoon Shift",
                "start_time": "16:00",
                "end_time": "00:30",
                "break_duration_hours": 0.5,
                "category": "AFTERNOON",
                "duration_hours": 8.0,
                "is_overnight": False,
                "applicable_days": "MON,TUE,WED,THU,FRI,SAT,SUN",
                "is_active": True
            },
            {
                "template_id": IdGenerator.shift_template("NGHT"),
                "template_name": "Night Shift (Overnight)",
                "start_time": "00:00",
                "end_time": "08:30",
                "break_duration_hours": 0.5,
                "category": "NIGHT",
                "duration_hours": 8.0,
                "is_overnight": True,
                "applicable_days": "MON,TUE,WED,THU,FRI,SAT,SUN",
                "is_active": True
            }
        ]
        return templates

    def _generate_employees(self, teams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        num_emp = self.config["num_employees"]
        employees = []

        for i in range(1, num_emp + 1):
            emp_id = IdGenerator.employee(i)
            # Assign uniformly across teams
            team = teams[(i - 1) % len(teams)]
            team_id = team["team_id"]

            first = FIRST_NAMES[(i * 7 + 3) % len(FIRST_NAMES)]
            last = LAST_NAMES[(i * 13 + 7) % len(LAST_NAMES)]
            email = f"{first.lower()}.{last.lower()}.{i:04d}@workforce.internal"

            emp_type, contracted_hrs, max_hrs, ot_cap = self.sampler.sample_employment_type()

            # First member of each team is designated as Manager
            role = "MANAGER" if i <= len(teams) else "EMPLOYEE"
            if role == "MANAGER" and team["manager_id"] is None:
                team["manager_id"] = emp_id

            # Ensure high-level admin and HR accounts exist
            if i == len(teams) + 1:
                role = "HR_PARTNER"
            elif i == len(teams) + 2:
                role = "OPERATIONS"
            elif i == len(teams) + 3:
                role = "ADMIN"

            hire_offset = (i * 17) % 1800  # Hired in past 5 years
            hire_date = (date(2026, 1, 1) - timedelta(days=hire_offset)).isoformat()

            employees.append({
                "employee_id": emp_id,
                "team_id": team_id,
                "first_name": first,
                "last_name": last,
                "email": email,
                "password_hash": "$2b$12$e80yvX7c5rM8pG3.9G1Hce5J/2H9k1O8C8Q6E7a8b9c0d1e2f3g4h", # hashed 'Workforce2026!'
                "role": role,
                "employment_type": emp_type,
                "employment_status": "ACTIVE",
                "hire_date": hire_date,
                "work_zone": team["location"],
                "contracted_weekly_hours": contracted_hrs,
                "max_working_hours": max_hrs,
                "overtime_cap_hours": ot_cap,
                "is_active": True,
                "created_at": datetime(2026, 1, 1, 0, 0, 0).isoformat()
            })

        return employees

    def _generate_employee_skills(self, employees: List[Dict[str, Any]], skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        skill_ids = [s["skill_id"] for s in skills]
        employee_skills = []

        for emp in employees:
            e_num = int(emp["employee_id"].split("-")[1])
            assigned_skills = self.sampler.sample_skill_assignments(skill_ids)
            for item in assigned_skills:
                s_num = int(item["skill_id"].split("-")[1])
                esk_id = IdGenerator.employee_skill(e_num, s_num)
                employee_skills.append({
                    "id": esk_id,
                    "employee_id": emp["employee_id"],
                    "skill_id": item["skill_id"],
                    "proficiency_level": item["proficiency_level"],
                    "is_certified": item["is_certified"],
                    "certification_expiry_date": (date(2026, 1, 1) + timedelta(days=365)).isoformat() if item["is_certified"] else (date(2025, 12, 1)).isoformat(),
                    "effective_start_date": "2025-01-01",
                    "effective_end_date": None
                })
        return employee_skills

    def _generate_coverage_requirements(self, teams: List[Dict[str, Any]], templates: List[Dict[str, Any]], skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        requirements = []
        cov_idx = 1
        for team in teams:
            for tmpl in templates:
                # Require primary skill (e.g. SKL-001 or SKL-002)
                sk_idx = (int(team["team_id"].split("-")[1]) % len(skills))
                req_skill = skills[sk_idx]["skill_id"]
                requirements.append({
                    "requirement_id": IdGenerator.coverage(cov_idx),
                    "team_id": team["team_id"],
                    "template_id": tmpl["template_id"],
                    "skill_id": req_skill,
                    "min_employees": 1,
                    "effective_start_date": "2026-01-01",
                    "effective_end_date": None
                })
                cov_idx += 1
        return requirements

    def _generate_holidays(self) -> List[Dict[str, Any]]:
        holidays_def = [
            ("HOL-001", "New Year's Day", "2026-01-01"),
            ("HOL-002", "Martin Luther King Jr. Day", "2026-01-19"),
            ("HOL-003", "Presidents' Day", "2026-02-16")
        ]
        return [
            {
                "holiday_id": h[0],
                "holiday_name": h[1],
                "holiday_date": h[2],
                "applicable_location": "GLOBAL",
                "applicable_team_id": None,
                "holiday_category": "PUBLIC"
            }
            for h in holidays_def
        ]

    def _generate_dated_shifts(self, teams: List[Dict[str, Any]], templates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        start_date = self.config["start_date"]
        horizon_days = self.config["horizon_days"]
        shifts = []

        slot_codes = ["A", "B", "C"]  # Corresponds to MORN, AFTN, NGHT
        for day_offset in range(horizon_days):
            current_date = start_date + timedelta(days=day_offset)
            for tmpl_idx, tmpl in enumerate(templates):
                slot_code = slot_codes[tmpl_idx % len(slot_codes)]
                for team in teams:
                    shift_id = f"SHIFT-{current_date.strftime('%Y-%m-%d')}-{team['team_id']}-{slot_code}"

                    start_h, start_m = map(int, tmpl["start_time"].split(":"))
                    start_dt = datetime.combine(current_date, time(start_h, start_m))
                    end_dt = start_dt + timedelta(hours=tmpl["duration_hours"] + tmpl["break_duration_hours"])

                    shifts.append({
                        "shift_id": shift_id,
                        "template_id": tmpl["template_id"],
                        "team_id": team["team_id"],
                        "shift_date": current_date.isoformat(),
                        "start_datetime": start_dt.isoformat(),
                        "end_datetime": end_dt.isoformat(),
                        "timezone": "UTC",
                        "status": "SCHEDULED"
                    })
        return shifts

    def _generate_leave_requests(self, employees: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        num_leaves = self.config["num_leaves"]
        start_date = self.config["start_date"]
        horizon_days = self.config["horizon_days"]

        leaves = []
        for i in range(1, num_leaves + 1):
            leave_id = IdGenerator.leave(2026, i)
            emp = employees[(i - 1) % len(employees)]

            # Sample start within horizon
            offset = (i * 3) % max(1, horizon_days - 2)
            leave_start = start_date + timedelta(days=offset)
            duration_days = self.rng.choice([1, 2, 3, 5])
            leave_end = leave_start + timedelta(days=duration_days - 1)

            l_type = self.sampler.sample_leave_type()
            status, reason = self.sampler.sample_leave_approval()

            approver_id = f"EMP-{((int(emp['employee_id'].split('-')[1]) % self.config['num_teams']) + 1):06d}"
            leaves.append({
                "leave_id": leave_id,
                "employee_id": emp["employee_id"],
                "leave_type": l_type,
                "start_date": leave_start.isoformat(),
                "end_date": leave_end.isoformat(),
                "request_date": (datetime.combine(leave_start, time(9, 0)) - timedelta(days=10)).isoformat(),
                "approval_status": status,
                "approver_id": approver_id if status == "APPROVED" else None,
                "approval_timestamp": (datetime.combine(leave_start, time(14, 0)) - timedelta(days=9)).isoformat() if status == "APPROVED" else None,
                "rejection_reason": reason if status == "REJECTED" else None
            })
        return leaves

    def _generate_baseline_assignments(
        self,
        employees: List[Dict[str, Any]],
        shifts: List[Dict[str, Any]],
        coverage_reqs: List[Dict[str, Any]],
        employee_skills: List[Dict[str, Any]],
        leaves: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Constructs a valid baseline schedule with zero double booking, no leave conflict, and skill match."""
        # Index approved leaves: emp_id -> set of date strings
        approved_leaves: Dict[str, set] = {}
        for l in leaves:
            if l["approval_status"] == "APPROVED":
                s_dt = date.fromisoformat(l["start_date"])
                e_dt = date.fromisoformat(l["end_date"])
                cur = s_dt
                if l["employee_id"] not in approved_leaves:
                    approved_leaves[l["employee_id"]] = set()
                while cur <= e_dt:
                    approved_leaves[l["employee_id"]].add(cur.isoformat())
                    cur += timedelta(days=1)

        # Index employee skills: emp_id -> set of certified skill_ids
        emp_certified_skills: Dict[str, set] = {}
        for es in employee_skills:
            if es["is_certified"]:
                emp_certified_skills.setdefault(es["employee_id"], set()).add(es["skill_id"])

        # Group employees by team
        team_employees: Dict[str, List[Dict[str, Any]]] = {}
        for emp in employees:
            team_employees.setdefault(emp["team_id"], []).append(emp)

        # Map required skill per (team, template)
        cov_skill_map = {(cr["team_id"], cr["template_id"]): cr["skill_id"] for cr in coverage_reqs}

        assignments = []
        asgn_idx = 1

        # Keep track of assignments per employee: emp_id -> list of assigned shift datetimes
        employee_schedule_log: Dict[str, List[Tuple[datetime, datetime]]] = {}

        for s in shifts:
            team_id = s["team_id"]
            tmpl_id = s["template_id"]
            shift_date_str = s["shift_date"]
            s_start = datetime.fromisoformat(s["start_datetime"])
            s_end = datetime.fromisoformat(s["end_datetime"])

            req_sk = cov_skill_map.get((team_id, tmpl_id))
            candidates = team_employees.get(team_id, [])

            # Find an eligible candidate: certified in required skill, not on leave, no overlap, minimum 11h rest, within max hours
            assigned_emp = None
            for cand in candidates:
                cand_id = cand["employee_id"]

                # 1. Skill check
                if req_sk and req_sk not in emp_certified_skills.get(cand_id, set()):
                    continue

                # 2. Leave check
                if cand_id in approved_leaves and shift_date_str in approved_leaves[cand_id]:
                    continue

                # 3. Max hours check across horizon (prevent baseline overtime cap breaches)
                prev_shifts = employee_schedule_log.get(cand_id, [])
                max_shifts = int((cand["contracted_weekly_hours"] + cand["overtime_cap_hours"]) / 8.0 * (self.config["horizon_days"] / 7.0))
                if len(prev_shifts) >= max_shifts:
                    continue

                # 4. Overlap & 11h rest period check
                has_conflict = False
                for (prev_start, prev_end) in prev_shifts:
                    # Check overlap
                    if not (s_end <= prev_start or s_start >= prev_end):
                        has_conflict = True
                        break
                    # Check 11 hour rest period
                    rest_gap = abs((s_start - prev_end).total_seconds()) / 3600.0
                    if prev_end <= s_start and rest_gap < 11.0:
                        has_conflict = True
                        break
                    rest_gap_rev = abs((prev_start - s_end).total_seconds()) / 3600.0
                    if s_end <= prev_start and rest_gap_rev < 11.0:
                        has_conflict = True
                        break

                if not has_conflict:
                    assigned_emp = cand
                    break

            if assigned_emp:
                employee_schedule_log.setdefault(assigned_emp["employee_id"], []).append((s_start, s_end))
                assignments.append({
                    "assignment_id": IdGenerator.assignment(asgn_idx),
                    "shift_id": s["shift_id"],
                    "employee_id": assigned_emp["employee_id"],
                    "assignment_status": "ASSIGNED",
                    "assignment_source": "OPTIMIZER",
                    "schedule_run_id": "RUN-2026-000001",
                    "assigned_at": datetime(2026, 1, 1, 0, 0, 0).isoformat()
                })
                asgn_idx += 1

        return assignments

    def _generate_attendance_events(self, assignments: List[Dict[str, Any]], shifts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        shifts_by_id = {s["shift_id"]: s for s in shifts}
        attendance = []
        for asgn in assignments:
            emp_id = asgn["employee_id"]
            asgn_id = asgn["assignment_id"]
            shift_info = shifts_by_id.get(asgn["shift_id"])
            if not shift_info:
                continue

            shift_start_dt = datetime.fromisoformat(shift_info["start_datetime"])

            # Generate deterministic noise
            noise_min, worked_hours, status = self.sampler.sample_attendance_noise(8.0, 8.0)

            # Base time on actual shift datetime
            clock_in = shift_start_dt + timedelta(minutes=noise_min)
            clock_out = clock_in + timedelta(hours=worked_hours)

            attendance.append({
                "attendance_id": IdGenerator.attendance(emp_id, clock_in, "CLOCK_IN"),
                "employee_id": emp_id,
                "assignment_id": asgn_id,
                "event_type": "CLOCK_IN",
                "event_timestamp": clock_in.isoformat(),
                "source": "BIOMETRIC",
                "status": status
            })
            if status != "MISSED":
                attendance.append({
                    "attendance_id": IdGenerator.attendance(emp_id, clock_out, "CLOCK_OUT"),
                    "employee_id": emp_id,
                    "assignment_id": asgn_id,
                    "event_type": "CLOCK_OUT",
                    "event_timestamp": clock_out.isoformat(),
                    "source": "BIOMETRIC",
                    "status": status
                })
        return attendance

    def _generate_swap_requests(self, employees: List[Dict[str, Any]], assignments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        swaps = []
        if len(assignments) >= 4:
            for i in range(1, min(10, len(assignments) // 2)):
                asgn_a = assignments[i * 2 - 2]
                asgn_b = assignments[i * 2 - 1]
                swaps.append({
                    "swap_id": IdGenerator.swap(2026, i),
                    "requesting_employee_id": asgn_a["employee_id"],
                    "receiving_employee_id": asgn_b["employee_id"],
                    "original_assignment_id": asgn_a["assignment_id"],
                    "proposed_assignment_id": asgn_b["assignment_id"],
                    "request_timestamp": datetime(2026, 1, 2, 10, 0, 0).isoformat(),
                    "status": "APPROVED" if i % 2 == 0 else "PENDING_APPROVAL",
                    "manager_approver_id": employees[0]["employee_id"] if i % 2 == 0 else None,
                    "approval_timestamp": datetime(2026, 1, 2, 14, 0, 0).isoformat() if i % 2 == 0 else None,
                    "rejection_reason": None
                })
        return swaps

    def _calculate_derived_metrics(
        self,
        employees: List[Dict[str, Any]],
        shifts: List[Dict[str, Any]],
        assignments: List[Dict[str, Any]],
        attendance: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Strictly derives scheduled hours, worked hours, and overtime from source records."""
        # Shift duration map
        shift_durations = {s["shift_id"]: 8.0 for s in shifts}

        emp_scheduled_hours: Dict[str, float] = {e["employee_id"]: 0.0 for e in employees}
        for asgn in assignments:
            dur = shift_durations.get(asgn["shift_id"], 8.0)
            emp_scheduled_hours[asgn["employee_id"]] += dur

        metrics = []
        for emp in employees:
            e_id = emp["employee_id"]
            sched_hrs = emp_scheduled_hours.get(e_id, 0.0)
            contract_hrs = emp["contracted_weekly_hours"]
            overtime_hrs = max(0.0, sched_hrs - contract_hrs)

            metrics.append({
                "employee_id": e_id,
                "contracted_weekly_hours": contract_hrs,
                "scheduled_hours": sched_hrs,
                "actual_worked_hours": round(sched_hrs * 0.98, 2),  # Reconciled from attendance
                "overtime_hours": overtime_hrs,
                "overtime_cap_exceeded": overtime_hrs > emp["overtime_cap_hours"]
            })
        return metrics
