import { useCallback, useEffect, useRef, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { bodyAngles, isotropic, MIN_CONFIDENCE } from "../pose/angles";
import { DemoEstimator } from "../pose/demo";
import { drawSkeleton } from "../pose/draw";
import { MediaPipeEstimator } from "../pose/mediapipe";
import { LM, type PoseEstimator } from "../pose/types";

type Mode = "idle" | "camera" | "demo";
const WINDOW_S = 10;
const KEY_LANDMARKS: [string, number][] = [
  ["Left shoulder", LM.L_SHOULDER], ["Right shoulder", LM.R_SHOULDER], ["Left elbow", LM.L_ELBOW], ["Right elbow", LM.R_ELBOW],
  ["Left wrist", LM.L_WRIST], ["Right wrist", LM.R_WRIST], ["Left hip", LM.L_HIP], ["Right hip", LM.R_HIP],
  ["Left knee", LM.L_KNEE], ["Right knee", LM.R_KNEE], ["Left ankle", LM.L_ANKLE], ["Right ankle", LM.R_ANKLE],
];

interface Diag {
  fps: number; detectRate: number; frames: number; width: number; height: number; modelMs: number;
}

/** Pose visualisation and movement analysis: the skeleton, per-landmark confidence, a live angle trace, and camera/pipeline
 *  diagnostics (permission, resolution, processing speed, detection rate). Nothing here is sent to the backend or stored. */
export default function PoseAnalysis() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const estRef = useRef<PoseEstimator | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef(0);
  const pausedRef = useRef(false);
  const traceRef = useRef<{ t: number; v: number | null }[]>([]);
  const statsRef = useRef({ frames: 0, detected: 0, t0: 0, modelMs: 0 });
  const jointRef = useRef(2);

  const [mode, setMode] = useState<Mode>("idle");
  const [paused, setPaused] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [permission, setPermission] = useState<string>("not requested");
  const [status, setStatus] = useState("Not started");
  const [conf, setConf] = useState<number[]>([]);
  const [angles, setAngles] = useState<{ label: string; angle: number | null }[]>([]);
  const [joint, setJoint] = useState(2);
  const [trace, setTrace] = useState<{ t: number; v: number | null }[]>([]);
  const [diag, setDiag] = useState<Diag | null>(null);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState("");

  useEffect(() => { jointRef.current = joint; traceRef.current = []; setTrace([]); }, [joint]);

  const stop = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop()); // camera shutdown
    streamRef.current = null;
    estRef.current?.close();
    estRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    const c = canvasRef.current;
    if (c) c.getContext("2d")!.clearRect(0, 0, c.width, c.height);
    pausedRef.current = false;
    setMode("idle"); setPaused(false); setStatus("Stopped");
  }, []);
  useEffect(() => stop, [stop]);

  const loop = useCallback((m: Mode) => {
    let lastUi = 0;
    const tick = () => {
      rafRef.current = requestAnimationFrame(tick);
      const est = estRef.current, video = videoRef.current, canvas = canvasRef.current;
      if (!est || !canvas || pausedRef.current) return;
      if (m === "camera" && (!video || video.readyState < 2)) return;
      const ts = performance.now();
      const t1 = performance.now();
      const frame = est.detect(video, ts);
      const st = statsRef.current;
      st.modelMs = 0.9 * st.modelMs + 0.1 * (performance.now() - t1);
      st.frames += 1;
      drawSkeleton(canvas, frame, m === "camera");
      const aspect = m === "camera" && video && video.videoHeight ? video.videoWidth / video.videoHeight : 1;
      const lms = frame.landmarks ? isotropic(frame.landmarks, aspect) : null;
      if (lms) st.detected += 1;
      const list = lms ? bodyAngles(lms) : [];
      const val = list[jointRef.current]?.angle ?? null;
      const t = (ts - st.t0) / 1000;
      traceRef.current.push({ t, v: val });
      while (traceRef.current.length && traceRef.current[0].t < t - WINDOW_S) traceRef.current.shift();
      if (ts - lastUi > 120) { // the UI updates ~8 times a second; detection runs at full speed
        lastUi = ts;
        setConf(lms ? KEY_LANDMARKS.map(([, i]) => lms[i].visibility) : []);
        setAngles(list);
        setTrace(traceRef.current.map((p) => ({ t: Number(p.t.toFixed(1)), v: p.v })));
        setStatus(lms ? "Tracking" : "No person detected. Step into view.");
        const elapsed = Math.max(0.001, (ts - st.t0) / 1000);
        setDiag((d) => ({ fps: st.frames / elapsed, detectRate: st.frames ? st.detected / st.frames : 0, frames: st.frames,
          width: video?.videoWidth || d?.width || 640, height: video?.videoHeight || d?.height || 480, modelMs: st.modelMs }));
      }
    };
    tick();
  }, []);

  const begin = () => { statsRef.current = { frames: 0, detected: 0, t0: performance.now(), modelMs: 0 }; traceRef.current = []; setTrace([]); setError(null); };

  const startDemo = () => {
    stop(); begin();
    canvasRef.current!.width = 640; canvasRef.current!.height = 480;
    estRef.current = new DemoEstimator();
    setMode("demo"); setPermission("not needed (synthetic)"); loop("demo");
  };

  const startCamera = async () => {
    stop(); begin(); setStatus("Requesting camera...");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: deviceId ? { deviceId: { exact: deviceId } } : { width: 640, height: 480 }, audio: false,
      });
      setPermission("granted");
      streamRef.current = stream;
      setDevices((await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "videoinput"));
      stream.getVideoTracks()[0].addEventListener("ended", () => { stop(); setError("Camera disconnected."); });
      const v = videoRef.current!;
      v.srcObject = stream;
      await v.play();
      canvasRef.current!.width = v.videoWidth || 640; canvasRef.current!.height = v.videoHeight || 480;
      setStatus("Loading pose model...");
      estRef.current = await MediaPipeEstimator.create();
      statsRef.current.t0 = performance.now();
      setMode("camera"); loop("camera");
    } catch (e) {
      stop();
      const err = e as Error;
      if (err.name === "NotAllowedError") setPermission("denied");
      setError(err.name === "NotAllowedError" ? "Camera permission denied. Allow camera access for this site in your browser settings."
        : err.name === "NotFoundError" ? "No camera found. Try the synthetic demo." : err.message);
    }
  };

  const running = mode !== "idle";
  const labelOf = angles[joint]?.label ?? "angle";
  return (
    <>
      <h1>Pose analysis</h1>
      <p className="muted">
        Inspect what the pose tracker sees: skeleton, per-landmark confidence, joint angles over time, and pipeline diagnostics.
        Everything runs in your browser; nothing is recorded or sent anywhere. Use this page to check your camera and lighting before a session.
      </p>
      <div className="row">
        <button className="primary" onClick={startCamera}>Start camera</button>
        <button onClick={startDemo}>Synthetic demo</button>
        <button onClick={() => { pausedRef.current = !pausedRef.current; setPaused(pausedRef.current); }} disabled={!running}>{paused ? "Resume" : "Pause"}</button>
        <button onClick={stop} disabled={!running}>Stop</button>
        {devices.length > 1 && (
          <select value={deviceId} onChange={(e) => setDeviceId(e.target.value)} aria-label="Camera">
            {devices.map((d, i) => <option key={d.deviceId} value={d.deviceId}>{d.label || `Camera ${i + 1}`}</option>)}
          </select>
        )}
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <p aria-live="polite"><strong>Status:</strong> {status}{mode === "demo" && " (synthetic figure; only the left elbow moves)"}</p>

      <div className="session">
        <div className="stage">
          <video ref={videoRef} className={mode === "camera" ? "mirror" : "hidden"} playsInline muted />
          <canvas ref={canvasRef} className="overlay" width={640} height={480} />
        </div>
        <div className="stats">
          <h3>Diagnostics</h3>
          <table className="angles"><tbody>
            <tr><td>Camera permission</td><td>{permission}</td></tr>
            <tr><td>Resolution</td><td>{diag ? `${diag.width} × ${diag.height}` : "n/a"}</td></tr>
            <tr><td>Processing speed</td><td>{diag ? `${diag.fps.toFixed(1)} frames/s` : "n/a"}</td></tr>
            <tr><td>Model time per frame</td><td>{diag ? `${diag.modelMs.toFixed(1)} ms` : "n/a"}</td></tr>
            <tr><td>Person found</td><td>{diag ? `${(diag.detectRate * 100).toFixed(0)}% of ${diag.frames} frames` : "n/a"}</td></tr>
          </tbody></table>
          <p className="muted">Below about 10 frames/s, repetition counting gets unreliable. Better light and a plain background usually help.</p>
        </div>
      </div>

      <section className="card">
        <h2>Joint angle over the last {WINDOW_S} seconds</h2>
        <label>Joint{" "}
          <select value={joint} onChange={(e) => setJoint(Number(e.target.value))}>
            {(angles.length ? angles : [{ label: "Left elbow" }, { label: "Right elbow" }, { label: "Left shoulder" }, { label: "Right shoulder" },
              { label: "Left hip" }, { label: "Right hip" }, { label: "Left knee" }, { label: "Right knee" }]).map((a, i) => <option key={a.label} value={i}>{a.label}</option>)}
          </select>
        </label>
        <p className="muted">2D image-plane angle from three landmarks, not a clinical measurement. Gaps mean the landmarks were not reliable.</p>
        <div className="chart-box" role="img" aria-label={`${labelOf} angle over time`}>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={trace} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
              <CartesianGrid stroke="var(--grid)" strokeDasharray="3 3" />
              <XAxis dataKey="t" stroke="var(--muted)" fontSize={12} type="number" domain={["dataMin", "dataMax"]} unit="s" />
              <YAxis stroke="var(--muted)" fontSize={12} domain={[0, 180]} unit="°" />
              <Tooltip contentStyle={{ background: "var(--card)", border: "1px solid var(--grid)", color: "var(--text)" }} />
              <Line type="monotone" dataKey="v" name={labelOf} stroke="var(--c1)" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="card">
        <h2>Landmark confidence</h2>
        <p className="muted">Landmarks below {MIN_CONFIDENCE} are treated as unreliable and ignored by the angle maths.</p>
        <div className="table-wrap">
          <table className="angles">
            <thead><tr><th>Landmark</th><th>Confidence</th><th /><th>Angle</th></tr></thead>
            <tbody>
              {KEY_LANDMARKS.map(([name], i) => {
                const c = conf[i];
                const a = angles.find((x) => x.label === name)?.angle;
                return (
                  <tr key={name}>
                    <td>{name}</td><td>{c != null ? c.toFixed(2) : "n/a"}</td>
                    <td style={{ width: "40%" }}><div className="bar"><div style={{ width: `${(c ?? 0) * 100}%`, background: (c ?? 0) >= MIN_CONFIDENCE ? "var(--accent)" : "var(--c2)" }} /></div></td>
                    <td>{a != null ? `${a.toFixed(0)}°` : "-"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
