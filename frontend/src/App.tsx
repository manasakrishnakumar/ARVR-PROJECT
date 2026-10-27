import { useCallback, useEffect, useState } from "react";
import AccountPanel from "./components/AccountPanel";
import ProgressPanel from "./components/ProgressPanel";
import PoseLab from "./pages/PoseLab";
import { api, ApiError, tokenStore } from "./services/api";
import type { Exercise, Health, User } from "./types/api";

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [progressKey, setProgressKey] = useState(0);

  useEffect(() => {
    Promise.all([api.health(), api.exercises()])
      .then(([h, e]) => {
        setHealth(h);
        setExercises(e);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  // restore a previous sign-in; an expired or invalid token silently falls back to guest mode
  useEffect(() => {
    if (!tokenStore.get()) return;
    api.me().then(setUser).catch((e) => { if (e instanceof ApiError && e.status === 401) tokenStore.set(null); });
  }, []);

  const onSessionSaved = useCallback(() => setProgressKey((k) => k + 1), []);

  return (
    <main className="page">
      <header>
        <h1>ARVR Adaptive Rehabilitation</h1>
        <p className="muted">Vision-based pose estimation with personalized difficulty</p>
      </header>

      <div className="notice" role="note">
        {health?.disclaimer ?? "Research prototype. Not a medical device and not clinically validated."}
      </div>

      <AccountPanel user={user} onUser={setUser} />

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

      <PoseLab exercises={exercises} user={user} onSessionSaved={onSessionSaved} />
      {user && <ProgressPanel refreshKey={progressKey} />}
    </main>
  );
}
