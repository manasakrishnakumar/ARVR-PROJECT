import { Link } from "react-router-dom";
import { useExercises } from "../hooks/useExercises";
import type { Exercise } from "../types/api";

/** Two reference segments meeting at the joint: the grey one at the start angle, the green one at the illustrative target. */
function AngleDiagram({ start, target }: { start: number; target: number }) {
  const cx = 70, cy = 80, len = 56;
  const pt = (deg: number) => {
    const r = ((deg - 90) * Math.PI) / 180; // 0 deg points straight up; angles open clockwise
    return [cx + len * Math.cos(r), cy + len * Math.sin(r)];
  };
  const [sx, sy] = pt(start), [tx, ty] = pt(target);
  return (
    <svg viewBox="0 0 140 110" role="img" aria-label={`Illustrative range from ${start} to ${target} degrees`} className="diagram">
      <line x1={cx} y1={cy} x2={cx} y2={cy - len} stroke="var(--muted)" strokeWidth="3" strokeLinecap="round" />
      <line x1={cx} y1={cy} x2={sx} y2={sy} stroke="var(--muted)" strokeWidth="3" strokeDasharray="4 4" strokeLinecap="round" />
      <line x1={cx} y1={cy} x2={tx} y2={ty} stroke="var(--c1)" strokeWidth="4" strokeLinecap="round" />
      <circle cx={cx} cy={cy} r="5" fill="var(--text)" />
      <text x="4" y="105" fontSize="10" fill="var(--muted)">start {start}°</text>
      <text x="74" y="105" fontSize="10" fill="var(--c1)">target {target}°</text>
    </svg>
  );
}

function Card({ ex }: { ex: Exercise }) {
  return (
    <article className="card exercise">
      <h3>{ex.name}</h3>
      <AngleDiagram start={ex.start_angle_deg} target={ex.target_angle_deg} />
      <p className="muted">Joint: {ex.target_joints.join(", ")}. Measured as the 2D angle at the joint between three body landmarks.</p>
      <p><strong>Things the system can notice:</strong></p>
      <ul>{ex.common_errors.map((e) => <li key={e}>{e}</li>)}</ul>
      <table className="angles">
        <thead><tr><th>Level</th><th>Reps</th><th>Range</th><th>Pace</th></tr></thead>
        <tbody>
          {Object.entries(ex.difficulty_levels).map(([lv, p]) => (
            <tr key={lv}><td>{lv}</td><td>{p.target_reps}</td><td>{Math.round(p.range_fraction * 100)}%</td><td>{p.min_rep_duration_s.toFixed(1)}s+</td></tr>
          ))}
        </tbody>
      </table>
      <p className="muted">Illustrative values only, not medically prescribed targets. Your professional decides what is right for you.</p>
      <Link className="btn primary" to={`/session?exercise=${ex.id}`}>Practice this</Link>
    </article>
  );
}

export default function Library() {
  const { exercises, error, loading } = useExercises();
  return (
    <>
      <h1>Exercise library</h1>
      <p className="muted">Exercises are defined in configuration files on the backend, so more can be added without changing the app code.</p>
      {loading && <p className="muted">Loading exercises...</p>}
      {error && <p className="error" role="alert">Could not load exercises: {error}</p>}
      {!loading && !error && exercises.length === 0 && <p className="muted">No exercises available.</p>}
      <div className="grid3">{exercises.map((e) => <Card key={e.id} ex={e} />)}</div>
    </>
  );
}
