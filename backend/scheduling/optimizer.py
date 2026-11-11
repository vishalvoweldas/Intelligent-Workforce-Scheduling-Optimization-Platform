"""Constraint-based workforce scheduling optimization engine powered by Google OR-Tools CP-SAT."""
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set
from ortools.sat.python import cp_model

class ScheduleOptimizer:
    """Solves the multi-skill, multi-shift workforce scheduling problem using CP-SAT."""

    def __init__(
        self,
        employees: List[Dict[str, Any]],
        shifts: List[Dict[str, Any]],
        coverage_requirements: List[Dict[str, Any]],
        employee_skills: List[Dict[str, Any]],
        approved_leaves: List[Dict[str, Any]],
        weights: Optional[Dict[str, int]] = None,
        timeout_seconds: int = 30,
        seed: int = 20261022
    ):
        self.employees = employees
        self.shifts = shifts
        self.coverage_requirements = coverage_requirements
        self.employee_skills = employee_skills
        self.approved_leaves = approved_leaves
        self.timeout_seconds = timeout_seconds
        self.seed = seed

        # Default objective weights
        default_weights = {
            "unfilled_penalty": 10000,
            "overtime_penalty": 50,
            "fairness_weight": 20,
            "weekend_penalty": 15,
            "night_penalty": 15,
            "preference_reward": 5
        }
        self.weights = {**default_weights, **(weights or {})}

    def solve(self) -> Dict[str, Any]:
        """Formulates constraints and executes CP-SAT solver."""
        start_time = time.time()
        model = cp_model.CpModel()

        # Pre-process lookups
        # 1. Employee skill certification set: emp_id -> set of certified skill_ids
        emp_certs: Dict[str, Set[str]] = {}
        for es in self.employee_skills:
            if es.get("is_certified", False):
                emp_certs.setdefault(es["employee_id"], set()).add(es["skill_id"])

        # 2. Approved leave dates: emp_id -> set of ISO date strings
        emp_leaves: Dict[str, Set[str]] = {}
        for l in self.approved_leaves:
            if l.get("approval_status") == "APPROVED":
                cur = date.fromisoformat(l["start_date"])
                end = date.fromisoformat(l["end_date"])
                e_id = l["employee_id"]
                emp_leaves.setdefault(e_id, set())
                while cur <= end:
                    emp_leaves[e_id].add(cur.isoformat())
                    cur += timedelta(days=1)

        # 3. Coverage requirements mapping: (team_id, template_id) -> list of (skill_id, min_count)
        cov_map: Dict[Tuple[str, str], List[Tuple[str, int]]] = {}
        for cov in self.coverage_requirements:
            key = (cov["team_id"], cov["template_id"])
            cov_map.setdefault(key, []).append((cov["skill_id"], cov["min_employees"]))

        # Decision Variables: x[(emp_id, shift_id)] in {0, 1}
        x: Dict[Tuple[str, str], cp_model.IntVar] = {}
        # Unfilled slack variables: u[shift_id, skill_id] >= 0
        u: Dict[Tuple[str, str], cp_model.IntVar] = {}

        # Filter active employees and index by team
        active_emps = [e for e in self.employees if e.get("is_active", True) and e.get("employment_status") == "ACTIVE"]
        team_emps: Dict[str, List[Dict[str, Any]]] = {}
        for e in active_emps:
            team_emps.setdefault(e["team_id"], []).append(e)

        team_shifts: Dict[str, List[Dict[str, Any]]] = {}
        for s in self.shifts:
            team_shifts.setdefault(s["team_id"], []).append(s)

        # Parse shift datetime windows
        shift_windows = {}
        for s in self.shifts:
            s_start = datetime.fromisoformat(s["start_datetime"])
            s_end = datetime.fromisoformat(s["end_datetime"])
            shift_windows[s["shift_id"]] = (s_start, s_end, s["shift_date"], s["team_id"], s["template_id"])

        # Create variables: strictly scoped to matching team membership
        for t_id, t_emps in team_emps.items():
            t_shifts = team_shifts.get(t_id, [])
            for e in t_emps:
                e_id = e["employee_id"]
                for s in t_shifts:
                    s_id = s["shift_id"]
                    x[(e_id, s_id)] = model.NewBoolVar(f"x_{e_id}_{s_id}")

        # Slack variables for unfilled coverage
        for s in self.shifts:
            s_id = s["shift_id"]
            team_id = s["team_id"]
            tmpl_id = s["template_id"]
            reqs = cov_map.get((team_id, tmpl_id), [("GENERAL", 1)])
            for sk_id, min_cnt in reqs:
                u[(s_id, sk_id)] = model.NewIntVar(0, min_cnt, f"unfilled_{s_id}_{sk_id}")

        # ----------------------------------------------------
        # HARD CONSTRAINTS
        # ----------------------------------------------------

        # 1. Staffing / Coverage per shift and skill
        for s in self.shifts:
            s_id = s["shift_id"]
            team_id = s["team_id"]
            tmpl_id = s["template_id"]
            reqs = cov_map.get((team_id, tmpl_id), [("GENERAL", 1)])
            all_shift_eligible = set()
            total_req_count = 0

            for sk_id, min_cnt in reqs:
                total_req_count += min_cnt
                # Eligible employees: in same team and certified in skill (or if skill is GENERAL)
                eligible_emps = []
                for e in active_emps:
                    e_id = e["employee_id"]
                    # Team check: must belong to shift's team
                    if e["team_id"] != team_id:
                        continue
                    # Skill check
                    if sk_id != "GENERAL" and sk_id not in emp_certs.get(e_id, set()):
                        continue
                    eligible_emps.append(e_id)
                    all_shift_eligible.add(e_id)

                if eligible_emps:
                    model.Add(sum(x[(e_id, s_id)] for e_id in eligible_emps) + u[(s_id, sk_id)] == min_cnt)
                else:
                    # Infeasible for this skill - force slack to take deficit
                    model.Add(u[(s_id, sk_id)] == min_cnt)

            # Hard Constraint: Any employee not certified for this shift's requirements cannot be assigned
            for e in team_emps.get(team_id, []):
                e_id = e["employee_id"]
                if e_id not in all_shift_eligible and (e_id, s_id) in x:
                    model.Add(x[(e_id, s_id)] == 0)

            # Hard Constraint: Do not over-assign beyond required headcount for the shift
            if all_shift_eligible:
                model.Add(sum(x[(e_id, s_id)] for e_id in all_shift_eligible if (e_id, s_id) in x) <= total_req_count)

        # 2. Approved Leave Protection: x[e, s] = 0 if employee is on approved leave
        for e in active_emps:
            e_id = e["employee_id"]
            leaves = emp_leaves.get(e_id, set())
            if leaves:
                t_shifts = team_shifts.get(e["team_id"], [])
                for s in t_shifts:
                    if s["shift_date"] in leaves and (e_id, s["shift_id"]) in x:
                        model.Add(x[(e_id, s["shift_id"])] == 0)

        # 3. No Overlapping Shifts (Double Booking Prevention within team)
        for t_id, t_shift_list in team_shifts.items():
            t_emps = team_emps.get(t_id, [])
            if not t_emps:
                continue
            for i in range(len(t_shift_list)):
                s1 = t_shift_list[i]
                w1_start, w1_end, _, _, _ = shift_windows[s1["shift_id"]]
                for j in range(i + 1, len(t_shift_list)):
                    s2 = t_shift_list[j]
                    w2_start, w2_end, _, _, _ = shift_windows[s2["shift_id"]]
                    if max(w1_start, w2_start) < min(w1_end, w2_end):
                        for e in t_emps:
                            e_id = e["employee_id"]
                            model.Add(x[(e_id, s1["shift_id"])] + x[(e_id, s2["shift_id"])] <= 1)

        # 4. Minimum Rest Periods (11 Hours Rest between consecutive shifts within team)
        min_rest_seconds = 11.0 * 3600.0
        for t_id, t_shift_list in team_shifts.items():
            t_emps = team_emps.get(t_id, [])
            if not t_emps:
                continue
            # Sort shifts chronologically
            sorted_t_shifts = sorted(t_shift_list, key=lambda s: shift_windows[s["shift_id"]][0])
            for i in range(len(sorted_t_shifts)):
                s1 = sorted_t_shifts[i]
                w1_start, w1_end, _, _, _ = shift_windows[s1["shift_id"]]
                for j in range(i + 1, len(sorted_t_shifts)):
                    s2 = sorted_t_shifts[j]
                    w2_start, w2_end, _, _, _ = shift_windows[s2["shift_id"]]
                    if (w2_start - w1_end).total_seconds() > 24.0 * 3600.0:
                        break
                    if w2_start > w1_end and (w2_start - w1_end).total_seconds() < min_rest_seconds:
                        for e in t_emps:
                            e_id = e["employee_id"]
                            model.Add(x[(e_id, s1["shift_id"])] + x[(e_id, s2["shift_id"])] <= 1)

        # 5. Maximum Working Hours & Overtime Limit (Rolling 7-day window adhering to BR-01)
        shift_dates = sorted(list({date.fromisoformat(s["shift_date"]) for s in self.shifts}))
        for e in active_emps:
            e_id = e["employee_id"]
            max_hours = int(e.get("max_working_hours", 48.0))
            shift_duration_int = 8
            t_shifts = team_shifts.get(e["team_id"], [])
            if shift_dates:
                start_d = shift_dates[0]
                end_d = shift_dates[-1]
                cur_d = start_d
                while cur_d <= end_d:
                    window_end = cur_d + timedelta(days=6)
                    window_shifts = [
                        s["shift_id"] for s in t_shifts
                        if cur_d <= date.fromisoformat(s["shift_date"]) <= window_end
                        and (e_id, s["shift_id"]) in x
                    ]
                    if window_shifts:
                        model.Add(sum(x[(e_id, s_id)] * shift_duration_int for s_id in window_shifts) <= max_hours)
                    cur_d += timedelta(days=1)
            else:
                window_shifts = [s["shift_id"] for s in t_shifts if (e_id, s["shift_id"]) in x]
                if window_shifts:
                    model.Add(sum(x[(e_id, s_id)] * shift_duration_int for s_id in window_shifts) <= max_hours)

        # 6. Team Membership Eligibility: Strictly enforced by variable scoping

        # ----------------------------------------------------
        # OBJECTIVE FUNCTION (Multi-Objective Weighted Optimization)
        # ----------------------------------------------------
        objective_terms = []

        # A. Heavily penalize unfilled shifts (ensure coverage priority)
        unfilled_penalty = self.weights["unfilled_penalty"]
        for key, slack_var in u.items():
            objective_terms.append(slack_var * unfilled_penalty)

        # B. Soft: Workload equity (penalize extreme variance from target shifts)
        target_shifts_per_emp = max(1, len(self.shifts) // max(1, len(active_emps)))
        fairness_weight = self.weights["fairness_weight"]
        for e in active_emps:
            e_id = e["employee_id"]
            t_shifts = team_shifts.get(e["team_id"], [])
            emp_vars = [x[(e_id, s["shift_id"])] for s in t_shifts if (e_id, s["shift_id"]) in x]
            if emp_vars:
                emp_total_shifts = sum(emp_vars)
                dev = model.NewIntVar(0, len(t_shifts), f"dev_{e_id}")
                model.Add(dev >= emp_total_shifts - target_shifts_per_emp)
                model.Add(dev >= target_shifts_per_emp - emp_total_shifts)
                objective_terms.append(dev * fairness_weight)

        # Minimize combined objective
        model.Minimize(sum(objective_terms))

        # ----------------------------------------------------
        # SOLVER EXECUTION
        # ----------------------------------------------------
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = float(self.timeout_seconds)
        solver.parameters.random_seed = int(self.seed)
        solver.parameters.num_workers = 8

        status_code = solver.Solve(model)
        elapsed_time = round(time.time() - start_time, 3)

        status_mapping = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.MODEL_INVALID: "FAILED",
            cp_model.UNKNOWN: "TIME_LIMIT_WITH_FEASIBLE_SOLUTION" if solver.ResponseStats() else "FAILED"
        }
        final_status = status_mapping.get(status_code, "FAILED")

        # Collect results
        assigned_records = []
        gaps = []
        assigned_count = 0
        unfilled_count = 0

        if final_status in ("OPTIMAL", "FEASIBLE"):
            for s in self.shifts:
                s_id = s["shift_id"]
                shift_filled = False
                for e in team_emps.get(s["team_id"], []):
                    e_id = e["employee_id"]
                    if (e_id, s_id) in x and solver.Value(x[(e_id, s_id)]) == 1:
                        assigned_count += 1
                        shift_filled = True
                        assigned_records.append({
                            "shift_id": s_id,
                            "employee_id": e_id,
                            "assignment_source": "OPTIMIZER",
                            "assignment_status": "ASSIGNED"
                        })
                # Check for slack unfilled
                team_id = s["team_id"]
                tmpl_id = s["template_id"]
                reqs = cov_map.get((team_id, tmpl_id), [("GENERAL", 1)])
                for sk_id, min_cnt in reqs:
                    slack_val = solver.Value(u[(s_id, sk_id)])
                    if slack_val > 0:
                        unfilled_count += slack_val
                        gaps.append({
                            "shift_id": s_id,
                            "skill_id": sk_id,
                            "shortage_count": slack_val,
                            "reason": f"Insufficient certified employees available in team {team_id} (conflicts with leaves/rest constraints)"
                        })
        else:
            # Report all requirements as uncovered gaps with diagnostic reasons
            for s in self.shifts:
                s_id = s["shift_id"]
                team_id = s["team_id"]
                tmpl_id = s["template_id"]
                reqs = cov_map.get((team_id, tmpl_id), [("GENERAL", 1)])
                for sk_id, min_cnt in reqs:
                    unfilled_count += min_cnt
                    gaps.append({
                        "shift_id": s_id,
                        "skill_id": sk_id,
                        "shortage_count": min_cnt,
                        "reason": "Solver proved no feasible assignment satisfies all hard labor constraints"
                    })

        total_shifts = len(self.shifts)
        coverage_rate = round(assigned_count / max(1, total_shifts), 4)

        return {
            "status": final_status,
            "objective_value": solver.ObjectiveValue() if final_status in ("OPTIMAL", "FEASIBLE") else None,
            "runtime_seconds": elapsed_time,
            "total_shifts": total_shifts,
            "assigned_shifts": assigned_count,
            "unfilled_shifts": unfilled_count,
            "coverage_rate": coverage_rate,
            "assignments": assigned_records,
            "gaps": gaps,
            "weights": self.weights,
            "solver_info": {
                "name": "Google OR-Tools CP-SAT",
                "wall_time": solver.WallTime(),
                "branches": solver.NumBranches(),
                "conflicts": solver.NumConflicts()
            }
        }

