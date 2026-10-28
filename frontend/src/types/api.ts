export interface Health {
  status: string;
  version: string;
  disclaimer: string;
}

export interface Exercise {
  id: string;
  name: string;
  target_joints: string[];
  landmarks: string[]; // [A, B, C]; angle is measured at B
  common_errors: string[];
  start_angle_deg: number;
  target_angle_deg: number;
  difficulty_levels: Record<string, { target_reps: number; range_fraction: number; min_rep_duration_s: number }>;
  illustrative_only: boolean;
}

export interface User {
  id: string;
  username: string;
  age_range: string | null;
  goals: string | null;
  preferences: Record<string, boolean>;
  created_at: string;
}

export interface SessionCreated {
  id: string;
  exercise_id: string;
  is_demo: boolean;
  difficulty: number;
  ws_key: string;
}

export interface SessionMetrics {
  n_reps: number;
  n_reliable: number;
  counted_reps: number;
  target_reps: number;
  quality: number | null;
  error_rate: number | null;
  completion: number;
  range_std: number | null;
  reliable_fraction: number;
}

export interface Recommendation {
  action: "increase" | "decrease" | "maintain" | "pause" | "reset";
  current_level: number;
  next_level: number;
  target_reps: number;
  range_fraction: number;
  min_rep_duration_s: number;
  feedback_intensity: string;
  classification: string;
  reasons: string[];
  metrics: SessionMetrics;
  safety_note: string;
}

export interface CompleteOut {
  recommendation: Recommendation;
  history_used: boolean;
  saved_to_history: boolean;
}

export interface AdaptationState {
  exercise_id: string;
  recommended_level: number;
  source: "history" | "default";
  last_action: string | null;
  last_reasons: string[];
  last_at: string | null;
}

export interface ProgressPoint {
  session_id: string;
  exercise_id: string;
  started_at: string;
  is_demo: boolean;
  level: number;
  counted_reps: number | null;
  target_reps: number | null;
  quality: number | null;
  error_rate: number | null;
  duration_s: number;
  mean_rom_deg: number | null;
  classification: string | null;
  action: string | null;
  next_level: number | null;
}

export interface AnalyticsSummary {
  total_sessions: number;
  demo_sessions_included: boolean;
  completed_repetitions: number;
  average_quality_score: number | null;
  total_duration_s: number;
  error_categories: Record<string, number>;
  sessions_by_exercise: Record<string, number>;
  note: string;
  disclaimer: string;
}

export interface Filters {
  exercise_id?: string;
  from?: string;
  to?: string;
  include_demo?: boolean;
}

export interface RepDetail {
  index: number;
  label: string | null;
  score: number | null;
  counted: boolean;
  reliable: boolean;
  range_of_motion_deg: number | null;
  duration_s: number | null;
}

export interface WeeklySummary {
  sessions_last_7_days: number;
  counted_repetitions_last_7_days: number;
  day_streak: number;
  active_days_last_7: number;
  note: string;
}

export interface SessionDetail {
  pain?: number | null;
  note?: string | null;
  id: string;
  exercise_id: string;
  is_demo: boolean;
  difficulty: number;
  started_at: string;
  ended_at: string | null;
  summary: { metrics?: SessionMetrics; classification?: string; action?: string; next_level?: number };
  repetitions: RepDetail[];
  decision: { action: string; from_level: number; to_level: number; classification: string; reasons: string[] } | null;
}

export interface ResearchResult {
  id: string;
  kind: "external" | "lopo" | "synthetic" | "train" | "counting" | "angle" | "simulation";
  title: string;
  caveat: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any;
}
