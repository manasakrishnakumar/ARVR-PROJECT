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
  level: number;
  counted_reps: number | null;
  target_reps: number | null;
  quality: number | null;
  error_rate: number | null;
  classification: string | null;
  action: string | null;
  next_level: number | null;
}
