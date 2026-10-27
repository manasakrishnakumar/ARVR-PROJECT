import { useCallback, useEffect, useRef, useState } from "react";
import { buildRecording, fileName, frameRow, MAX_SECONDS, validateMeta, type Intended, type Recording } from "../collect/recording";
import { useExercises } from "../hooks/useExercises";
import { MIN_CONFIDENCE } from "../pose/angles";
import { DemoEstimator } from "../pose/demo";
import { drawSkeleton } from "../pose/draw";
import { MediaPipeEstimator } from "../pose/mediapipe";
import type { PoseEstimator } from "../pose/types";

type Mode = "idle" | "camera" | "demo";

function download(rec: Recording, n: number) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(rec)], { type: "application/json" }));
  const a = document.createElement("a");
  a.href = url; a.download = fileName(rec, n); a.click();
  URL.revokeObjectURL(url);
}

/** Records landmark coordinates (numbers only) for research use. No video or image is captured or stored, nothing is uploaded,
 *  and recordings exist only in this page until you download them. */
export default function Collect() {
  const { exercises } = useExercises();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const estRef = useRef<PoseEstimator | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef(0);
  const framesRef = useRef<[number, number[][]][]>([]);
  const recordingRef = useRef(false);
  const t0Ref = useRef(0);

  const [consent, setConsent] = useState(false);
  const [code, setCode] = useState("");
  const [exerciseId, setExerciseId] = useState("");
  const [side, setSide] = useState<"left" | "right">("right");
  const [intended, setIntended] = useState<Intended>({ label: "correct", error: "" });
  const [mode, setMode] = useState<Mode>("idle");
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [frames, setFrames] = useState(0);
  const [visible, setVisible] = useState<number | null>(null);
  const [saved, setSaved] = useState<Recording[]>([]);
  const [problems, setProblems] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const exercise = exercises.find((e) => e.id === exerciseId) ?? null;
  const errorOptions = exercise?.common_errors ?? [];

  const finish = useCallback((synthetic: boolean) => {
    recordingRef.current = false;
    setRecording(false);
    const f = framesRef.current;
    framesRef.current = [];
    if (f.length < 30) { setError("Recording too short (fewer than 30 frames); discarded."); return; }
    const v = videoRef.current;
    setSaved((s) => [...s, buildRecording({
      participant_code: code, exercise_id: exerciseId, side, intended, synthetic,
      camera: { width: v?.videoWidth || 640, height: v?.videoHeight || 480 },
      model: synthetic ? "synthetic-demo" : "pose_landmarker_lite (MediaPipe, in-browser)",
    }, f)]);
  }, [code, exerciseId, side, intended]);

  const stopAll = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop()); // camera shutdown
    streamRef.current = null;
    estRef.current?.close();
    estRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    const c = canvasRef.current;
    if (c) c.getContext("2d")!.clearRect(0, 0, c.width, c.height);
    setMode("idle");
  }, []);
  useEffect(() => stopAll, [stopAll]);

  const loop = useCallback((m: Mode) => {
    let lastUi = 0;
    const tick = () => {
      rafRef.current = requestAnimationFrame(tick);
      const est = estRef.current, video = videoRef.current, canvas = canvasRef.current;
      if (!est || !canvas) return;
      if (m === "camera" && (!video || video.readyState < 2)) return;
      const ts = performance.now();
      const frame = est.detect(video, ts);
      drawSkeleton(canvas, frame, m === "camera");
      if (recordingRef.current) {
        const t = (ts - t0Ref.current) / 1000;
        if (frame.landmarks) framesRef.current.push(frameRow(t, frame.landmarks));
        if (t >= MAX_SECONDS) finish(m === "demo");
        if (ts - lastUi > 200) {
          lastUi = ts;
          setSeconds(Math.round(t)); setFrames(framesRef.current.length);
          setVisible(frame.landmarks ? frame.landmarks.filter((l) => l.visibility >= MIN_CONFIDENCE).length : 0);
        }
      }
    };
    tick();
  }, [finish]);

  const start = async (m: Mode) => {
    const p = validateMeta({ participant_code: code, exercise_id: exerciseId, intended }, consent, errorOptions);
    setProblems(p); setError(null);
    if (p.length) return;
    stopAll();
    try {
      if (m === "demo") {
        canvasRef.current!.width = 640; canvasRef.current!.height = 480;
        estRef.current = new DemoEstimator();
      } else {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
        streamRef.current = stream;
        const v = videoRef.current!;
        v.srcObject = stream; await v.play();
        canvasRef.current!.width = v.videoWidth || 640; canvasRef.current!.height = v.videoHeight || 480;
        estRef.current = await MediaPipeEstimator.create();
      }
      setMode(m); loop(m);
    } catch (e) {
      stopAll();
      const err = e as Error;
      setError(err.name === "NotAllowedError" ? "Camera permission denied." : err.name === "NotFoundError" ? "No camera found." : err.message);
    }
  };

  const toggleRecord = () => {
    if (recording) { finish(mode === "demo"); return; }
    framesRef.current = []; t0Ref.current = performance.now(); setSeconds(0); setFrames(0);
    recordingRef.current = true; setRecording(true);
  };

  return (
    <>
      <h1>Record movement data (research)</h1>
      <section className="card">
        <h2>What this records</h2>
        <ul>
          <li><strong>Only numbers:</strong> body-landmark coordinates and timestamps. <strong>No video and no images</strong> are captured or stored.</li>
          <li>Recordings stay inside this page until you download them as files. <strong>Nothing is uploaded.</strong> Leaving the page discards recordings you have not downloaded.</li>
          <li>Use a participant <strong>code</strong> (for example P01), never a name. Body-movement data can still be personal: keep the files private and delete them when no longer needed.</li>
          <li>Record only yourself, or people who have agreed to take part after being told what is recorded and why. For any real study, get the approval your institution requires.</li>
        </ul>
        <label><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /> I understand this, and everyone being recorded has agreed.</label>
      </section>

      <section className="card">
        <h2>Recording details</h2>
        <div className="row">
          <label>Participant code <input value={code} maxLength={16} onChange={(e) => setCode(e.target.value)} placeholder="P01" /></label>
          <label>Exercise{" "}
            <select value={exerciseId} onChange={(e) => { setExerciseId(e.target.value); setIntended({ label: "correct", error: "" }); }}>
              <option value="">Choose...</option>
              {exercises.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
            </select>
          </label>
          <label>Side{" "}
            <select value={side} onChange={(e) => setSide(e.target.value as "left" | "right")}>
              <option value="right">Right</option><option value="left">Left</option>
            </select>
          </label>
          <label>Performed{" "}
            <select value={intended.label === "correct" ? "correct" : intended.error} onChange={(e) => setIntended(e.target.value === "correct" ? { label: "correct", error: "" } : { label: "error", error: e.target.value })}>
              <option value="correct">Correctly</option>
              {errorOptions.map((x) => <option key={x} value={x}>With error: {x}</option>)}
              {exerciseId && <option value="other">With another error</option>}
            </select>
          </label>
        </div>
        <p className="muted">Record several repetitions per take (for example 5 to 10) in good light, facing the camera for arm exercises or side-on for squats. Label each take by what was done on purpose.</p>
        {problems.length > 0 && <ul className="error" role="alert">{problems.map((p) => <li key={p}>{p}</li>)}</ul>}
        {error && <p className="error" role="alert">{error}</p>}
        <div className="row">
          <button className="primary" onClick={() => start("camera")} disabled={mode !== "idle"}>Start camera</button>
          <button onClick={() => start("demo")} disabled={mode !== "idle"}>Synthetic demo (pipeline test)</button>
          <button className={recording ? "danger" : ""} onClick={toggleRecord} disabled={mode === "idle"}>{recording ? "Stop recording" : "Record"}</button>
          <button onClick={stopAll} disabled={mode === "idle" || recording}>Stop camera</button>
        </div>
        <p aria-live="polite">{recording ? `Recording: ${seconds}s, ${frames} frames, ${visible ?? 0}/33 landmarks visible` : mode === "idle" ? "Camera off." : "Camera on, not recording."}</p>
        <div className="stage">
          <video ref={videoRef} className={mode === "camera" ? "mirror" : "hidden"} playsInline muted />
          <canvas ref={canvasRef} className="overlay" width={640} height={480} />
        </div>
      </section>

      <section className="card">
        <h2>Recordings in this page ({saved.length})</h2>
        {saved.length === 0 && <p className="muted">None yet.</p>}
        {saved.length > 0 && (
          <div className="table-wrap">
            <table className="angles">
              <thead><tr><th>#</th><th>Participant</th><th>Exercise</th><th>Performed</th><th>Length</th><th /></tr></thead>
              <tbody>
                {saved.map((r, i) => (
                  <tr key={i}>
                    <td>{i + 1}</td><td>{r.participant_code}</td><td>{r.exercise_id.replace("_", " ")}{r.synthetic ? " (synthetic)" : ""}</td>
                    <td>{r.intended.label === "correct" ? "correctly" : `error: ${r.intended.error}`}</td>
                    <td>{r.frames.length} frames</td>
                    <td className="row"><button onClick={() => download(r, i + 1)}>Download</button>
                      <button onClick={() => setSaved((s) => s.filter((_, j) => j !== i))}>Discard</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="muted">
          Put the downloaded files in <code>datasets/own/</code> and run <code>python -m app.ml.cli import-own</code> (see docs/user-guide.md) to turn them into repetition rows
          for the evaluation scripts.
        </p>
      </section>
    </>
  );
}
