export interface HelloMsg { type: "hello"; exercise_id: string; difficulty: number; target_reps: number; disclaimer: string; calibrating?: boolean }
export interface StateMsg { type: "state"; phase: string; counted_reps: number; angle: number | null; progress: number | null; calibrating?: boolean }
export interface CalibratedMsg { type: "calibrated"; start: number; target: number }
export interface RepMsg {
  type: "rep"; index: number; counted: boolean; label: string; score: number | null; reliable: boolean;
  explanation: string; feedback: string; features: Record<string, number>;
}
export interface ErrorMsg { type: "error"; detail: string }
export type AnalysisMsg = HelloMsg | StateMsg | RepMsg | ErrorMsg | CalibratedMsg;
export type SocketStatus = "connecting" | "open" | "closed" | "failed";

/** Streams joint-angle samples to the backend, which owns counting and assessment. */
export class AnalysisSocket {
  private ws: WebSocket;

  constructor(
    exerciseId: string,
    difficulty: number,
    private onMsg: (m: AnalysisMsg) => void,
    private onStatus: (s: SocketStatus) => void,
    session?: { id: string; key: string }, // per-session secret (not an account credential): lets the server save repetitions
    calibrate = false, // measure the counting range from the user's own first seconds of movement
  ) {
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    const saving = session ? `&session_id=${encodeURIComponent(session.id)}&key=${encodeURIComponent(session.key)}` : "";
    const cal = calibrate ? "&calibrate=auto" : "";
    this.ws = new WebSocket(`${scheme}://${location.host}/api/ws/analysis?exercise_id=${encodeURIComponent(exerciseId)}&difficulty=${difficulty}${saving}${cal}`);
    onStatus("connecting");
    this.ws.onopen = () => onStatus("open");
    this.ws.onclose = (e) => onStatus(e.code === 1000 || e.code === 1005 ? "closed" : "failed");
    this.ws.onerror = () => onStatus("failed");
    this.ws.onmessage = (e) => {
      try { this.onMsg(JSON.parse(e.data as string) as AnalysisMsg); } catch { /* ignore malformed frame */ }
    };
  }

  send(t: number, angle: number | null) {
    if (this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify({ t, angle }));
  }

  close() {
    this.ws.onclose = null;
    this.ws.close(1000);
  }
}
