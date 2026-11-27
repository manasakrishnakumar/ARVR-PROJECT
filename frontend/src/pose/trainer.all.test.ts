import { describe, expect, it } from "vitest";
import { jointAngle } from "./angles";
import { DemoEstimator } from "./demo";
import { LANDMARK_INDEX } from "./types";
import type { Exercise } from "../types/api";

const files = import.meta.glob("../../../backend/app/exercises/definitions/*.json", { eager: true }) as Record<string, { default: Exercise }>;
const all = Object.values(files).map((m) => m.default);

describe("synthetic demo for every exercise in the library", () => {
  it("finds all thirteen definitions", () => expect(all.length).toBe(13));
  it.each(all.map((e) => [e.id, e] as const))("%s moves between its start and target angles", (id, ex) => {
    const est = new DemoEstimator(4, ex);
    const angleAt = (ms: number) => {
      const lm = est.detect(null, ms).landmarks!;
      const [a, b, c] = ex.landmarks.map((n) => lm[LANDMARK_INDEX[n]]);
      return jointAngle(a, b, c)!;
    };
    if (id === "elbow_flexion") { expect(angleAt(0)).toBeCloseTo(160, 0); expect(angleAt(2000)).toBeCloseTo(50, 0); return; }
    expect(angleAt(0)).toBeCloseTo(ex.start_angle_deg, 0);
    expect(angleAt(2000)).toBeCloseTo(ex.target_angle_deg, 0);
  });
});
