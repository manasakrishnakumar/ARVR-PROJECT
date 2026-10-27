import type { Landmark } from "../pose/types";

export const FORMAT = "arvr-landmarks-v1";
export const MAX_SECONDS = 300; // a recording is held in memory until downloaded, so it is capped

export interface Intended {
  label: "correct" | "error";
  error: string; // empty for "correct"; otherwise one of the exercise's listed errors or "other"
}

export interface RecordingMeta {
  participant_code: string;
  exercise_id: string;
  side: "left" | "right";
  intended: Intended;
  synthetic: boolean; // the synthetic demo can be recorded to test the pipeline; the importer keeps it apart from real data
  camera: { width: number; height: number };
  model: string;
}

export interface Recording extends RecordingMeta {
  format: typeof FORMAT;
  created_utc: string;
  frames: [number, number[][]][]; // [seconds since start, 33 x [x, y, z, visibility]] (no video, no images)
}

const CODE = /^[A-Za-z0-9-]{2,16}$/;

/** Returns a list of problems; empty means the form is acceptable. The participant code must not identify anyone. */
export function validateMeta(m: { participant_code: string; exercise_id: string; intended: Intended }, consent: boolean, knownErrors: string[]): string[] {
  const p: string[] = [];
  if (!consent) p.push("Please confirm consent before recording.");
  if (!CODE.test(m.participant_code)) p.push("Participant code must be 2-16 letters, numbers or hyphens (use a code like P01, not a name).");
  if (!m.exercise_id) p.push("Choose an exercise.");
  if (m.intended.label === "error" && !m.intended.error) p.push("Say which error is being performed on purpose, or choose 'other'.");
  if (m.intended.label === "error" && m.intended.error !== "other" && !knownErrors.includes(m.intended.error)) p.push("Unknown error type for this exercise.");
  return p;
}

const r4 = (v: number) => Math.round(v * 10000) / 10000;

export function frameRow(t: number, lms: Landmark[]): [number, number[][]] {
  return [Math.round(t * 1000) / 1000, lms.map((l) => [r4(l.x), r4(l.y), r4(l.z), r4(l.visibility)])];
}

export function buildRecording(meta: RecordingMeta, frames: [number, number[][]][], now = new Date()): Recording {
  return { format: FORMAT, created_utc: now.toISOString(), ...meta, frames };
}

export function fileName(r: Recording, n: number): string {
  return `arvr-recording-${r.participant_code}-${r.exercise_id}-${r.intended.label}-${n}.json`;
}
