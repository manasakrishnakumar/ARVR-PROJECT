import type { Landmark } from "../pose/types";

const ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // no look-alike characters (0/O, 1/I)

/** A random room code for the local Unity client to join. Not an account credential. */
export function newRoomCode(length = 8): string {
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => ALPHABET[b % ALPHABET.length]).join("");
}

export interface RelayState {
  angle: number | null;
  phase: string;
  countedReps: number;
  targetReps: number;
  feedback: string;
  label: string;
}

/** One frame for the relay: landmarks flattened to 33 x [x, y, z, visibility] (numbers only; no video or image). */
export function buildRelayFrame(lm: Landmark[], s: RelayState): string {
  const r = (v: number) => Math.round(v * 10000) / 10000;
  const flat: number[] = [];
  for (let i = 0; i < 33; i++) {
    const l = lm[i] ?? { x: 0, y: 0, z: 0, visibility: 0 };
    flat.push(r(l.x), r(l.y), r(l.z), r(l.visibility));
  }
  return JSON.stringify({ lm: flat, angle: s.angle == null ? -1 : r(s.angle), has_angle: s.angle != null, phase: s.phase,
    counted_reps: s.countedReps, target_reps: s.targetReps, feedback: s.feedback, label: s.label });
}

export class RelayPublisher {
  private ws: WebSocket;
  status: "connecting" | "open" | "closed" = "connecting";

  constructor(room: string, onStatus: (s: "connecting" | "open" | "closed", detail?: string) => void) {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    this.ws = new WebSocket(`${scheme}://${location.host}/api/ws/relay/${encodeURIComponent(room)}?role=publisher`);
    this.ws.onopen = () => { this.status = "open"; onStatus("open"); };
    this.ws.onclose = (e) => { this.status = "closed"; onStatus("closed", e.reason || undefined); };
    this.ws.onerror = () => onStatus("closed", "connection error");
  }

  publish(frame: string) {
    if (this.ws.readyState === WebSocket.OPEN) this.ws.send(frame);
  }

  close() {
    this.ws.onclose = null;
    this.ws.close(1000);
  }
}
