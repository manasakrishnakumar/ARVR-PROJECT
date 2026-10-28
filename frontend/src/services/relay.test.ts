import { describe, expect, it } from "vitest";
import { buildRelayFrame, newRoomCode } from "./relay";

const state = { angle: 52.123456, phase: "target", countedReps: 3, targetReps: 5, feedback: "Good repetition.", label: "acceptable" };

describe("relay frames", () => {
  it("flattens 33 landmarks into exactly 132 rounded numbers and carries the analysis state", () => {
    const lm = Array.from({ length: 33 }, (_, i) => ({ x: i / 100 + 0.123456, y: 0.5, z: -0.2, visibility: 0.98765 }));
    const f = JSON.parse(buildRelayFrame(lm, state));
    expect(f.lm).toHaveLength(132);
    expect(f.lm.slice(0, 4)).toEqual([0.1235, 0.5, -0.2, 0.9877]);
    expect(f).toMatchObject({ angle: 52.1235, has_angle: true, phase: "target", counted_reps: 3, target_reps: 5, label: "acceptable" });
    expect(buildRelayFrame(lm, state).length).toBeLessThan(8192); // within the server's message limit
  });

  it("pads missing landmarks as invisible and flags a missing angle", () => {
    const f = JSON.parse(buildRelayFrame([], { ...state, angle: null }));
    expect(f.lm).toHaveLength(132);
    expect(f.lm.every((v: number) => v === 0)).toBe(true);
    expect(f.has_angle).toBe(false);
    expect(buildRelayFrame([], state)).not.toMatch(/data:image|base64/);
  });
});

describe("room codes", () => {
  it("are 8 characters from the accepted alphabet, so the server accepts them, and differ each time", () => {
    const codes = new Set(Array.from({ length: 50 }, () => newRoomCode()));
    expect(codes.size).toBeGreaterThan(45);
    for (const c of codes) expect(c).toMatch(/^[A-Z0-9]{8}$/);
    expect(newRoomCode(6)).toHaveLength(6);
  });
});
