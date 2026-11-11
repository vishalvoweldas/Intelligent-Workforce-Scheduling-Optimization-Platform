"""Fairness analytics computing hours deviation, Gini coefficient, and weekend/night rotation equity."""
import numpy as np
from typing import Dict, Any, List

class FairnessAnalytics:
    """Calculates multi-dimensional workforce scheduling fairness metrics."""

    @staticmethod
    def calculate_fairness(
        employees: List[Dict[str, Any]],
        shifts: List[Dict[str, Any]],
        assignments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        shifts_by_id = {s["shift_id"]: s for s in shifts}

        emp_hours: Dict[str, float] = {e["employee_id"]: 0.0 for e in employees}
        emp_weekends: Dict[str, int] = {e["employee_id"]: 0 for e in employees}
        emp_nights: Dict[str, int] = {e["employee_id"]: 0 for e in employees}

        for asgn in assignments:
            emp_id = asgn["employee_id"]
            s = shifts_by_id.get(asgn["shift_id"])
            if not s:
                continue

            emp_hours[emp_id] = emp_hours.get(emp_id, 0.0) + 8.0

            # Check if weekend (Saturday=5, Sunday=6)
            s_date = s["shift_date"]
            from datetime import date
            dt = date.fromisoformat(s_date)
            if dt.weekday() in (5, 6):
                emp_weekends[emp_id] = emp_weekends.get(emp_id, 0) + 1

            # Check if night shift
            if "NGHT" in s["template_id"] or "NIGHT" in s.get("category", ""):
                emp_nights[emp_id] = emp_nights.get(emp_id, 0) + 1

        hours_array = np.array(list(emp_hours.values()), dtype=float)
        mean_hours = float(np.mean(hours_array)) if len(hours_array) > 0 else 0.0
        stdev_hours = float(np.std(hours_array)) if len(hours_array) > 0 else 0.0

        # Gini Coefficient calculation
        gini = FairnessAnalytics._calculate_gini(hours_array)

        # Weekend and Night rotation standard deviations
        weekend_stdev = float(np.std(list(emp_weekends.values()))) if emp_weekends else 0.0
        night_stdev = float(np.std(list(emp_nights.values()))) if emp_nights else 0.0

        return {
            "mean_scheduled_hours": round(mean_hours, 2),
            "stdev_scheduled_hours": round(stdev_hours, 2),
            "gini_inequality_coefficient": round(gini, 4),
            "weekend_shift_stdev": round(weekend_stdev, 2),
            "night_shift_stdev": round(night_stdev, 2),
            "employee_breakdown": [
                {
                    "employee_id": e["employee_id"],
                    "name": f"{e['first_name']} {e['last_name']}",
                    "team_id": e["team_id"],
                    "contracted_hours": e.get("contracted_weekly_hours", 40.0),
                    "scheduled_hours": emp_hours.get(e["employee_id"], 0.0),
                    "weekend_shifts": emp_weekends.get(e["employee_id"], 0),
                    "night_shifts": emp_nights.get(e["employee_id"], 0)
                }
                for e in employees
            ]
        }

    @staticmethod
    def _calculate_gini(array: np.ndarray) -> float:
        """Computes the Gini coefficient of inequality for an array of values."""
        if len(array) == 0:
            return 0.0
        array = array.flatten()
        if np.amin(array) < 0:
            array -= np.amin(array)
        array += 0.0000001 # Values cannot be all 0
        array = np.sort(array)
        index = np.arange(1, array.shape[0] + 1)
        n = array.shape[0]
        return float(((np.sum((2 * index - n - 1) * array)) / (n * np.sum(array))))

