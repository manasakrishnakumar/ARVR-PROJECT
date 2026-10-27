import { useEffect, useState } from "react";
import { api } from "./services/api";
import type { Exercise, Health } from "./types/api";
import PoseLab from "./pages/PoseLab";

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.health(), api.exercises()])
      .then(([h, e]) => {
        setHealth(h);
        setExercises(e);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <main className="page">
      <header>
        <h1>ARVR Adaptive Rehabilitation</h1>
        <p className="muted">Vision-based pose estimation with personalized difficulty</p>
      </header>

      <div className="notice" role="note">
        {health?.disclaimer ?? "Research prototype. Not a medical device and not clinically validated."}
      </div>

      <section className="card">
        <h2>Backend status</h2>
        {error && <p className="error">Cannot reach backend: {error}</p>}
        {!error && !health && <p className="muted">Checking...</p>}
        {health && <p>API {health.status} (v{health.version})</p>}
      </section>

      <section className="card">
        <h2>Exercise library</h2>
        {exercises.length === 0 && !error && <p className="muted">No exercises loaded.</p>}
        <ul>
          {exercises.map((x) => (
            <li key={x.id}>
              <strong>{x.name}</strong> <span className="muted">({x.target_joints.join(", ")}) - illustrative targets</span>
            </li>
          ))}
        </ul>
      </section>
      <PoseLab />
    </main>
  );
}

