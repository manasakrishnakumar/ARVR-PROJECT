import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import RecommendationCard from "../components/RecommendationCard";
import { bodyAngles, isotropic, jointAngle, MIN_CONFIDENCE, type JointAngles } from "../pose/angles";
import { DemoEstimator } from "../pose/demo";
import { MediaPipeEstimator } from "../pose/mediapipe";
import { drawSkeleton } from "../pose/draw";
import { LANDMARK_INDEX, type PoseEstimator } from "../pose/types";
import { api } from "../services/api";
import { AnalysisSocket, type RepMsg, type SocketStatus, type StateMsg } from "../services/analysisSocket";
import type { AdaptationState, CompleteOut, Exercise, SessionCreated, User } from "../types/api";

type Mode = "idle" | "camera" | "demo";
const SEND_INTERVAL_MS = 66; // ~15 Hz is plenty for rep counting

const LABELS: Record<string, string> = {
  acceptable: "Acceptable", insufficient_range: "Range short", incomplete_repetition: "Incomplete",
  too_fast: "Too fast", uncontrolled: "Uncontrolled", insufficient_data: "Not enough data",
};

interface Props {
  exercises: Exercise[];
  user: User | null;
  initialExerciseId?: string;
  onSessionSaved?: () => void;
}

export default function PoseLab({ exercises, user, initialExerciseId, onSessionSaved }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const estRef = useRef<PoseEstimator | null>(null);
  const rafRef = useRef(0);
  const streamRef = useRef<MediaStream | null>(null);
  const sockRef = useRef<AnalysisSocket | null>(null);
  const sessionRef = useRef<SessionCreated | null>(null);
  const repCountRef = useRef(0);
  const pausedRef = useRef(false);
  const exRef = useRef<Exercise | null>(null);
  const t0Ref = useRef(0);
  const lastSendRef = useRef(0);
  const nullSinceRef = useRef<number | null>(null);
  const poseWarnRef = useRef(false);
  const audioRef = useRef(false);

  const [mode, setMode] = useState<Mode>("idle");
  const [paused, setPaused] = useState(false);
  const [status, setStatus] = useState("Not started");
  const [error, setError] = useState<string | null>(null);
  const [angles, setAngles] = useState<JointAngles[]>([]);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState("");

  const [exerciseId, setExerciseId] = useState(
    initialExerciseId && exercises.some((e) => e.id === initialExerciseId) ? initialExerciseId : "elbow_flexion");
  const [lastSessionId, setLastSessionId] = useState<string | null>(null);
  const [difficulty, setDifficulty] = useState(1);
  const [adaptive, setAdaptive] = useState<AdaptationState | null>(null);
  const [live, setLive] = useState<StateMsg | null>(null);
  const [targetReps, setTargetReps] = useState(0);
  const [reps, setReps] = useState<RepMsg[]>([]);
  const [feedback, setFeedback] = useState<string>("");
  const [sockStatus, setSockStatus] = useState<SocketStatus | "none">("none");
  const [poseWarn, setPoseWarn] = useState(false);
  const [audio, setAudio] = useState(false);
  const [result, setResult] = useState<CompleteOut | null>(null);
  const [saving, setSaving] = useState(false);

  const exercise = exercises.find((e) => e.id === exerciseId) ?? null;
  const levels = exercise ? Object.keys(exercise.difficulty_levels) : ["1"];
  const running = mode !== "idle";

  useEffect(() => { audioRef.current = audio; }, [audio]);
  useEffect(() => { if (user) setAudio(!!user.preferences?.audio_feedback); }, [user]); // spoken feedback default from settings

  // signed-in users start at the level the adaptive controller suggested after their last session
  useEffect(() => {
    if (running) return;
    if (!user) { setAdaptive(null); setDifficulty(1); return; }
    api.adaptationState(exerciseId)
      .then((s) => { setAdaptive(s); setDifficulty(s.recommended_level); })
      .catch(() => setAdaptive(null));
  }, [user, exerciseId, running, result]);

  const finishSession = useCallback(async () => {
    const s = sessionRef.current;
    sessionRef.current = null;
    if (!s || repCountRef.current === 0) return; // nothing was exercised: leave no record
    setSaving(true);
    try {
      setResult(await api.completeSession(s.id));
      setLastSessionId(s.id);
      onSessionSaved?.();
    } catch (e) {
      setError(`Could not save the session summary: ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  }, [onSessionSaved]);

  const stop = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop()); // camera shutdown
    streamRef.current = null;
    sockRef.current?.close();
    sockRef.current = null;
    estRef.current?.close();
    estRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    const c = canvasRef.current;
    if (c) c.getContext("2d")!.clearRect(0, 0, c.width, c.height);
    pausedRef.current = false;
    poseWarnRef.current = false;
    nullSinceRef.current = null;
    setMode("idle"); setPaused(false); setAngles([]); setStatus("Stopped");
    setSockStatus("none"); setPoseWarn(false); setLive(null);
  }, []);

  const stopAndSave = useCallback(async () => {
    stop();
    await finishSession();
  }, [stop, finishSession]);

  useEffect(() => stop, [stop]);

  const speak = (text: string) => {
    if (audioRef.current && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
    }
  };

  const openSession = async (isDemo: boolean) => {
    exRef.current = exercise;
    t0Ref.current = performance.now();
    lastSendRef.current = 0;
    repCountRef.current = 0;
    setReps([]); setFeedback(""); setLive(null); setResult(null);
    // the session record lets the server save repetitions and later judge the session; the pose stream still works without it
    sessionRef.current = await api.createSession(exerciseId, difficulty, isDemo).catch(() => null);
    const s = sessionRef.current;
    sockRef.current = new AnalysisSocket(exerciseId, difficulty, (m) => {
      if (m.type === "hello") setTargetReps(m.target_reps);
      else if (m.type === "state") setLive(m);
      else if (m.type === "rep") {
        repCountRef.current += 1;
        setReps((r) => [...r, m]);
        setFeedback(m.feedback); // once per repetition, never per frame
        speak(m.feedback);
      }
    }, setSockStatus, s ? { id: s.id, key: s.ws_key } : undefined);
  };

  const loop = useCallback((m: Mode) => {
    let lastTs = -1;
    const tick = () => {
      rafRef.current = requestAnimationFrame(tick);
      const est = estRef.current, video = videoRef.current, canvas = canvasRef.current;
      if (!est || !canvas || pausedRef.current) return;
      const ts = performance.now();
      if (ts <= lastTs) return;
      if (m === "camera" && (!video || video.readyState < 2)) return;
      lastTs = ts;
      const frame = est.detect(video, ts);
      drawSkeleton(canvas, frame, m === "camera");

      // exercise angle -> backend (which owns counting and assessment)
      const ex = exRef.current;
      const aspect = m === "camera" && video && video.videoHeight ? video.videoWidth / video.videoHeight : 1;
      const lms = frame.landmarks ? isotropic(frame.landmarks, aspect) : null; // demo poses are already isotropic
      let exAngle: number | null = null;
      if (lms && ex) {
        const [a, b, c] = ex.landmarks.map((n) => lms[LANDMARK_INDEX[n]]);
        exAngle = jointAngle(a, b, c);
      }
      if (ts - lastSendRef.current >= SEND_INTERVAL_MS) {
        lastSendRef.current = ts;
        sockRef.current?.send((ts - t0Ref.current) / 1000, exAngle);
      }
      if (exAngle === null) {
        nullSinceRef.current ??= ts;
        if (ts - nullSinceRef.current > 1000 && !poseWarnRef.current) { poseWarnRef.current = true; setPoseWarn(true); }
      } else {
        nullSinceRef.current = null;
        if (poseWarnRef.current) { poseWarnRef.current = false; setPoseWarn(false); }
      }

      if (!lms) { setStatus("No person detected. Step into view."); setAngles([]); return; }
      const conf = lms.filter((l) => l.visibility >= MIN_CONFIDENCE).length;
      setStatus(`Tracking: ${conf}/33 landmarks above confidence ${MIN_CONFIDENCE}`);
      setAngles(bodyAngles(lms));
    };
    tick();
  }, []);

  const startDemo = async () => {
    stop();
    canvasRef.current!.width = 640;
    canvasRef.current!.height = 480;
    setError(null);
    await openSession(true);
    estRef.current = new DemoEstimator();
    setMode("demo"); loop("demo");
  };

  const startCamera = async () => {
    stop(); setError(null); setStatus("Requesting camera...");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: deviceId ? { deviceId: { exact: deviceId } } : { width: 640, height: 480 }, audio: false,
      });
      streamRef.current = stream;
      setDevices((await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "videoinput"));
      stream.getVideoTracks()[0].addEventListener("ended", () => { void stopAndSave(); setError("Camera disconnected."); });
      const v = videoRef.current!;
      v.srcObject = stream;
      await v.play();
      canvasRef.current!.width = v.videoWidth || 640;
      canvasRef.current!.height = v.videoHeight || 480;
      setStatus("Loading pose model...");
      estRef.current = await MediaPipeEstimator.create();
      await openSession(false);
      setMode("camera"); loop("camera");
    } catch (e) {
      stop();
      const err = e as Error;
      setError(
        err.name === "NotAllowedError" ? "Camera permission denied."
          : err.name === "NotFoundError" ? "No camera found. Try the synthetic demo."
          : err.message,
      );
    }
  };

  const togglePause = () => { pausedRef.current = !pausedRef.current; setPaused(pausedRef.current); };
  const resetLevel = async () => {
    try { await api.resetAdaptation(exerciseId); setResult(null); } catch (e) { setError((e as Error).message); }
  };
  const count = live?.counted_reps ?? 0;
  const progress = Math.max(0, Math.min(1, live?.progress ?? 0));
  const message = poseWarn ? "Pose not detected clearly. Adjust your position."
    : targetReps && count >= targetReps ? "Target repetitions reached. Take a break if you feel discomfort."
    : feedback;

  return (
    <section className="card">
      <h2>Live session</h2>
      <p className="muted">
        Pose estimation runs locally in your browser; only joint angles (numbers) go to the local backend.
        No video is uploaded or stored. Angles are 2D image-plane estimates, not clinical measurements.
      </p>
      <div className="row">
        <label>Exercise{" "}
          <select value={exerciseId} onChange={(e) => { setExerciseId(e.target.value); setDifficulty(1); setResult(null); }} disabled={running}>
            {exercises.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
          </select>
        </label>
        <label>Level{" "}
          <select value={difficulty} onChange={(e) => setDifficulty(Number(e.target.value))} disabled={running}>
            {levels.map((l) => <option key={l} value={l}>Level {l}{adaptive && Number(l) === adaptive.recommended_level ? " (suggested)" : ""}</option>)}
          </select>
        </label>
        <label><input type="checkbox" checked={audio} onChange={(e) => setAudio(e.target.checked)} /> Audio feedback</label>
      </div>
      {adaptive && adaptive.source === "history" && (
        <p className="muted">
          Suggested level {adaptive.recommended_level} after your last session ({adaptive.last_action}).
          {adaptive.last_reasons[0] ? ` ${adaptive.last_reasons[0]}` : ""} You can choose another level; it is a suggestion only.{" "}
          <button className="link" onClick={resetLevel} disabled={running}>Reset to default level</button>
        </p>
      )}
      {!user && <p className="muted">Guest mode: level suggestions need an account, so the default level is used.</p>}
      <div className="row">
        <button onClick={startCamera}>Start camera</button>
        <button onClick={startDemo}>Synthetic demo</button>
        <button onClick={togglePause} disabled={!running}>{paused ? "Resume" : "Pause"}</button>
        <button onClick={() => void stopAndSave()} disabled={!running}>Stop and save</button>
        {devices.length > 1 && (
          <select value={deviceId} onChange={(e) => setDeviceId(e.target.value)} aria-label="Camera">
            {devices.map((d, i) => <option key={d.deviceId} value={d.deviceId}>{d.label || `Camera ${i + 1}`}</option>)}
          </select>
        )}
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {(sockStatus === "failed") && <p className="error" role="alert">Analysis backend unreachable: pose is shown but reps are not counted. Start the backend and restart the session.</p>}
      <p aria-live="polite"><strong>Status:</strong> {status}{mode === "demo" && " (synthetic data, not a real person; only elbow flexion moves; demo sessions are never saved to your history)"}</p>

      <div className="session">
        <div className="stage">
          <video ref={videoRef} className={mode === "camera" ? "mirror" : "hidden"} playsInline muted />
          <canvas ref={canvasRef} className="overlay" width={640} height={480} />
        </div>
        <div className="stats">
          <div className="big" aria-label="Repetitions">{count}<span className="muted"> / {targetReps || "-"} reps</span></div>
          <div className="chip">{live ? live.phase.replace("_", " ") : "waiting"}</div>
          <div className="bar" aria-label="Movement progress"><div style={{ width: `${progress * 100}%` }} /></div>
          <p className="muted">Angle {live?.angle != null ? `${live.angle.toFixed(0)}°` : "n/a"} · Level {difficulty}{exercise?.illustrative_only ? " · illustrative targets" : ""}</p>
          <p className="feedback" aria-live="polite">{message || "Start moving to begin."}</p>
        </div>
      </div>

      {saving && <p className="muted">Saving session...</p>}
      {result && <RecommendationCard result={result} />}
      {result && lastSessionId && <p><Link className="btn" to={`/sessions/${lastSessionId}`}>View the full session summary</Link></p>}

      <h3>Repetitions</h3>
      <table className="angles">
        <thead><tr><th>#</th><th>Result</th><th>Score</th><th>Range</th><th>Time</th><th>Why</th></tr></thead>
        <tbody>
          {reps.length === 0 && <tr><td colSpan={6} className="muted">None yet</td></tr>}
          {reps.map((r) => (
            <tr key={r.index}>
              <td>{r.index}</td><td>{LABELS[r.label] ?? r.label}{r.counted ? "" : " (not counted)"}</td>
              <td>{r.score == null ? "n/a" : r.score.toFixed(2)}</td>
              <td>{r.features.rom_deg?.toFixed(0)}°</td><td>{r.features.duration_s?.toFixed(1)}s</td><td className="muted">{r.explanation}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Joint angles</h3>
      <table className="angles">
        <thead><tr><th>Joint</th><th>Angle</th></tr></thead>
        <tbody>
          {angles.length === 0 && <tr><td colSpan={2} className="muted">No data</td></tr>}
          {angles.map((a) => (
            <tr key={a.label}><td>{a.label}</td><td>{a.angle === null ? "n/a (unreliable)" : `${a.angle.toFixed(0)}°`}</td></tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
