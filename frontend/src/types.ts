export type Role = 'EMPLOYEE' | 'MANAGER' | 'HR_PARTNER' | 'OPERATIONS' | 'ADMIN';

export interface DemoUser {
  employee_id: string;
  name: string;
  email: string;
  role: Role;
  team_id: string;
}

export interface DemoUsersResponse {
  total: number;
  managers: DemoUser[];
  employees: DemoUser[];
  hr_partners: DemoUser[];
  operations: DemoUser[];
  admins: DemoUser[];
}

export interface Employee {
  employee_id: string;
  first_name: string;
  last_name: string;
  name: string;
  email: string;
  team_id: string;
  role: Role;
  employment_type: string;
  employment_status: string;
  contracted_weekly_hours: number;
  max_working_hours: number;
  overtime_cap_hours: number;
  work_zone: string;
  is_active: boolean;
}

export interface Team {
  team_id: string;
  team_name: string;
  department: string;
  location: string;
  manager_id: string | null;
  is_active: boolean;
}

export interface Skill {
  skill_id: string;
  skill_name: string;
  category: string;
  description: string;
  is_active: boolean;
}

export interface ShiftTemplate {
  template_id: string;
  template_name: string;
  start_time: string;
  end_time: string;
  break_duration_hours: number;
  category: string;
  duration_hours: number;
  is_overnight: boolean;
  applicable_days: string;
}

export interface ShiftAssignment {
  assignment_id: string;
  employee_id: string;
  employee_name: string;
  status: string;
  source: string;
}

export interface Shift {
  shift_id: string;
  template_id: string;
  team_id: string;
  shift_date: string;
  start_datetime: string;
  end_datetime: string;
  status: string;
  assignments: ShiftAssignment[];
}

export interface LeaveRequest {
  leave_id: string;
  employee_id: string;
  employee_name: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  request_date: string;
  approval_status: 'SUBMITTED' | 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
  approver_id: string | null;
  rejection_reason: string | null;
}

export interface SwapRequest {
  swap_id: string;
  requesting_employee_id: string;
  requesting_employee_name?: string;
  receiving_employee_id: string;
  receiving_employee_name?: string;
  original_assignment_id: string;
  original_shift_info?: string;
  proposed_assignment_id: string;
  proposed_shift_info?: string;
  request_timestamp: string;
  status: string;
  manager_approver_id: string | null;
  rejection_reason: string | null;
}

export interface AttendanceReconItem {
  assignment_id: string;
  employee_id: string;
  employee_name: string;
  shift_id: string;
  shift_date: string;
  scheduled_hours: number;
  actual_worked_hours: number;
  status: string;
  clock_in: string | null;
  clock_out: string | null;
}

export interface OvertimeSummaryItem {
  employee_id: string;
  employee_name: string;
  contracted_hours: number;
  total_worked_hours: number;
  regular_hours: number;
  overtime_hours: number;
  overtime_cap: number;
  cap_exceeded: boolean;
}

export interface CoverageAnalyticsData {
  total_required_shifts: number;
  filled_shifts: number;
  unfilled_shifts: number;
  overall_coverage_rate: number;
  team_breakdown: Array<{
    team_id: string;
    required_shifts: number;
    filled_shifts: number;
    coverage_rate: number;
  }>;
}

export interface FairnessAnalyticsData {
  mean_scheduled_hours: number;
  stdev_scheduled_hours: number;
  gini_inequality_coefficient: number;
  weekend_shift_stdev: number;
  night_shift_stdev: number;
  employee_breakdown: Array<{
    employee_id: string;
    name: string;
    team_id: string;
    contracted_hours: number;
    scheduled_hours: number;
    weekend_shifts: number;
    night_shifts: number;
  }>;
}

export interface ConfusionMatrix {
  true_positives: number;
  false_positives: number;
  true_negatives: number;
  false_negatives: number;
}

export interface CategoryMetric {
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  precision: number;
  recall: number;
  f1_score: number;
}

export interface EvaluationResult {
  evaluation_id: string;
  confusion_matrix: ConfusionMatrix;
  overall_metrics: {
    precision: number;
    recall: number;
    f1_score: number;
  };
  by_category: Record<string, CategoryMetric>;
  detected_anomalies: any[];
}

export interface DatasetProfileItem {
  id: 'STARTER' | 'FULL';
  name: string;
  badge_label: string;
  employees_count: number;
  teams_count: number;
  horizon_days: number;
  start_date: string;
  end_date: string;
  leaves_count: number;
  is_active: boolean;
  is_generated: boolean;
  counts?: Record<string, number>;
}

export interface DatasetProfilesResponse {
  active_profile: 'STARTER' | 'FULL';
  profiles: DatasetProfileItem[];
}

export interface ActiveProfileInfo {
  profile: 'STARTER' | 'FULL';
  name: string;
  badge_label: string;
  horizon_days: number;
  start_date: string;
  end_date: string;
  is_active: boolean;
  counts: Record<string, number>;
}
