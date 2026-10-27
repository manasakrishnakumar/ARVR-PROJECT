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
