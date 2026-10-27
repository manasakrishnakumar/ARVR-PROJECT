export interface Landmark {
  x: number; // normalized 0..1, image plane
  y: number;
  z: number;
  visibility: number; // 0..1 confidence
}

export interface PoseFrame {
  timestampMs: number;
  landmarks: Landmark[] | null; // null = no person detected
  source: "camera" | "demo";
}

export interface PoseEstimator {
  readonly name: string;
  detect(video: HTMLVideoElement | null, timestampMs: number): PoseFrame;
  close(): void;
}

// MediaPipe Pose landmark indices
export const LM = {
  L_SHOULDER: 11, R_SHOULDER: 12, L_ELBOW: 13, R_ELBOW: 14, L_WRIST: 15, R_WRIST: 16,
  L_HIP: 23, R_HIP: 24, L_KNEE: 25, R_KNEE: 26, L_ANKLE: 27, R_ANKLE: 28,
} as const;

export const LANDMARK_INDEX: Record<string, number> = {
  LEFT_SHOULDER: 11, RIGHT_SHOULDER: 12, LEFT_ELBOW: 13, RIGHT_ELBOW: 14, LEFT_WRIST: 15, RIGHT_WRIST: 16,
  LEFT_HIP: 23, RIGHT_HIP: 24, LEFT_KNEE: 25, RIGHT_KNEE: 26, LEFT_ANKLE: 27, RIGHT_ANKLE: 28,
};

export const SKELETON: [number, number][] = [
  [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
  [11, 23], [12, 24], [23, 24], [23, 25], [25, 27], [24, 26], [26, 28],
];
