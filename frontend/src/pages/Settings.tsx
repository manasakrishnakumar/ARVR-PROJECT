import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useExercises } from "../hooks/useExercises";
import { api, tokenStore } from "../services/api";

const AGE_RANGES = ["", "<18", "18-30", "31-45", "46-60", "61-75", "75+"];

export default function Settings() {
  const { user, setUser, signOut, loading } = useAuth();
  const { exercises } = useExercises();
  const nav = useNavigate();
  const [age, setAge] = useState("");
  const [goals, setGoals] = useState("");
  const [audio, setAudio] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [resetEx, setResetEx] = useState("");

  useEffect(() => {
    if (!user) return;
    setAge(user.age_range ?? ""); setGoals(user.goals ?? ""); setAudio(!!user.preferences?.audio_feedback);
  }, [user]);

  const run = async (fn: () => Promise<void>, ok: string) => {
    setMsg(null); setError(null);
    try { await fn(); setMsg(ok); } catch (e) { setError((e as Error).message); }
  };

  return (
    <>
      <h1>Settings & privacy</h1>

      <section className="card">
        <h2>Privacy</h2>
        <ul>
          <li><strong>Camera:</strong> your browser asks for permission each time you start a camera session. Pose estimation runs locally in your browser; video is not uploaded, not stored, and the camera is switched off when you stop.</li>
          <li><strong>What the backend receives:</strong> only joint-angle numbers (and timestamps) for the exercise, sent to the backend running on your own computer.</li>
          <li><strong>What is saved (signed-in users only):</strong> your username and a salted password hash, optional age range and goals text, two preferences, and for each completed session its repetitions, scores and the difficulty suggestion. Guest and demo sessions are not saved.</li>
          <li><strong>Not collected:</strong> medical information, video, images, location. Please do not type medical details into the goals field.</li>
          <li><strong>No cloud services:</strong> no external AI service or analytics is used.</li>
        </ul>
        <p className="notice">Research prototype. Not a medical device, not clinically validated, and not a substitute for professional care. It cannot decide whether an exercise is safe for you.</p>
      </section>

      {loading && <p className="muted">Loading...</p>}
      {!loading && !user && (
        <section className="card">
          <h2>Your account</h2>
          <p>You are using guest mode: nothing is saved. Profile, data export and deletion settings appear when you sign in.</p>
          <Link className="btn primary" to="/account">Sign in / create account</Link>
        </section>
      )}

      {user && (
        <>
          <section className="card">
            <h2>Profile</h2>
            <div className="row">
              <label>Age range{" "}
                <select value={age} onChange={(e) => setAge(e.target.value)}>
                  {AGE_RANGES.map((a) => <option key={a} value={a}>{a || "Prefer not to say"}</option>)}
                </select>
              </label>
              <label>Goals{" "}
                <input value={goals} maxLength={256} onChange={(e) => setGoals(e.target.value)} placeholder="e.g. regain a comfortable arm raise" />
              </label>
              <label><input type="checkbox" checked={audio} onChange={(e) => setAudio(e.target.checked)} /> Spoken feedback by default</label>
              <button className="primary" onClick={() => run(async () => setUser(await api.updateMe({ age_range: age, goals, preferences: { audio_feedback: audio } })), "Saved.")}>Save</button>
            </div>
          </section>

          <section className="card">
            <h2>Your data</h2>
            <div className="row">
              <button onClick={() => run(() => api.exportCsv("sessions"), "Sessions CSV downloaded.")}>Download sessions (CSV)</button>
              <button onClick={() => run(() => api.exportCsv("repetitions"), "Repetitions CSV downloaded.")}>Download repetitions (CSV)</button>
            </div>
            <h3>Adaptive difficulty</h3>
            <p className="muted">Reset an exercise to the safe default level. Your session history stays; the next suggestion starts from the default.</p>
            <div className="row">
              <select value={resetEx} onChange={(e) => setResetEx(e.target.value)} aria-label="Exercise to reset">
                <option value="">Choose an exercise</option>
                {exercises.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
              </select>
              <button disabled={!resetEx} onClick={() => run(async () => { await api.resetAdaptation(resetEx); }, "Reset to the default level.")}>Reset level</button>
            </div>
            <h3>Delete everything</h3>
            <p className="muted">Permanently removes your account, sessions, repetitions and suggestions from this computer. This cannot be undone.</p>
            {!confirmDelete
              ? <button onClick={() => setConfirmDelete(true)}>Delete my account and data</button>
              : <button className="danger" onClick={async () => {
                  try { await api.deleteMe(); tokenStore.set(null); setUser(null); nav("/"); } catch (e) { setError((e as Error).message); }
                }}>Confirm: permanently delete</button>}
            <p><button className="link" onClick={() => void signOut().then(() => nav("/"))}>Sign out</button></p>
          </section>
        </>
      )}
      {msg && <p role="status" className="ok">{msg}</p>}
      {error && <p className="error" role="alert">{error}</p>}
    </>
  );
}
