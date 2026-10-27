import { FilesetResolver, PoseLandmarker } from "@mediapipe/tasks-vision";
import type { PoseEstimator, PoseFrame } from "./types";

export const MODEL_URL = "/models/pose_landmarker_lite.task";

export class MediaPipeEstimator implements PoseEstimator {
  readonly name = "MediaPipe Pose Landmarker (lite, local)";
  private constructor(private lm: PoseLandmarker) {}

  /** Throws if the model file or WASM is missing; callers surface that rather than faking output. */
  static async create(): Promise<MediaPipeEstimator> {
    const head = await fetch(MODEL_URL, { method: "HEAD" });
    const type = head.headers.get("content-type") ?? "";
    if (!head.ok || type.includes("text/html")) {
      throw new Error(`Pose model not found at ${MODEL_URL}. Run scripts\\download_pose_model.ps1 and reload.`);
    }
    const vision = await FilesetResolver.forVisionTasks("/wasm");
    const lm = await PoseLandmarker.createFromOptions(vision, {
      baseOptions: { modelAssetPath: MODEL_URL, delegate: "CPU" },
      runningMode: "VIDEO",
      numPoses: 1,
    });
    return new MediaPipeEstimator(lm);
  }

  detect(video: HTMLVideoElement | null, timestampMs: number): PoseFrame {
    if (!video) return { timestampMs, landmarks: null, source: "camera" };
    const res = this.lm.detectForVideo(video, timestampMs);
    const p = res.landmarks[0];
    return {
      timestampMs,
      source: "camera",
      landmarks: p ? p.map((l) => ({ x: l.x, y: l.y, z: l.z, visibility: l.visibility ?? 0 })) : null,
    };
  }

  close() {
    this.lm.close();
  }
}
