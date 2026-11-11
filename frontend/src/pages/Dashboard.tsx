import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Bars, ChartCard, TrendLines } from "../components/Charts";
import { CountUp } from "../components/Fx";
import { useAuth } from "../context/AuthContext";
import { useExercises } from "../hooks/useExercises";
import { api } from "../services/api";
import type { AnalyticsSummary, Filters, ProgressPoint, WeeklySummary } from "../types/api";

const ERR_LABEL: Record<string, string> = {
  insufficient_range: "Range short", incomplete_repetition: "Incomplete", too_fast: "Too fast", uncontrolled: "Uncontrolled",
};
const dayKey = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
/** The last seven calendar days (oldest first), each marked when at least one saved session started that day. */
function lastSevenDays(points: ProgressPoint[]) {
  const active = new Set(points.map((p) => dayKey(new Date(p.started_at))));
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (6 - i));
    return { key: dayKey(d), label: d.toLocaleDateString(undefined, { weekday: "narrow" }), on: active.has(dayKey(d)) };
  });
}
/** Simple fun milestones computed from the user's own saved totals. They say nothing about health. */
function milestones(s: AnalyticsSummary | null, w: WeeklySummary | null) {
  const sessions = s?.total_sessions ?? 0, reps = s?.completed_repetitions ?? 0, q = s?.average_quality_score ?? 0;
  return [
    { icon: "🌱", name: "First session", hint: "finish 1 session", on: sessions >= 1 },
    { icon: "🔁", name: "100 reps", hint: "complete 100 repetitions", on: reps >= 100 },
    { icon: "📅", name: "Regular", hint: "finish 5 sessions", on: sessions >= 5 },
    { icon: "🔥", name: "3-day run", hint: "exercise 3 days in a row", on: (w?.day_streak ?? 0) >= 3 },
    { icon: "🎯", name: "Smooth mover", hint: "average score 0.8+ over 3+ sessions", on: sessions >= 3 && q >= 0.8 },
  ];
}
const fmtDur =(s: number) => (s >= 3600 ? `${(s / 3600).toFixed(1)} h` : s >= 60 ? `${Math.round(s / 60)} min` : `${Math.round(s)} s`);

