import { describe, expect, it } from "vitest";
import { jointAngle } from "./angles";
import { LANDMARK_INDEX } from "./types";
import { standingPose, trainerPose, trainerProgress } from "./trainer";
import type { Exercise } from "../types/api";

const ex = (landmarks: string[], start: number, target: number): Exercise => ({
  id: "x", name: "x", target_joints: [], landmarks, common_errors: [], start_angle_deg: start, target_angle_deg: target,
  difficulty_levels: {}, illustrative_only: true,
});

describe("trainer pose", () => {
  it("sets the exercise joint to the start and target angles", () => {
    const e = ex(["LEFT_SHOULDER", "LEFT_ELBOW", "LEFT_WRIST"], 160, 50);
    for (const [p, want] of [[0, 160], [1, 50], [0.5, 105]] as const) {
      const lm = trainerPose(e, "LEFT", p);
      const [a, b, c] = e.landmarks.map((n) => lm[LANDMARK_INDEX[n]]);
      expect(jointAngle(a, b, c)).toBeCloseTo(want, 0);
    }
  });

  it("works for the right side and keeps every other landmark in place", () => {
    const e = ex(["LEFT_HIP", "LEFT_SHOULDER", "LEFT_ELBOW"], 20, 90);
    const lm = trainerPose(e, "RIGHT", 1), base = standingPose();
    expect(jointAngle(lm[LANDMARK_INDEX.RIGHT_HIP], lm[LANDMARK_INDEX.RIGHT_SHOULDER], lm[LANDMARK_INDEX.RIGHT_ELBOW])).toBeCloseTo(90, 0);
    expect(lm[LANDMARK_INDEX.LEFT_ELBOW]).toEqual(base[LANDMARK_INDEX.LEFT_ELBOW]);
  });

  it("clamps progress and repeats smoothly", () => {
    const e = ex(["LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE"], 170, 90);
    expect(trainerPose(e, "LEFT", 5)).toEqual(trainerPose(e, "LEFT", 1));
    expect(trainerProgress(0)).toBeCloseTo(0);
    expect(trainerProgress(2)).toBeCloseTo(1);
    expect(trainerProgress(4)).toBeCloseTo(0);
  });
});
