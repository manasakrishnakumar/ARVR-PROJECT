import { LANDMARK_INDEX, type Landmark } from "./types";
import type { Exercise } from "../types/api";
import { trainerPose } from "./trainer";

/** Camera-setup hint from one frame of landmarks (normalised image coordinates). Pure, so it is unit-tested. */
export function setupHint(lm: Landmark[] | null, ex: Exercise): { ok: boolean; text: string } {
  if (!lm) return { ok: false, text: "Step into view so the camera can see you." };
  const joints = ex.landmarks.map((n) => lm[LANDMARK_INDEX[n]]);
  if (joints.some((j) => j.visibility < 0.5)) return { ok: false, text: "The exercising joints are not clearly visible. Face the camera or turn side-on as the exercise needs, and check the light." };
  const seen = lm.filter((p) => p.visibility >= 0.5);
  const minY = Math.min(...seen.map((p) => p.y)), maxY = Math.max(...seen.map((p) => p.y));
  const minX = Math.min(...seen.map((p) => p.x)), maxX = Math.max(...seen.map((p) => p.x));
  if (minX < 0.03 || maxX > 0.97 || minY < 0.02 || maxY > 0.98) return { ok: false, text: "Step back a little: part of you is at the edge of the picture." };
  if (maxY - minY < 0.35) return { ok: false, text: "Step closer: you look small in the picture." };
  const cx = (minX + maxX) / 2;
  if (Math.abs(cx - 0.5) > 0.25) return { ok: false, text: "Move towards the middle of the picture." };
  return { ok: true, text: "Good position." };
}

export type JointState = "reached" | "moving" | "unclear";

/** Colour state of the exercising joint: unclear when its landmarks are low confidence, reached when the angle is within
 *  `tol` degrees of the (illustrative) target, otherwise moving. */
export function jointState(angle: number | null, visible: boolean, ex: Exercise, tol = 10): JointState {
  if (angle === null || !visible) return "unclear";
  return Math.abs(angle - ex.target_angle_deg) <= tol ? "reached" : "moving";
}

export const JOINT_COLOUR: Record<JointState, string> = { reached: "#22c55e", moving: "#f59e0b", unclear: "#ef4444" };

export function exerciseSide(ex: Exercise): "LEFT" | "RIGHT" {
  return ex.landmarks[0].startsWith("RIGHT_") ? "RIGHT" : "LEFT";
}

/** The virtual trainer's pose fitted onto the user's body (shoulder midpoint and torso length), so it can be drawn as a translucent
 *  "ghost" to match. Returns null when the user's torso is not visible. */
export function ghostPose(ex: Exercise, progress: number, user: Landmark[] | null): Landmark[] | null {
  if (!user) return null;
  const need = [11, 12, 23, 24];
  if (need.some((i) => user[i].visibility < 0.5)) return null;
  const t = trainerPose(ex, exerciseSide(ex), progress);
  const mid = (l: Landmark[], a: number, b: number) => ({ x: (l[a].x + l[b].x) / 2, y: (l[a].y + l[b].y) / 2 });
  const tS = mid(t, 11, 12), tH = mid(t, 23, 24), uS = mid(user, 11, 12), uH = mid(user, 23, 24);
  const tTorso = Math.hypot(tH.x - tS.x, tH.y - tS.y), uTorso = Math.hypot(uH.x - uS.x, uH.y - uS.y);
  if (uTorso < 0.05 || tTorso === 0) return null;
  const k = uTorso / tTorso;
  return t.map((p) => ({ ...p, x: uS.x + (p.x - tS.x) * k, y: uS.y + (p.y - tS.y) * k }));
}

const FLASH_TEXT: Record<string, string> = {
  acceptable: "Good", insufficient_range: "Go further", incomplete_repetition: "Finish the movement", too_fast: "Slower",
  uncontrolled: "Steadier", insufficient_data: "Not seen clearly",
};

/** Large on-screen confirmation shown briefly after each repetition. Colour: green for an acceptable repetition, amber otherwise. */
export function repFlash(rep: { counted: boolean; label: string }): { text: string; colour: string } {
  const good = rep.counted && rep.label === "acceptable";
  const known = FLASH_TEXT[rep.label];
  const text = known ? (rep.counted ? known : `${known} (not counted)`) : rep.counted ? "Counted" : "Not counted";
  return { text, colour: good ? "#22c55e" : "#f59e0b" };
}
