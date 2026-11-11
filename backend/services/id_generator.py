"""Deterministic identifier generator adhering to Section 5 standards."""
from datetime import datetime, date

class IdGenerator:
    @staticmethod
    def employee(index: int) -> str:
        """Format: EMP-000001"""
        return f"EMP-{index:06d}"

    @staticmethod
    def team(index: int) -> str:
        """Format: TEAM-001"""
        return f"TEAM-{index:03d}"

    @staticmethod
    def skill(index: int) -> str:
        """Format: SKL-001"""
        return f"SKL-{index:03d}"

    @staticmethod
    def employee_skill(emp_index: int, skill_index: int) -> str:
        """Format: ESK-000001-001"""
        return f"ESK-{emp_index:06d}-{skill_index:03d}"

    @staticmethod
    def shift_template(code: str) -> str:
        """Format: TMPL-MORN, TMPL-AFTN, TMPL-NGHT"""
        return f"TMPL-{code.upper()}"

    @staticmethod
    def shift(shift_date: date, slot_letter: str) -> str:
        """Format: SHIFT-2026-01-01-A"""
        date_str = shift_date.strftime("%Y-%m-%d")
        return f"SHIFT-{date_str}-{slot_letter.upper()}"

    @staticmethod
    def assignment(index: int) -> str:
        """Format: ASGN-000001"""
        return f"ASGN-{index:06d}"

    @staticmethod
    def leave(year: int, index: int) -> str:
        """Format: LVE-2026-000001"""
        return f"LVE-{year}-{index:06d}"

    @staticmethod
    def attendance(employee_id: str, timestamp: datetime, event_type: str = "") -> str:
        """Format: ATT-<employee-id>-<timestamp>[-<event_type>]"""
        ts_str = timestamp.strftime("%Y%m%d%H%M%S")
        suffix = f"-{event_type.upper()[:2]}" if event_type else ""
        return f"ATT-{employee_id}-{ts_str}{suffix}"

    @staticmethod
    def swap(year: int, index: int) -> str:
        """Format: SWP-2026-000001"""
        return f"SWP-{year}-{index:06d}"

    @staticmethod
    def coverage(index: int) -> str:
        """Format: COV-{index:06d}"""
        return f"COV-{index:06d}"

    @staticmethod
    def schedule_run(year: int, index: int) -> str:
        """Format: RUN-{year}-{index:06d}"""
        return f"RUN-{year}-{index:06d}"

    @staticmethod
    def anomaly(index: int) -> str:
        """Format: ANOM-{index:06d}"""
        return f"ANOM-{index:06d}"

    @staticmethod
    def audit_log(timestamp: datetime, index: int) -> str:
        """Format: AUD-YYYYMMDD-000001"""
        dt_str = timestamp.strftime("%Y%m%d%H%M%S")
        import uuid
        uid = uuid.uuid4().hex[:6].upper()
        return f"AUD-{dt_str}-{index:04d}-{uid}"
