import { describe, expect, it } from "vitest";
import { exerciseSide, ghostPose, jointState, repFlash, setupHint } from "./guidance";
import { repCue } from "./speech";
import { standingPose } from "./trainer";
import type { Exercise } from "../types/api";

const ex = (over: Partial<Exercise> = {}): Exercise => ({
  id: "elbow_flexion", name: "Elbow flexion", target_joints: ["elbow"], landmarks: ["LEFT_SHOULDER", "LEFT_ELBOW", "LEFT_WRIST"],
  common_errors: [], start_angle_deg: 170, target_angle_deg: 60, difficulty_levels: {}, illustrative_only: true, ...over,
});

describe("setupHint", () => {
  it("asks the user to step into view when nobody is detected", () => {
    expect(setupHint(null, ex())).toMatchObject({ ok: false, text: expect.stringMatching(/step into view/i) });
  });
  it("accepts a well framed figure", () => {
    expect(setupHint(standingPose(), ex())).toEqual({ ok: true, text: "Good position." });
  });
  it("flags low-confidence exercising joints", () => {
    const lm = standingPose(); lm[13] = { ...lm[13], visibility: 0.2 };
    expect(setupHint(lm, ex()).text).toMatch(/not clearly visible/);
  });
  it("tells a user at the edge to step back and a small figure to step closer", () => {
    const edge = standingPose(); edge[27] = { ...edge[27], y: 0.995 };
    expect(setupHint(edge, ex()).text).toMatch(/step back/i);
    const small = standingPose().map((p) => ({ ...p, y: 0.4 + (p.y - 0.5) * 0.3 }));
    expect(setupHint(small, ex()).text).toMatch(/step closer/i);
  });
  it("asks an off-centre user to move towards the middle", () => {
    const shifted = standingPose().map((p) => ({ ...p, x: p.x - 0.3 }));
    expect(setupHint(shifted, ex()).text).toMatch(/middle|edge/i);
  });
});

describe("jointState", () => {
  it("is unclear without a measurement or when not visible", () => {
    expect(jointState(null, true, ex())).toBe("unclear");
    expect(jointState(100, false, ex())).toBe("unclear");
  });
  it("is reached near the target and moving elsewhere", () => {
    expect(jointState(65, true, ex())).toBe("reached");
    expect(jointState(120, true, ex())).toBe("moving");
  });
});

describe("ghostPose", () => {
  it("is null when the torso is not visible", () => {
    const lm = standingPose(); lm[23] = { ...lm[23], visibility: 0 };
    expect(ghostPose(ex(), 0.5, lm)).toBeNull();
    expect(ghostPose(ex(), 0.5, null)).toBeNull();
  });
  it("lands on the user's shoulders and scales to their torso", () => {
    const user = standingPose().map((p) => ({ ...p, x: p.x * 0.5 + 0.2, y: p.y * 0.5 + 0.1 }));
    const g = ghostPose(ex(), 1, user)!;
    expect((g[11].x + g[12].x) / 2).toBeCloseTo((user[11].x + user[12].x) / 2, 6);
    expect(g[23].y - g[11].y).toBeCloseTo(user[23].y - user[11].y, 6);
  });
  it("at progress 1 the ghost's joint angle equals the exercise target", () => {
    const g = ghostPose(ex(), 1, standingPose())!;
    const [a, b, c] = [11, 13, 15].map((i) => g[i]);
    const v1 = [a.x - b.x, a.y - b.y], v2 = [c.x - b.x, c.y - b.y];
    const ang = (Math.acos((v1[0] * v2[0] + v1[1] * v2[1]) / (Math.hypot(v1[0], v1[1]) * Math.hypot(v2[0], v2[1]))) * 180) / Math.PI;
    expect(ang).toBeCloseTo(60, 0);
  });
});

describe("exerciseSide and voice cues", () => {
  it("reads the side from the landmark names", () => {
    expect(exerciseSide(ex())).toBe("LEFT");
    expect(exerciseSide(ex({ landmarks: ["RIGHT_HIP", "RIGHT_KNEE", "RIGHT_ANKLE"] }))).toBe("RIGHT");
  });
  it("counts good repetitions and announces completion", () => {
    expect(repCue({ counted: true, label: "acceptable" }, 3, 5)).toBe("3.");
    expect(repCue({ counted: true, label: "acceptable" }, 5, 5)).toMatch(/all your repetitions/);
  });
  it("gives a short correction for flagged or uncounted repetitions", () => {
    expect(repCue({ counted: false, label: "insufficient_range" }, 2, 5)).toBe("Go a little further.");
    expect(repCue({ counted: true, label: "too_fast" }, 2, 5)).toBe("2. Slow down.");
    expect(repCue({ counted: false, label: "something_new" }, 2, 5)).toBe("");
  });
});

describe("repFlash", () => {
  it("is green for an acceptable counted repetition", () => {
    expect(repFlash({ counted: true, label: "acceptable" })).toEqual({ text: "Good", colour: "#22c55e" });
  });
  it("is amber with a correction for flagged ones, and says when it was not counted", () => {
    expect(repFlash({ counted: true, label: "too_fast" })).toEqual({ text: "Slower", colour: "#f59e0b" });
    expect(repFlash({ counted: false, label: "insufficient_range" }).text).toBe("Go further (not counted)");
    expect(repFlash({ counted: false, label: "mystery" }).text).toBe("Not counted");
    expect(repFlash({ counted: true, label: "mystery" }).text).toBe("Counted");
  });
});
