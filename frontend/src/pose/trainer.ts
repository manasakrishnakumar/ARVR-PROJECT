import { LANDMARK_INDEX, type Landmark } from "./types";
import type { Exercise } from "../types/api";

/** A standing figure in normalised image coordinates (y grows downward). Everything is visible. */
export function standingPose(): Landmark[] {
  const lm: Landmark[] = Array.from({ length: 33 }, () => ({ x: 0.5, y: 0.5, z: 0, visibility: 0 }));
  const set = (i: number, x: number, y: number) => (lm[i] = { x, y, z: 0, visibility: 1 });
  set(0, 0.5, 0.16); set(7, 0.53, 0.17); set(8, 0.47, 0.17);
  set(11, 0.57, 0.28); set(12, 0.43, 0.28); set(13, 0.59, 0.44); set(14, 0.41, 0.44); set(15, 0.6, 0.58); set(16, 0.4, 0.58);
  set(23, 0.55, 0.58); set(24, 0.45, 0.58); set(25, 0.55, 0.78); set(26, 0.45, 0.78); set(27, 0.55, 0.95); set(28, 0.45, 0.95);
  return lm;
}

/** Virtual trainer: the standing figure with the exercise's joint set to the angle at `progress` (0 = start, 1 = illustrative target).
 *  Landmark C of the exercise's [A, B, C] triplet is rotated about B so the angle at B equals the requested value. */
export function trainerPose(ex: Exercise, side: "LEFT" | "RIGHT", progress: number): Landmark[] {
  const lm = standingPose();
  const [a, b, c] = ex.landmarks.map((n) => LANDMARK_INDEX[n.replace("LEFT_", `${side}_`)]);
  const theta = ((ex.start_angle_deg + Math.max(0, Math.min(1, progress)) * (ex.target_angle_deg - ex.start_angle_deg)) * Math.PI) / 180;
  const A = lm[a], B = lm[b], C = lm[c];
  const len = Math.hypot(C.x - B.x, C.y - B.y);
  const ux = A.x - B.x, uy = A.y - B.y, un = Math.hypot(ux, uy) || 1;
  const cand = [1, -1].map((s) => {
    const cos = Math.cos(theta * s), sin = Math.sin(theta * s);
    return { x: B.x + (len * (ux * cos - uy * sin)) / un, y: B.y + (len * (ux * sin + uy * cos)) / un };
  });
  // the limb should move away from the body's midline, which is how these exercises look from the front
  const best = Math.abs(cand[0].x - 0.5) >= Math.abs(cand[1].x - 0.5) ? cand[0] : cand[1];
  lm[c] = { ...C, x: best.x, y: best.y };
  return lm;
}

/** Progress 0..1..0 over a repetition lasting `period` seconds. */
export function trainerProgress(tSeconds: number, period = 4): number {
  return (1 - Math.cos((2 * Math.PI * tSeconds) / period)) / 2;
}
