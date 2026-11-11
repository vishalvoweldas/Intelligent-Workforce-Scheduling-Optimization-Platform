import {
  Employee, Team, Skill, ShiftTemplate, Shift, LeaveRequest, SwapRequest,
  AttendanceReconItem, OvertimeSummaryItem, CoverageAnalyticsData, FairnessAnalyticsData,
  EvaluationResult, Role, DemoUsersResponse, DatasetProfilesResponse, ActiveProfileInfo
} from './types';

const API_BASE = '/api/v1';

let activeUserId: string = 'EMP-000014';
let activeRole: Role = 'EMPLOYEE';

export const setAuthContext = (userId: string, role: Role) => {
  activeUserId = userId;
  activeRole = role;
};

export const getAuthContext = () => ({
  userId: activeUserId,
  role: activeRole
});

const getHeaders = (extraHeaders: Record<string, string> = {}) => ({
  'Content-Type': 'application/json',
  'X-User-Id': activeUserId,
  'X-Role': activeRole,
  'Authorization': `Bearer jwt_token_for_${activeUserId}`,
  ...extraHeaders
});

export const api = {
  // Auth & Identity
  async getDemoUsers(): Promise<DemoUsersResponse> {
    const res = await fetch(`${API_BASE}/auth/demo-users`, { headers: getHeaders() });
    return res.json();
  },
  async getCurrentUser(): Promise<any> {
    const res = await fetch(`${API_BASE}/auth/me`, { headers: getHeaders() });
    return res.json();
  },

  // Workforce
  async getEmployees(teamId?: string): Promise<{ total: number; items: Employee[] }> {
    const url = teamId ? `${API_BASE}/workforce/employees?team_id=${teamId}` : `${API_BASE}/workforce/employees?limit=200`;
    const res = await fetch(url, { headers: getHeaders() });
    return res.json();
  },
  async getTeams(): Promise<Team[]> {
    const res = await fetch(`${API_BASE}/workforce/teams`, { headers: getHeaders() });
    return res.json();
  },
  async getSkills(): Promise<Skill[]> {
    const res = await fetch(`${API_BASE}/workforce/skills`, { headers: getHeaders() });
    return res.json();
  },

  // Shifts
  async getShiftTemplates(): Promise<ShiftTemplate[]> {
    const res = await fetch(`${API_BASE}/shifts/templates`, { headers: getHeaders() });
    return res.json();
  },
  async getShifts(teamId?: string): Promise<{ total: number; items: Shift[] }> {
    const url = teamId ? `${API_BASE}/shifts?team_id=${teamId}` : `${API_BASE}/shifts?limit=200`;
    const res = await fetch(url, { headers: getHeaders() });
    return res.json();
  },

  // Schedules / Optimizer
  async getMySchedule(): Promise<any> {
    const res = await fetch(`${API_BASE}/schedules/my`, { headers: getHeaders() });
    return res.json();
  },
  async runOptimizer(payload: { team_id?: string; start_date: string; end_date: string; timeout_seconds?: number; seed?: number }): Promise<any> {
    const res = await fetch(`${API_BASE}/schedules/run`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(payload)
    });
    return res.json();
  },
  async publishSchedule(scheduleRunId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/schedules/publish`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ schedule_run_id: scheduleRunId })
    });
    return res.json();
  },
  async getScheduleRuns(): Promise<any[]> {
    const res = await fetch(`${API_BASE}/schedules/runs`, { headers: getHeaders() });
    return res.json();
  },

  // Leave Management
  async getLeaveRequests(status?: string): Promise<{ total: number; items: LeaveRequest[] }> {
    const url = status && status !== 'ALL' ? `${API_BASE}/leave-requests?status_filter=${status}` : `${API_BASE}/leave-requests?limit=100`;
    const res = await fetch(url, { headers: getHeaders() });
    return res.json();
  },
  async submitLeaveRequest(payload: { employee_id: string; leave_type: string; start_date: string; end_date: string; comments?: string }): Promise<any> {
    const res = await fetch(`${API_BASE}/leave-requests`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(payload)
    });
    return res.json();
  },
  async decideLeaveRequest(leaveId: string, decision: 'APPROVED' | 'REJECTED', comments?: string): Promise<any> {
    const res = await fetch(`${API_BASE}/leave-requests/${leaveId}/decide`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ decision, comments })
    });
    return res.json();
  },

  // Shift Swaps
  async getSwapRequests(statusFilter?: string): Promise<SwapRequest[]> {
    const url = statusFilter && statusFilter !== 'ALL' ? `${API_BASE}/swaps?status_filter=${statusFilter}&limit=50` : `${API_BASE}/swaps?limit=50`;
    const res = await fetch(url, { headers: getHeaders() });
    return res.json();
  },
  async submitSwapRequest(payload: { requesting_employee_id: string; receiving_employee_id: string; original_assignment_id: string; proposed_assignment_id: string; reason?: string }): Promise<any> {
    const res = await fetch(`${API_BASE}/swaps`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(payload)
    });
    return res.json();
  },
  async peerAcceptSwap(swapId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/swaps/${swapId}/accept`, {
      method: 'POST',
      headers: getHeaders()
    });
    return res.json();
  },
  async peerDecideSwap(swapId: string, decision: 'ACCEPTED' | 'REJECTED', comments?: string): Promise<any> {
    const res = await fetch(`${API_BASE}/swaps/${swapId}/peer-decide`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ decision, comments })
    });
    return res.json();
  },
  async decideSwapRequest(swapId: string, decision: 'APPROVED' | 'REJECTED', rejectionReason?: string): Promise<any> {
    const res = await fetch(`${API_BASE}/swaps/${swapId}/decide`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ decision, rejection_reason: rejectionReason })
    });
    return res.json();
  },

  // Attendance & Overtime
  async getAttendanceEvents(employeeId?: string): Promise<any[]> {
    const url = employeeId ? `${API_BASE}/attendance/events?employee_id=${employeeId}` : `${API_BASE}/attendance/events?limit=100`;
    const res = await fetch(url, { headers: getHeaders() });
    return res.json();
  },
  async recordAttendance(payload: { employee_id: string; assignment_id?: string; event_type: 'CLOCK_IN' | 'CLOCK_OUT'; source?: string }): Promise<any> {
    const res = await fetch(`${API_BASE}/attendance/events`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(payload)
    });
    return res.json();
  },
  async getAttendanceReconciliation(teamId?: string): Promise<{ reconciliation: AttendanceReconItem[]; employee_overtime_summary: OvertimeSummaryItem[] }> {
    const url = teamId ? `${API_BASE}/attendance/reconciliation?team_id=${teamId}` : `${API_BASE}/attendance/reconciliation`;
    const res = await fetch(url, { headers: getHeaders() });
    return res.json();
  },

  // Analytics
  async getCoverageAnalytics(): Promise<CoverageAnalyticsData> {
    const res = await fetch(`${API_BASE}/analytics/coverage`, { headers: getHeaders() });
    return res.json();
  },
  async getFairnessAnalytics(): Promise<FairnessAnalyticsData> {
    const res = await fetch(`${API_BASE}/analytics/fairness`, { headers: getHeaders() });
    return res.json();
  },
  async getReports(): Promise<Record<string, string>> {
    const res = await fetch(`${API_BASE}/analytics/reports`, { headers: getHeaders() });
    return res.json();
  },

  // Datasets
  async getDatasetProfiles(): Promise<DatasetProfilesResponse> {
    const res = await fetch(`${API_BASE}/datasets/profiles`, { headers: getHeaders() });
    return res.json();
  },
  async getActiveProfile(): Promise<ActiveProfileInfo> {
    const res = await fetch(`${API_BASE}/datasets/active-profile`, { headers: getHeaders() });
    return res.json();
  },
  async switchDatasetProfile(profile: 'STARTER' | 'FULL'): Promise<any> {
    const res = await fetch(`${API_BASE}/datasets/switch-profile`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ profile })
    });
    return res.json();
  },
  async generateDataset(profile: 'STARTER' | 'FULL', seed: number = 20261022): Promise<any> {
    const res = await fetch(`${API_BASE}/datasets/generate`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ profile, seed, inject_anomalies: true })
    });
    return res.json();
  },
  async verifyReproducibility(profile: string = 'STARTER', seed: number = 20261022): Promise<any> {
    const res = await fetch(`${API_BASE}/datasets/reproducibility?profile=${profile}&seed=${seed}`, { headers: getHeaders() });
    return res.json();
  },

  // Evaluation
  async runEvaluation(): Promise<EvaluationResult> {
    const res = await fetch(`${API_BASE}/evaluations/run`, {
      method: 'POST',
      headers: getHeaders()
    });
    return res.json();
  }
};
