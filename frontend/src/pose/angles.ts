import { LM, type Landmark } from "./types";

export const MIN_CONFIDENCE = 0.5;

/** Angle (deg) at b between b->a and b->c, image plane. null when undefined/unreliable. */
export function jointAngle(a?: Landmark, b?: Landmark, c?: Landmark, minConf = MIN_CONFIDENCE): number | null {
  if (!a || !b || !c) return null;
  for (const p of [a, b, c]) {
    if (![p.x, p.y, p.visibility].every(Number.isFinite) || p.visibility < minConf) return null;
  }
  const v1 = [a.x - b.x, a.y - b.y];
  const v2 = [c.x - b.x, c.y - b.y];
  const n1 = Math.hypot(v1[0], v1[1]);
  const n2 = Math.hypot(v2[0], v2[1]);
  if (n1 < 1e-9 || n2 < 1e-9) return null;
  const cos = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2);
  return (Math.acos(Math.max(-1, Math.min(1, cos))) * 180) / Math.PI;
}

export interface JointAngles {
  label: string;
  angle: number | null;
}

export function bodyAngles(lm: Landmark[]): JointAngles[] {
  const g = (i: number) => lm[i];
  return [
    { label: "Left elbow", angle: jointAngle(g(LM.L_SHOULDER), g(LM.L_ELBOW), g(LM.L_WRIST)) },
    { label: "Right elbow", angle: jointAngle(g(LM.R_SHOULDER), g(LM.R_ELBOW), g(LM.R_WRIST)) },
    { label: "Left shoulder", angle: jointAngle(g(LM.L_HIP), g(LM.L_SHOULDER), g(LM.L_ELBOW)) },
    { label: "Right shoulder", angle: jointAngle(g(LM.R_HIP), g(LM.R_SHOULDER), g(LM.R_ELBOW)) },
    { label: "Left hip", angle: jointAngle(g(LM.L_SHOULDER), g(LM.L_HIP), g(LM.L_KNEE)) },
    { label: "Right hip", angle: jointAngle(g(LM.R_SHOULDER), g(LM.R_HIP), g(LM.R_KNEE)) },
    { label: "Left knee", angle: jointAngle(g(LM.L_HIP), g(LM.L_KNEE), g(LM.L_ANKLE)) },
    { label: "Right knee", angle: jointAngle(g(LM.R_HIP), g(LM.R_KNEE), g(LM.R_ANKLE)) },
  ];
}