export default function Dashboard() {
  const { user, loading: authLoading } = useAuth();
  const { exercises } = useExercises();
  const [filters, setFilters] = useState<Filters>({});
  const [points, setPoints] = useState<ProgressPoint[] | null>(null);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [weekly, setWeekly] = useState<WeeklySummary | null>(null);
  useEffect(() => {
    if (!user) return;
    Promise.resolve().then(() => api.weekly()).then(setWeekly).catch(() => setWeekly(null)); // optional extra: the page works without it
  }, [user]);

  useEffect(() => {
    if (!user) return;
    setPoints(null); setError(null);
    Promise.all([api.progress(filters), api.summary(filters)])
      .then(([p, s]) => { setPoints(p.points); setSummary(s); })
      .catch((e: Error) => setError(e.message));
  }, [user, filters]);

  const data = useMemo(() => (points ?? []).map((p, i) => ({
    n: i + 1, date: p.started_at, quality: p.quality, flagged: p.error_rate, level: p.level, suggested: p.next_level,
    rom: p.mean_rom_deg != null ? Math.round(p.mean_rom_deg) : null, counted: p.counted_reps ?? 0, target: p.target_reps ?? 0,
  })), [points]);
  const week = useMemo(() => lastSevenDays(points ?? []), [points]);
  const badges = useMemo(() => milestones(summary, weekly), [summary, weekly]);
  const errors = Object.entries(summary?.error_categories ?? {}).map(([k, v]) => ({ name: ERR_LABEL[k] ?? k, count: v }));

  if (authLoading) return <p className="muted">Loading...</p>;
  if (!user) {
    return (
      <section className="card">
        <h1>Dashboard</h1>
        <p>Sign in to see your saved sessions, trends and difficulty history. Guest and demo sessions are not saved.</p>
        <Link className="btn primary" to="/account">Sign in / create account</Link>
      </section>
    );
  }
  const set = (patch: Partial<Filters>) => setFilters((f) => ({ ...f, ...patch }));
  const exportCsv = async (kind: "sessions" | "repetitions") => {
    setBusy(true);
    try { await api.exportCsv(kind, filters); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  return (
    <>
      <h1>Your dashboard</h1>
      <p className="muted">All scores are experimental system metrics from a research prototype, not validated medical outcomes.</p>

      <section className="card filters" aria-label="Filters">
        <label>Exercise{" "}
          <select value={filters.exercise_id ?? ""} onChange={(e) => set({ exercise_id: e.target.value || undefined })}>
            <option value="">All</option>
            {exercises.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
          </select>
        </label>
        <label>From <input type="date" value={filters.from ?? ""} onChange={(e) => set({ from: e.target.value || undefined })} /></label>
        <label>To <input type="date" value={filters.to ?? ""} onChange={(e) => set({ to: e.target.value || undefined })} /></label>
        <label><input type="checkbox" checked={!!filters.include_demo} onChange={(e) => set({ include_demo: e.target.checked })} /> Include synthetic demo sessions</label>
        <span className="row">
          <button onClick={() => exportCsv("sessions")} disabled={busy}>Export sessions CSV</button>
          <button onClick={() => exportCsv("repetitions")} disabled={busy}>Export repetitions CSV</button>
        </span>
      </section>
      {filters.include_demo && <p className="notice">Demo data is included. It is synthetic and does not represent a real person.</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {!error && points === null && <p className="muted">Loading your sessions...</p>}

      {points && points.length === 0 && (
        <section className="card">
          <h2>No saved sessions yet</h2>
          <p>Complete a camera session while signed in and it will appear here. Synthetic demo sessions are never saved to your history.</p>
          <Link className="btn primary" to="/session">Start a session</Link>
        </section>
      )}

      {points && points.length > 0 && summary && (
        <>
          <div className="stats-grid">
            <div className="card stat"><span className="muted">Sessions</span><strong><CountUp value={summary.total_sessions} /></strong></div>
            <div className="card stat"><span className="muted">Repetitions completed</span><strong><CountUp value={summary.completed_repetitions} /></strong></div>
            <div className="card stat"><span className="muted">Average score (0-1)</span><strong>{summary.average_quality_score != null ? summary.average_quality_score.toFixed(2) : "n/a"}</strong></div>
            <div className="card stat"><span className="muted">Time exercising</span><strong>{fmtDur(summary.total_duration_s)}</strong></div>
          </div>
          {weekly && (
            <p className="muted" role="note">
              Last 7 days: {weekly.sessions_last_7_days} session{weekly.sessions_last_7_days === 1 ? "" : "s"} on {weekly.active_days_last_7} day{weekly.active_days_last_7 === 1 ? "" : "s"},
              {" "}{weekly.counted_repetitions_last_7_days} repetitions. Current run: {weekly.day_streak} day{weekly.day_streak === 1 ? "" : "s"} in a row. {weekly.note}
            </p>
          )}
          <section className="card" aria-label="Your week">
            <h2>Your week {weekly && weekly.day_streak > 0 && <span title="Days in a row"><span className="flame" aria-hidden="true">🔥</span> {weekly.day_streak}</span>}</h2>
            <div className="week" role="list" aria-label="Days with a session, oldest first">
              {week.map((d, i) => <span key={d.key} role="listitem" className={`day${d.on ? " on" : ""}`} style={{ "--d": `${i * 70}ms` } as React.CSSProperties} title={`${d.key}${d.on ? ": session" : ""}`}>{d.label}</span>)}
            </div>
            <h3>Milestones <span className="muted" style={{ fontWeight: 400, fontSize: ".85rem" }}>(for fun; not medical)</span></h3>
            <div className="badges">
              {badges.map((b) => <span key={b.name} className={`badge${b.on ? " on" : ""}`} title={b.hint}><span className="ic" aria-hidden="true">{b.icon}</span>{b.name}{!b.on && <span className="muted"> · {b.hint}</span>}</span>)}
            </div>
          </section>
          <div className="grid2">
            <ChartCard title="Score and flagged repetitions" description="Per session; higher score and lower flagged share are better.">
              <TrendLines data={data} domain={[0, 1]} lines={[{ key: "quality", name: "Average score", color: "var(--c1)" }, { key: "flagged", name: "Flagged share", color: "var(--c4)" }]} />
            </ChartCard>
            <ChartCard title="Difficulty level" description="Level played, and the level suggested afterwards.">
              <TrendLines data={data} step domain={[1, 3]} lines={[{ key: "level", name: "Level played", color: "var(--c3)" }, { key: "suggested", name: "Suggested next", color: "var(--c2)" }]} />
            </ChartCard>
            <ChartCard title="Movement range" description="Average joint-angle span per repetition, in degrees (2D estimate).">
              <TrendLines data={data} lines={[{ key: "rom", name: "Range (°)", color: "var(--c1)" }]} />
            </ChartCard>
            <ChartCard title="Repetitions" description="Counted versus target, per session.">
              <Bars data={data} xKey="n" bars={[{ key: "counted", name: "Counted", color: "var(--c1)" }, { key: "target", name: "Target", color: "var(--grid)" }]} />
            </ChartCard>
          </div>
          {errors.length > 0
            ? <ChartCard title="Detected issues" description="How many reliably measured repetitions were flagged, by category.">
                <Bars data={errors} xKey="name" bars={[{ key: "count", name: "Repetitions", color: "var(--c4)" }]} />
              </ChartCard>
            : <p className="muted">No flagged repetitions in this selection.</p>}

          <section className="card">
            <h2>Sessions</h2>
            <div className="table-wrap">
              <table className="angles">
                <thead><tr><th>Date</th><th>Exercise</th><th>Level</th><th>Reps</th><th>Score</th><th>Flagged</th><th>Suggested</th><th /></tr></thead>
                <tbody>
                  {[...points].reverse().map((p) => (
                    <tr key={p.session_id}>
                      <td>{new Date(p.started_at).toLocaleString()}{p.is_demo ? " (demo)" : ""}</td>
                      <td>{p.exercise_id.replace("_", " ")}</td><td>{p.level}</td>
                      <td>{p.counted_reps ?? "-"}/{p.target_reps ?? "-"}</td>
                      <td>{p.quality != null ? p.quality.toFixed(2) : "n/a"}</td>
                      <td>{p.error_rate != null ? `${(p.error_rate * 100).toFixed(0)}%` : "n/a"}</td>
                      <td>{p.action ?? "-"}{p.next_level != null ? ` → ${p.next_level}` : ""}</td>
                      <td><Link to={`/sessions/${p.session_id}`}>Details</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </>
  );
}
