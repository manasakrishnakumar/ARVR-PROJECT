import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { ProgressPoint } from "../types/api";

export default function ProgressPanel({ refreshKey }: { refreshKey: number }) {
  const [points, setPoints] = useState<ProgressPoint[] | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.progress().then((p) => { setPoints(p.points); setNote(p.note); setError(null); }).catch((e: Error) => setError(e.message));
  }, [refreshKey]);

  return (
    <section className="card" aria-label="Progress">
      <h2>Your sessions</h2>
      {error && <p className="error" role="alert">{error}</p>}
      {!error && points === null && <p className="muted">Loading...</p>}
      {points && points.length === 0 && <p className="muted">No saved sessions yet. Complete a camera session to see it here (demo sessions are never saved to your history).</p>}
      {points && points.length > 0 && (
        <table className="angles">
          <thead><tr><th>Date</th><th>Exercise</th><th>Level</th><th>Reps</th><th>Score</th><th>Flagged</th><th>Then suggested</th></tr></thead>
          <tbody>
            {[...points].reverse().map((p) => (
              <tr key={p.session_id}>
                <td>{new Date(p.started_at).toLocaleString()}</td>
                <td>{p.exercise_id.replace("_", " ")}</td>
                <td>{p.level}</td>
                <td>{p.counted_reps ?? "-"}/{p.target_reps ?? "-"}</td>
                <td>{p.quality != null ? p.quality.toFixed(2) : "n/a"}</td>
                <td>{p.error_rate != null ? `${(p.error_rate * 100).toFixed(0)}%` : "n/a"}</td>
                <td>{p.action ?? "-"}{p.next_level != null ? ` → level ${p.next_level}` : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {note && <p className="muted">{note}</p>}
    </section>
  );
}
