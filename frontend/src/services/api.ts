import type {
  AdaptationState, AnalyticsSummary, WeeklySummary, CompleteOut, Exercise, Filters, Health, ProgressPoint, Recommendation,
  ResearchResult, SessionCreated, SessionDetail, User,
} from "../types/api";

const TOKEN_KEY = "arvr.token";

/** Browser storage is a per-device convenience only; every read and write is guarded. */
export const tokenStore = {
  get(): string | null {
    try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
  },
  set(t: string | null) {
    try { if (t) localStorage.setItem(TOKEN_KEY, t); else localStorage.removeItem(TOKEN_KEY); } catch { /* storage unavailable */ }
  },
};

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const res = await fetch(path, { ...init, headers });
  if (!res.ok) {
    let detail = `${path} failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch { /* non-JSON error body */ }
    throw new ApiError(res.status, detail);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  health: () => request<Health>("/api/health"),
  exercises: () => request<Exercise[]>("/api/exercises"),

  register: (username: string, password: string, age_range = "", goals = "") =>
    post<{ token: string; user: User }>("/api/auth/register", { username, password, age_range, goals }),
  login: (username: string, password: string) => post<{ token: string; user: User }>("/api/auth/login", { username, password }),
  logout: () => post<void>("/api/auth/logout"),
  me: () => request<User>("/api/me"),
  updateMe: (patch: { age_range?: string; goals?: string; preferences?: Record<string, boolean> }) =>
    request<User>("/api/me", { method: "PATCH", body: JSON.stringify(patch) }),
  deleteMe: () => request<void>("/api/me", { method: "DELETE" }),

  createSession: (exercise_id: string, difficulty: number, is_demo: boolean) =>
    post<SessionCreated>("/api/sessions", { exercise_id, difficulty, is_demo }),
  completeSession: (id: string) => post<CompleteOut>(`/api/sessions/${id}/complete`),
  checkin: (id: string, pain: number, note: string) => post<CompleteOut>(`/api/sessions/${id}/checkin`, { pain, note }),

  adaptationState: (exercise_id: string) =>
    request<AdaptationState>(`/api/adaptation/state?exercise_id=${encodeURIComponent(exercise_id)}`),
  resetAdaptation: (exercise_id: string) => post<Recommendation>("/api/adaptation/reset", { exercise_id }),
  progress: (f: Filters = {}) =>
    request<{ points: ProgressPoint[]; note: string }>(`/api/analytics/progress${query(f)}`),
  summary: (f: Filters = {}) => request<AnalyticsSummary>(`/api/analytics/summary${query(f)}`),
  sessionDetail: (id: string) => request<SessionDetail>(`/api/sessions/${encodeURIComponent(id)}/detail`),
  researchResults: () => request<{ results: ResearchResult[]; note: string }>("/api/research/results"),

  weekly: () => request<WeeklySummary>("/api/analytics/weekly"),

  /** Downloads everything stored about the user's real sessions as one JSON file. */
  async backup(): Promise<void> {
    const headers = new Headers();
    const token = tokenStore.get();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const res = await fetch("/api/me/backup", { headers });
    if (!res.ok) throw new ApiError(res.status, `Backup failed (${res.status})`);
    const url = URL.createObjectURL(await res.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = "arvr-backup.json";
    a.click();
    URL.revokeObjectURL(url);
  },
  /** Restores sessions from a backup file; sessions that already exist are skipped. */
  async restore(file: File): Promise<{ added: number; skipped: number }> {
    let data: unknown;
    try { data = JSON.parse(await file.text()); } catch { throw new ApiError(422, "That file is not a valid backup (not JSON)."); }
    return post<{ added: number; skipped: number }>("/api/me/restore", data);
  },

  /** Downloads the user's own CSV (needs the auth header, so it goes through fetch rather than a plain link). */
  async exportCsv(kind: "sessions" | "repetitions", f: Filters = {}): Promise<void> {
    const headers = new Headers();
    const token = tokenStore.get();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const res = await fetch(`/api/analytics/export.csv${query({ ...f }, { kind })}`, { headers });
    if (!res.ok) throw new ApiError(res.status, `Export failed (${res.status})`);
    const url = URL.createObjectURL(await res.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = `arvr-${kind}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  },
};

function query(f: Filters, extra: Record<string, string> = {}): string {
  const p = new URLSearchParams(extra);
  if (f.exercise_id) p.set("exercise_id", f.exercise_id);
  if (f.from) p.set("from", f.from);
  if (f.to) p.set("to", f.to);
  if (f.include_demo) p.set("include_demo", "true");
  const s = p.toString();
  return s ? `?${s}` : "";
}
