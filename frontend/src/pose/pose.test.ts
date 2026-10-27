import { describe, expect, it } from "vitest";
import { bodyAngles, isotropic, jointAngle } from "./angles";
import { DemoEstimator } from "./demo";
import { LM, type Landmark } from "./types";

const P = (x: number, y: number, visibility = 1): Landmark => ({ x, y, z: 0, visibility });

describe("jointAngle", () => {
  it("measures the angle at the middle point", () => {
    expect(jointAngle(P(1, 0), P(0, 0), P(0, 1))).toBeCloseTo(90);
    expect(jointAngle(P(-1, 0), P(0, 0), P(1, 0))).toBeCloseTo(180);
    expect(jointAngle(P(1, 0), P(0, 0), P(2, 0))).toBeCloseTo(0);
  });

  it("returns null instead of a wrong number when landmarks are missing, unreliable or degenerate", () => {
    expect(jointAngle(undefined, P(0, 0), P(0, 1))).toBeNull();
    expect(jointAngle(P(1, 0, 0.1), P(0, 0), P(0, 1))).toBeNull(); // low confidence
    expect(jointAngle(P(NaN, 0), P(0, 0), P(0, 1))).toBeNull();
    expect(jointAngle(P(0, 0), P(0, 0), P(0, 1))).toBeNull(); // zero-length segment
  });
});

describe("isotropic", () => {
  it("equalises the x and y scales so angles on non-square video are not distorted", () => {
    // a true 45 degree arm in a 9:16 portrait frame appears as dx = 0.1125, dy = 0.2 in normalised units
    const a = P(0.5 + 0.1125, 0.5 + 0.2), b = P(0.5, 0.5), c = P(0.5, 1);
    const raw = jointAngle(a, b, c)!;
    const fixed = jointAngle(...(isotropic([a, b, c], 0.5625) as [Landmark, Landmark, Landmark]))!;
    expect(raw).not.toBeCloseTo(fixed, 0);
    expect(isotropic([a], 1)[0]).toBe(a); // square: untouched
  });
});

describe("DemoEstimator (synthetic)", () => {
  it("sweeps the left elbow between about 50 and 160 degrees and reports a visible figure", () => {
    const est = new DemoEstimator(4);
    const seen: number[] = [];
    for (let t = 0; t < 4000; t += 100) {
      const f = est.detect(null, t);
      expect(f.source).toBe("demo");
      const a = jointAngle(f.landmarks![LM.L_SHOULDER], f.landmarks![LM.L_ELBOW], f.landmarks![LM.L_WRIST])!;
      seen.push(a);
    }
    expect(Math.min(...seen)).toBeGreaterThan(45);
    expect(Math.max(...seen)).toBeLessThan(165);
    expect(Math.max(...seen) - Math.min(...seen)).toBeGreaterThan(90);
  });

  it("gives bodyAngles for every joint, with null where landmarks are invisible", () => {
    const f = new DemoEstimator().detect(null, 0);
    const list = bodyAngles(f.landmarks!);
    expect(list).toHaveLength(8);
    expect(list.find((x) => x.label === "Left elbow")!.angle).not.toBeNull();
    const hidden = f.landmarks!.map((l) => ({ ...l, visibility: 0 }));
    expect(bodyAngles(hidden).every((x) => x.angle === null)).toBe(true);
  });
});
