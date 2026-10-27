import { useCallback, useEffect, useRef, useState } from "react";
import { bodyAngles, MIN_CONFIDENCE, type JointAngles } from "../pose/angles";
import { DemoEstimator } from "../pose/demo";
import { MediaPipeEstimator } from "../pose/mediapipe";
import { SKELETON, type PoseEstimator, type PoseFrame } from "../pose/types";

type Mode = "idle" | "camera" | "demo";

function draw(canvas: HTMLCanvasElement, frame: PoseFrame | null, mirror: boolean) {
  const ctx = canvas.getContext("2d")!;
  const { width: w, height: h } = canvas;
  ctx.clearRect(0, 0, w, h);
  if (!frame?.landmarks) return;
  const lms = frame.landmarks;
  const pt = (i: number) => {
    const l = lms[i];
    return { x: (mirror ? 1 - l.x : l.x) * w, y: l.y * h, ok: l.visibility >= MIN_CONFIDENCE };
  };
  ctx.lineWidth = 3;
  for (const [a, b] of SKELETON) {
    const p = pt(a), q = pt(b);
    ctx.strokeStyle = p.ok && q.ok ? "#22d3a8" : "rgba(250,204,21,.5)";
    ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
  }
  lms.forEach((_, i) => {
    if (i < 11 || lms[i].visibility === 0) return;
    const p = pt(i);
    ctx.fillStyle = p.ok ? "#fff" : "#facc15";
    ctx.beginPath(); ctx.arc(p.x, p.y, 4, 0, Math.PI * 2); ctx.fill();
  });
}

export default function PoseLab() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const estRef = useRef<PoseEstimator | null>(null);
  const rafRef = useRef(0);
  const streamRef = useRef<MediaStream | null>(null);
  const pausedRef = useRef(false);
  const [mode, setMode] = useState<Mode>("idle");
  const [paused, setPaused] = useState(false);
  const [status, setStatus] = useState("Not started");
  const [error, setError] = useState<string | null>(null);
  const [angles, setAngles] = useState<JointAngles[]>([]);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState("");

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
    setMode("idle"); setPaused(false); setAngles([]); setStatus("Stopped");
  }, []);

  useEffect(() => stop, [stop]);

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
      draw(canvas, frame, m === "camera");
      if (!frame.landmarks) { setStatus("No person detected. Step into view."); setAngles([]); return; }
      const conf = frame.landmarks.filter((l) => l.visibility >= MIN_CONFIDENCE).length;
      setStatus(`Tracking: ${conf}/33 landmarks above confidence ${MIN_CONFIDENCE}`);
      setAngles(bodyAngles(frame.landmarks));
    };
    tick();
  }, []);

  const startDemo = () => {
    stop();
    canvasRef.current!.width = 640;
    canvasRef.current!.height = 480;
    estRef.current = new DemoEstimator();
    setMode("demo"); setError(null); loop("demo");
  };

  const startCamera = async () => {
    stop(); setError(null); setStatus("Requesting camera...");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: deviceId ? { deviceId: { exact: deviceId } } : { width: 640, height: 480 }, audio: false,
      });
      streamRef.current = stream;
      setDevices((await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "videoinput"));
      stream.getVideoTracks()[0].addEventListener("ended", () => { stop(); setError("Camera disconnected."); });
      const v = videoRef.current!;
      v.srcObject = stream;
      await v.play();
      canvasRef.current!.width = v.videoWidth || 640;
      canvasRef.current!.height = v.videoHeight || 480;
      setStatus("Loading pose model...");
      estRef.current = await MediaPipeEstimator.create();
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

  return (
    <section className="card">
      <h2>Pose lab</h2>
      <p className="muted">
        Processing runs locally in your browser. No video is uploaded or stored. Angles are 2D image-plane
        estimates, not clinical measurements.
      </p>
      <div className="row">
        <button onClick={startCamera}>Start camera</button>
        <button onClick={startDemo}>Synthetic demo</button>
        <button onClick={togglePause} disabled={mode === "idle"}>{paused ? "Resume" : "Pause"}</button>
        <button onClick={stop} disabled={mode === "idle"}>Stop</button>
        {devices.length > 1 && (
          <select value={deviceId} onChange={(e) => setDeviceId(e.target.value)} aria-label="Camera">
            {devices.map((d, i) => <option key={d.deviceId} value={d.deviceId}>{d.label || `Camera ${i + 1}`}</option>)}
          </select>
        )}
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <p aria-live="polite"><strong>Status:</strong> {status}{mode === "demo" && " (synthetic data, not a real person)"}</p>
      <div className="stage">
        <video ref={videoRef} className={mode === "camera" ? "mirror" : "hidden"} playsInline muted />
        <canvas ref={canvasRef} className="overlay" width={640} height={480} />
      </div>
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
