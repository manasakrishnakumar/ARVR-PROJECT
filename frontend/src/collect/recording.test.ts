import { describe, expect, it } from "vitest";
import { buildRecording, fileName, FORMAT, frameRow, validateMeta } from "./recording";

const ok = { participant_code: "P01", exercise_id: "elbow_flexion", intended: { label: "correct" as const, error: "" } };
const errors = ["Incomplete bend", "Moving too fast"];

describe("validateMeta", () => {
  it("accepts a complete, consented form", () => {
    expect(validateMeta(ok, true, errors)).toEqual([]);
    expect(validateMeta({ ...ok, intended: { label: "error", error: "Moving too fast" } }, true, errors)).toEqual([]);
    expect(validateMeta({ ...ok, intended: { label: "error", error: "other" } }, true, errors)).toEqual([]);
  });

  it("requires consent first", () => {
    expect(validateMeta(ok, false, errors)[0]).toMatch(/consent/i);
  });

  it("rejects codes that could identify a person or are malformed", () => {
    for (const bad of ["", "A", "Maria Garcia", "john.doe@mail.com", "x".repeat(17), "P 01"]) {
      expect(validateMeta({ ...ok, participant_code: bad }, true, errors).join(" ")).toMatch(/Participant code/);
    }
  });

  it("requires a valid error type when an error is performed on purpose", () => {
    expect(validateMeta({ ...ok, intended: { label: "error", error: "" } }, true, errors).join(" ")).toMatch(/which error/);
    expect(validateMeta({ ...ok, intended: { label: "error", error: "Made up" } }, true, errors).join(" ")).toMatch(/Unknown error/);
    expect(validateMeta({ ...ok, exercise_id: "" }, true, errors).join(" ")).toMatch(/Choose an exercise/);
  });
});

describe("recording serialisation", () => {
  it("stores only rounded landmark numbers and timestamps (no images)", () => {
    const row = frameRow(1.23456, Array.from({ length: 33 }, () => ({ x: 0.123456789, y: 0.5, z: -0.1, visibility: 0.98765 })));
    expect(row[0]).toBe(1.235);
    expect(row[1]).toHaveLength(33);
    expect(row[1][0]).toEqual([0.1235, 0.5, -0.1, 0.9877]);
    const rec = buildRecording({ participant_code: "P01", exercise_id: "knee_flexion", side: "left", intended: { label: "correct", error: "" },
      synthetic: false, camera: { width: 640, height: 480 }, model: "m" }, [row], new Date("2026-10-27T10:00:00Z"));
    expect(rec.format).toBe(FORMAT);
    expect(rec.created_utc).toBe("2026-10-27T10:00:00.000Z");
    expect(JSON.stringify(rec)).not.toMatch(/data:image|base64/);
    expect(fileName(rec, 2)).toBe("arvr-recording-P01-knee_flexion-correct-2.json");
  });
});
