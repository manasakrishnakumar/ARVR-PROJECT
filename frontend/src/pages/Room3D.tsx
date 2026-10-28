import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import RecommendationCard from "../components/RecommendationCard";
import Scene3D, { SceneBoundary } from "../components/Avatar3D";
import { useAuth } from "../context/AuthContext";
import { useExerciseStream } from "../hooks/useExerciseStream";
import { useExercises } from "../hooks/useExercises";
import { api } from "../services/api";
import { trainerPose, trainerProgress } from "../pose/trainer";
import { buildRelayFrame, newRoomCode, RelayPublisher } from "../services/relay";
import type { Landmark } from "../pose/types";
import { repCue, speak } from "../pose/speech";
import { hudText } from "../pose/xr";

/** Desktop 3D rehabilitation room: a virtual trainer demonstrates the movement beside an avatar that mirrors you.
 *  Works in any browser without a headset. The pose pipeline is independent of the 3D scene: if 3D fails, counting and feedback continue. */
export default function Room3D() {
  const { exercises, loading } = useExercises();
  const { user } = useAuth();
  const [exerciseId, setExerciseId] = useState("elbow_flexion");
  const [level, setLevel] = useState(1);
  const videoRef = useRef<HTMLVideoElement>(null);
  const trainerRef = useRef<Landmark[] | null>(null);
  const exercise = exercises.find((e) => e.id === exerciseId) ?? null;
  const s = useExerciseStream(exercise, level, videoRef);

  // signed-in users start at the suggested level
  useEffect(() => {
    if (!user || s.mode !== "idle") return;
    api.adaptationState(exerciseId).then((a) => setLevel(a.recommended_level)).catch(() => undefined);
  }, [user, exerciseId, s.mode]);

  // the virtual trainer loops the exercise's illustrative movement
  useEffect(() => {
    if (!exercise) return;
    let raf = 0;
    const t0 = performance.now();
    const tick = () => { trainerRef.current = trainerPose(exercise, "LEFT", trainerProgress((performance.now() - t0) / 1000)); raf = requestAnimationFrame(tick); };
    tick();
    return () => cancelAnimationFrame(raf);
  }, [exercise]);

  // optional: share the live pose with the Unity client (numbers only, through the local backend)
  const [share, setShare] = useState(false);
  const [room, setRoom] = useState("");
  const [relayStatus, setRelayStatus] = useState("not sharing");
  const latest = useRef({ live: s.live, lastRep: s.lastRep, targetReps: s.targetReps });
  latest.current = { live: s.live, lastRep: s.lastRep, targetReps: s.targetReps };
  useEffect(() => {
    if (!share || !room) { setRelayStatus("not sharing"); return; }
    const pub = new RelayPublisher(room, (st, detail) => setRelayStatus(st === "open" ? "sharing: waiting for Unity" : st === "connecting" ? "connecting..." : `stopped${detail ? ` (${detail})` : ""}`));
    const timer = setInterval(() => {
      const lm = s.landmarksRef.current;
      if (!lm) return;
      const { live, lastRep, targetReps } = latest.current;
      pub.publish(buildRelayFrame(lm, { angle: s.angleRef.current, phase: live?.phase ?? "waiting", countedReps: live?.counted_reps ?? 0,
        targetReps, feedback: lastRep?.feedback ?? "", label: lastRep?.label ?? "" }));
    }, 66);
    return () => { clearInterval(timer); pub.close(); };
  }, [share, room, s.landmarksRef, s.angleRef]);

  const [voice, setVoice] = useState(false);
  const voiceRef = useRef(false);
  voiceRef.current = voice;
  useEffect(() => {
    if (voiceRef.current && s.lastRep) speak(repCue(s.lastRep, s.live?.counted_reps ?? s.repCount, s.targetReps));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s.lastRep]);
  const hudRef = useRef<string[]>([]);
  hudRef.current = hudText(s.live?.counted_reps ?? 0, s.targetReps, s.live?.phase ?? "waiting", s.lastRep?.feedback ?? "");
  const running = s.mode !== "idle";
  if (loading) return <p className="muted">Loading...</p>;
  const lv = exercise?.difficulty_levels ?? {};
  return (
    <>
      <h1>3D rehabilitation room</h1>
      <p className="muted">
        Desktop 3D view (no headset needed). The amber figure is a virtual trainer showing the illustrative movement; the teal figure mirrors you.
        An experimental Enter VR button appears below the view when the browser reports a VR headset (untested without one).
      </p>
      <div className="row">
        <label>Exercise{" "}
          <select value={exerciseId} disabled={running} onChange={(e) => { setExerciseId(e.target.value); setLevel(1); }}>
            {exercises.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
          </select>
        </label>
        <label>Level{" "}
          <select value={level} disabled={running} onChange={(e) => setLevel(Number(e.target.value))}>
            {Object.keys(lv).map((l) => <option key={l} value={l}>Level {l}</option>)}
          </select>
        </label>
        <button className="primary" onClick={() => void s.startCamera()} disabled={running}>Start camera</button>
        <button onClick={s.startDemo} disabled={running}>Synthetic demo</button>
        <button onClick={() => void s.stopAndSave()} disabled={!running}>Stop and save</button>
        <label><input type="checkbox" checked={voice} onChange={(e) => setVoice(e.target.checked)} /> Voice cues</label>
      </div>
      {s.error && <p className="error" role="alert">{s.error}</p>}
      {s.sock === "failed" && <p className="error" role="alert">Analysis backend unreachable: movement is shown but repetitions are not counted.</p>}

      <video ref={videoRef} className="hidden" playsInline muted />
      <SceneBoundary fallback={<p className="notice error-banner" role="alert">The 3D view could not start (WebGL may be unavailable). Counting and feedback below still work; you can also use the Live session page.</p>}>
        <Scene3D user={s.landmarksRef} trainer={trainerRef} hud={hudRef} />
      </SceneBoundary>

      <div className="stats-grid">
        <div className="card stat"><span className="muted">Repetitions</span><strong>{s.live?.counted_reps ?? 0}/{s.targetReps || "-"}</strong></div>
        <div className="card stat"><span className="muted">Phase</span><strong style={{ fontSize: "1.2rem", textTransform: "capitalize" }}>{s.live ? s.live.phase.replace("_", " ") : "waiting"}</strong></div>
        <div className="card stat"><span className="muted">Last repetition</span><strong style={{ fontSize: "1.2rem" }}>{s.lastRep ? `${s.lastRep.label.replace("_", " ")}${s.lastRep.score != null ? ` (${s.lastRep.score.toFixed(2)})` : ""}` : "-"}</strong></div>
        <div className="card stat"><span className="muted">Level</span><strong>{level}</strong></div>
      </div>
      <p className="feedback" aria-live="polite">{s.live?.calibrating ? "Calibrating: do 2 or 3 slow, comfortable repetitions (about 5 seconds)." : s.poseWarn ? "Pose not detected clearly. Adjust your position." : s.lastRep?.feedback ?? "Start the camera or the demo."}</p>
      {s.calibrated && <p className="muted">Calibrated range: {s.calibrated.start.toFixed(0)}° to {s.calibrated.target.toFixed(0)}° (what you demonstrated, not a target).</p>}
      {s.result && <RecommendationCard result={s.result} sessionId={s.sessionId} />}
      {s.sessionId && <p><Link className="btn" to={`/sessions/${s.sessionId}`}>View the full session summary</Link></p>}
      <section className="card">
        <h2>Show this session in Unity (optional)</h2>
        <p className="muted">Sends your pose as numbers (no video or image) to the backend on this computer, which forwards it to the Unity client that joins the same room code.
          Do not share the code or expose the backend to the internet.</p>
        <label><input type="checkbox" checked={share} onChange={(e) => { setShare(e.target.checked); if (e.target.checked && !room) setRoom(newRoomCode()); }} /> Share live pose</label>
        {share && <p>Room code: <strong style={{ letterSpacing: 2 }}>{room}</strong> · {relayStatus}</p>}
        {share && <p className="muted">In Unity, choose "Live from browser", type this code and press Start. Start the camera here first.</p>}
      </section>
      <p className="muted">Targets are illustrative, not prescribed. Research prototype, not a medical device.</p>
    </>
  );
}
