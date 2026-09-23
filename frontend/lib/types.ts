export type Locale = "en" | "ru";

export interface AuthUser {
  id: number;
  username: string;
  role: "employee" | "hr" | "admin";
  employee_id: string | null;
  display_name: string;
}

export interface EmployeeSummary {
  employee_id: string;
  display_name: string;
  role: string;
  grade: string;
  tenure_months: number;
  organisation_unit: string;
}

export interface Skill {
  code: string;
  name: string;
  kind: "hard" | "soft";
  level: number;
}

export interface SkillGap {
  skill_code: string;
  skill_name: string;
  kind: string;
  current_level: number;
  required_level: number;
  gap: number;
  priority: number;
}

export interface Trajectory {
  current_grade: { code: string; name: string; rank: number };
  target_grade: { code: string; name: string; rank: number } | null;
  readiness_percent: number;
  gaps: SkillGap[];
  is_top_grade: boolean;
}

export interface EmployeeProfile extends Omit<EmployeeSummary, "role" | "grade"> {
  role: { code: string; name: string };
  grade: { code: string; name: string };
  skills: Skill[];
  activities: Array<{
    id: string;
    event_code: string;
    event_name: string;
    status: string;
    occurred_at: string;
    completed_on_time: boolean | null;
  }>;
  trajectory: Trajectory;
}

export interface Recommendation {
  id: string;
  rank: number;
  score: number;
  event: {
    code: string;
    name: string;
    description: string;
    type: string;
    format: string;
    duration_hours: number;
  };
  impacted_skills: Array<{
    skill_code: string;
    skill_name: string;
    current_level: number;
    required_level: number;
    gain: number;
    max_level: number;
    priority: number;
  }>;
  explanation: {
    summary: string;
    reasons: Array<{ factor: string; message: string }>;
    score_breakdown: Record<string, number>;
    engine: string;
  };
}

export interface RecommendationExplanation {
  recommendations: Array<{
    event_id: string;
    rank: number;
    title: string;
    headline: string;
    why_recommended: string;
    expected_impact: string;
    history_context: string | null;
    next_step: string;
  }>;
  overall_summary: string;
}

export interface HRDashboard {
  summary: { employees: number; completion_rate: number; employees_without_step: number };
  top_skill_gaps: Array<{ skill_code: string; skill_name: string; employees: number }>;
  employees_without_step: Array<{ employee_id: string; display_name: string }>;
  participation: Array<{
    event_code: string;
    event_name: string;
    total: number;
    completed: number;
    missed: number;
    declined: number;
    completion_rate: number;
  }>;
}
