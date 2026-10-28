import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Bars, ChartCard } from "../components/Charts";
import { api } from "../services/api";
import type { SessionDetail } from "../types/api";

const LABELS: Record<string, string> = {
  acceptable: "Acceptable", insufficient_range: "Range short", incomplete_repetition: "Incomplete",
  too_fast: "Too fast", uncontrolled: "Uncontrolled", insufficient_data: "Not enough data",
};

export default function SessionSummary() {
  const { id = "" } = useParams();
  const [s, setS] = useState<SessionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.sessionDetail(id).then(setS).catch((e: Error) => setError(e.message));
  }, [id]);

  if (error) return <section className="card"><p className="error" role="alert">Could not load this session: {error}</p><Link to="/dashboard">Back to dashboard</Link></section>;
  if (!s) return <p className="muted">Loading session...</p>;

  const m = s.summary.metrics;
  const reps = s.repetitions.map((r) => ({ rep: `#${r.index}`, score: r.score ?? 0, range: r.range_of_motion_deg ?? 0 }));
  return (
    <>
      <h1>Session summary</h1>
      <p className="muted">
        {s.exercise_id.replace("_", " ")} · level {s.difficulty} · {new Date(s.started_at).toLocaleString()}
        {s.is_demo && " · SYNTHETIC DEMO (not a real person; never saved to a history)"}
      </p>
      {(s.pain != null || s.note) && (
        <p>{s.pain != null && <>Reported pain: <strong>{s.pain}/10</strong>. </>}{s.note && <>Note: {s.note}</>}</p>
      )}
      {!m && <p className="notice">This session was not completed, so there is no summary.</p>}
      {m && (
        <div className="stats-grid">
          <div className="card stat"><span className="muted">Repetitions counted</span><strong>{m.counted_reps}/{m.target_reps}</strong></div>
          <div className="card stat"><span className="muted">Measured reliably</span><strong>{m.n_reliable}/{m.n_reps}</strong></div>
          <div className="card stat"><span className="muted">Average score</span><strong>{m.quality != null ? m.quality.toFixed(2) : "n/a"}</strong></div>
          <div className="card stat"><span className="muted">Flagged repetitions</span><strong>{m.error_rate != null ? `${(m.error_rate * 100).toFixed(0)}%` : "n/a"}</strong></div>
        </div>
      )}
      {s.decision && (
        <section className="card result">
          <h2>Suggestion: {s.decision.action} (level {s.decision.from_level} → {s.decision.to_level})</h2>
          <ul>{s.decision.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
          <p className="muted">A software suggestion for a research prototype, not a clinical decision.</p>
        </section>
      )}
      {reps.length > 0 && (
        <ChartCard title="Score and range per repetition" description="Score is 0-1 (rule-based, experimental); range is the joint-angle span in degrees (2D estimate).">
          <Bars data={reps} xKey="rep" bars={[{ key: "score", name: "Score", color: "var(--c1)" }, { key: "range", name: "Range (°)", color: "var(--c2)" }]} />
        </ChartCard>
      )}
      <section className="card">
        <h2>Repetitions</h2>
        {s.repetitions.length === 0 && <p className="muted">No repetitions were recorded.</p>}
        {s.repetitions.length > 0 && (
          <div className="table-wrap">
            <table className="angles">
              <thead><tr><th>#</th><th>Result</th><th>Score</th><th>Range</th><th>Time</th><th>Counted</th><th>Reliable</th></tr></thead>
              <tbody>
                {s.repetitions.map((r) => (
                  <tr key={r.index}>
                    <td>{r.index}</td><td>{LABELS[r.label ?? ""] ?? r.label ?? "n/a"}</td>
                    <td>{r.score != null ? r.score.toFixed(2) : "n/a"}</td>
                    <td>{r.range_of_motion_deg != null ? `${r.range_of_motion_deg.toFixed(0)}°` : "n/a"}</td>
                    <td>{r.duration_s != null ? `${r.duration_s.toFixed(1)}s` : "n/a"}</td>
                    <td>{r.counted ? "yes" : "no"}</td><td>{r.reliable ? "yes" : "no"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <p className="muted print-only">Printed from ARVR, a research prototype and not a medical device. Scores are experimental system metrics, not validated medical outcomes. Share with your rehabilitation professional if you wish; it is not a clinical report.</p>
      <div className="row no-print"><button onClick={() => window.print()}>Print or save as PDF</button><Link className="btn" to="/session">New session</Link><Link className="btn" to="/dashboard">Dashboard</Link></div>
    </>
  );
}
