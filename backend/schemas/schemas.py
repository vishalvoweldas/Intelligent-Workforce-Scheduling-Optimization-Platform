"""Pydantic v2 Request & Response Data Schemas."""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    email: str
    role: str
    team_id: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user: UserResponse

class EmployeeCreate(BaseModel):
    team_id: str
    first_name: str
    last_name: str
    email: str
    role: str = "EMPLOYEE"
    employment_type: str = "FULL_TIME"
    contracted_weekly_hours: float = 40.0
    max_working_hours: float = 48.0
    overtime_cap_hours: float = 8.0

class ScheduleRunRequest(BaseModel):
    team_id: Optional[str] = None
    start_date: str = "2026-01-01"
    end_date: str = "2026-01-14"
    weights: Optional[Dict[str, int]] = None
    timeout_seconds: int = 30
    seed: int = 20261022

class LeaveSubmitRequest(BaseModel):
    employee_id: str
    leave_type: str = "ANNUAL"
    start_date: str
    end_date: str
    comments: Optional[str] = None

class LeaveDecisionRequest(BaseModel):
    decision: str  # APPROVED or REJECTED
    comments: Optional[str] = None
    approver_id: Optional[str] = None

class SwapSubmitRequest(BaseModel):
    requesting_employee_id: str
    receiving_employee_id: str
    original_assignment_id: str
    proposed_assignment_id: str
    reason: Optional[str] = None

class SwapPeerDecisionRequest(BaseModel):
    decision: str  # ACCEPTED or REJECTED
    comments: Optional[str] = None

class SwapDecisionRequest(BaseModel):
    decision: str  # APPROVED or REJECTED
    rejection_reason: Optional[str] = None
    approver_id: Optional[str] = None

class AttendanceEventCreate(BaseModel):
    employee_id: str
    assignment_id: Optional[str] = None
    event_type: str  # CLOCK_IN or CLOCK_OUT
    event_timestamp: Optional[str] = None
    source: str = "BIOMETRIC"

class DatasetGenerateRequest(BaseModel):
    profile: str = "STARTER"  # STARTER or FULL
    seed: int = 20261022
    inject_anomalies: bool = True

class SwitchProfileRequest(BaseModel):
    profile: str = "STARTER"  # STARTER or FULL
