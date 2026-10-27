import type { CompleteOut } from "../types/api";

const ACTION_TEXT: Record<string, string> = {
  increase: "Suggested: a small step up",
  decrease: "Suggested: a step down",
  maintain: "Suggested: keep the same level",
  pause: "Suggested: take a break",
  reset: "Reset to the default level",
};

export default function RecommendationCard({ result }: { result: CompleteOut }) {
  const r = result.recommendation;
  const m = r.metrics;
  return (
    <section className="card result" aria-label="Session recommendation">
      <h3>{ACTION_TEXT[r.action]}: level {r.next_level}{r.next_level === r.current_level ? "" : ` (was ${r.current_level})`}</h3>
      <ul>{r.reasons.map((x, i) => <li key={i}>{x}</li>)}</ul>
      <p>
        Next session: {r.target_reps} repetitions, reach at least {Math.round(r.range_fraction * 100)}% of the range,
        about {r.min_rep_duration_s.toFixed(1)}s per repetition. Feedback detail: {r.feedback_intensity}.
      </p>
      <p className="muted">
        This session: {m.counted_reps}/{m.target_reps} repetitions counted, {m.n_reliable}/{m.n_reps} measured reliably
        {m.quality != null ? `, average score ${m.quality.toFixed(2)}` : ""}
        {m.error_rate != null ? `, ${(m.error_rate * 100).toFixed(0)}% flagged` : ""}. Scores are experimental system metrics.
      </p>
      <p className="muted">
        {result.saved_to_history
          ? "Saved to your adaptive history."
          : "Not saved to any history (guest or demo session): this judgment used this session alone."}
      </p>
      <p className="notice">{r.safety_note}</p>
    </section>
  );
}
