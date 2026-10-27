export interface Health {
  status: string;
  version: string;
  disclaimer: string;
}

export interface Exercise {
  id: string;
  name: string;
  target_joints: string[];
  common_errors: string[];
  start_angle_deg: number;
  target_angle_deg: number;
  illustrative_only: boolean;
}
