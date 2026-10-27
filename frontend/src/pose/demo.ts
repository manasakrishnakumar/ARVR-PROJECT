import { LM, type Landmark, type PoseEstimator, type PoseFrame } from "./types";

/** SYNTHETIC pose generator (not real human data): a standing figure whose left elbow flexes 160 -> 50 degrees. */
export class DemoEstimator implements PoseEstimator {
  readonly name = "Synthetic demo";
  constructor(private periodS = 4) {}

  detect(_video: HTMLVideoElement | null, timestampMs: number): PoseFrame {
    const t = timestampMs / 1000;
    const theta = 105 + 55 * Math.cos((2 * Math.PI * t) / this.periodS); // 50..160 deg
    const rad = (theta * Math.PI) / 180;
    const lm: Landmark[] = Array.from({ length: 33 }, () => ({ x: 0.5, y: 0.5, z: 0, visibility: 0 }));
    const set = (i: number, x: number, y: number) => (lm[i] = { x, y, z: 0, visibility: 0.99 });
    set(LM.L_SHOULDER, 0.58, 0.28); set(LM.R_SHOULDER, 0.42, 0.28);
    set(LM.L_HIP, 0.56, 0.58); set(LM.R_HIP, 0.44, 0.58);
    set(LM.L_KNEE, 0.56, 0.78); set(LM.R_KNEE, 0.44, 0.78);
    set(LM.L_ANKLE, 0.56, 0.95); set(LM.R_ANKLE, 0.44, 0.95);
    set(LM.R_ELBOW, 0.40, 0.44); set(LM.R_WRIST, 0.40, 0.58);
    // Upper arm hangs straight up from the elbow to the shoulder; forearm direction is
    // chosen so the angle at the elbow between (shoulder) and (wrist) equals theta.
    const ex = 0.6, ey = 0.44;
    set(LM.L_SHOULDER, ex, 0.28);
    set(LM.L_ELBOW, ex, ey);
    set(LM.L_WRIST, ex + 0.16 * Math.sin(rad), ey - 0.16 * Math.cos(rad));
    return { timestampMs, landmarks: lm, source: "demo" };
  }
  close() {}
}
