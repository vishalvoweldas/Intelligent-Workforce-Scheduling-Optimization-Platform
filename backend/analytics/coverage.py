"""Coverage analytics measuring filled vs unfilled staffing requirements."""
from typing import Dict, Any, List

class CoverageAnalytics:
    """Computes coverage percentages, team-level fill rates, and gap summaries."""

    @staticmethod
    def calculate_coverage(
        shifts: List[Dict[str, Any]],
        assignments: List[Dict[str, Any]],
        coverage_requirements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        asgn_by_shift: Dict[str, List[Dict[str, Any]]] = {}
        for a in assignments:
            asgn_by_shift.setdefault(a["shift_id"], []).append(a)

        total_shifts = len(shifts)
        filled_shifts = sum(1 for s in shifts if len(asgn_by_shift.get(s["shift_id"], [])) > 0)
        unfilled_shifts = total_shifts - filled_shifts
        overall_fill_rate = round(filled_shifts / max(1, total_shifts), 4)

        # Team level coverage
        team_coverage: Dict[str, Dict[str, int]] = {}
        for s in shifts:
            t_id = s["team_id"]
            if t_id not in team_coverage:
                team_coverage[t_id] = {"required": 0, "filled": 0}
            team_coverage[t_id]["required"] += 1
            if len(asgn_by_shift.get(s["shift_id"], [])) > 0:
                team_coverage[t_id]["filled"] += 1

        team_breakdown = [
            {
                "team_id": t_id,
                "required_shifts": stats["required"],
                "filled_shifts": stats["filled"],
                "coverage_rate": round(stats["filled"] / max(1, stats["required"]), 4)
            }
            for t_id, stats in team_coverage.items()
        ]

        return {
            "total_required_shifts": total_shifts,
            "filled_shifts": filled_shifts,
            "unfilled_shifts": unfilled_shifts,
            "overall_coverage_rate": overall_fill_rate,
            "team_breakdown": team_breakdown
        }

