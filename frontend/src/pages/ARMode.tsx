import { useEffect, useRef, useState } from "react";
import RecommendationCard from "../components/RecommendationCard";
import { useExerciseStream } from "../hooks/useExerciseStream";
import { useExercises } from "../hooks/useExercises";
import { isotropic } from "../pose/angles";
import { LANDMARK_INDEX, SKELETON, type Landmark } from "../pose/types";
import type { Exercise } from "../types/api";

type XrState = "checking" | "supported" | "unsupported";

/** Draws guidance over the camera picture: the skeleton, the exercise joint with the illustrative target ray, the live angle, and progress. */
function drawOverlay(canvas: HTMLCanvasElement, lm: Landmark[] | null, ex: Exercise, angle: number | null, reps: string, tip: string, mirror: boolean) {
  const ctx = canvas.getContext("2d")!;
  const { width: w, height: h } = canvas;
  ctx.clearRect(0, 0, w, h);
  ctx.font = "bold 22px system-ui"; ctx.fillStyle = "#fff"; ctx.strokeStyle = "rgba(0,0,0,.6)"; ctx.lineWidth = 4;
  ctx.strokeText(reps, 14, 32); ctx.fillText(reps, 14, 32);
  if (tip) { ctx.font = "18px system-ui"; ctx.strokeText(tip, 14, h - 16); ctx.fillText(tip, 14, h - 16); }
  if (!lm) return;
  const P = (i: number) => ({ x: (mirror ? 1 - lm[i].x : lm[i].x) * w, y: lm[i].y * h, ok: lm[i].visibility >= 0.5 });
  ctx.lineWidth = 3;
  for (const [a, b] of SKELETON) { const p = P(a), q = P(b); ctx.strokeStyle = p.ok && q.ok ? "rgba(45,212,191,.9)" : "rgba(250,204,21,.5)"; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke(); }
  const [ia, ib, ic] = ex.landmarks.map((n) => LANDMARK_INDEX[n]);
  const A = P(ia), B = P(ib), C = P(ic);
  // target ray: from the joint, at the illustrative target angle from the reference limb, on the side the user is moving to
  const ref = Math.atan2(A.y - B.y, A.x - B.x), cur = Math.atan2(C.y - B.y, C.x - B.x);
  let signed = cur - ref; signed = Math.atan2(Math.sin(signed), Math.cos(signed));
  const dir = signed >= 0 ? 1 : -1, tgt = ref + dir * (ex.target_angle_deg * Math.PI) / 180, R = 90;
  ctx.strokeStyle = "rgba(251,191,36,.95)"; ctx.setLineDash([8, 6]); ctx.lineWidth = 4;
  ctx.beginPath(); ctx.moveTo(B.x, B.y); ctx.lineTo(B.x + R * Math.cos(tgt), B.y + R * Math.sin(tgt)); ctx.stroke(); ctx.setLineDash([]);
  ctx.beginPath(); ctx.arc(B.x, B.y, 38, ref, ref + dir * ((ex.target_angle_deg * Math.PI) / 180), dir < 0); ctx.stroke();
  ctx.fillStyle = "#fff"; ctx.font = "bold 20px system-ui"; ctx.strokeStyle = "rgba(0,0,0,.6)";
  const txt = angle != null ? `${angle.toFixed(0)}°  (target ${ex.target_angle_deg}°)` : "angle n/a";
  ctx.strokeText(txt, B.x + 12, B.y - 12); ctx.fillText(txt, B.x + 12, B.y - 12);
}

export default function ARMode() {
  const { exercises } = useExercises();
  const [exerciseId, setExerciseId] = useState("elbow_flexion");
  const [xr, setXr] = useState<XrState>("checking");
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const exercise = exercises.find((e) => e.id === exerciseId) ?? null;
  const tipRef = useRef(""), repsRef = useRef("0 reps"), modeRef = useRef("idle");
  const s = useExerciseStream(exercise, 1, videoRef, (lm, angle) => {
    const c = canvasRef.current, v = videoRef.current;
    if (!c || !exercise) return;
    if (v && v.videoWidth && c.width !== v.videoWidth) { c.width = v.videoWidth; c.height = v.videoHeight; }
    const iso = lm && v && v.videoHeight && modeRef.current === "camera" ? isotropic(lm, 1) : lm; // overlay is drawn in image coordinates
    drawOverlay(c, iso, exercise, angle, repsRef.current, tipRef.current, modeRef.current === "camera");
  });
  tipRef.current = s.poseWarn ? "Pose not detected clearly. Adjust your position." : s.lastRep?.feedback ?? "";
  repsRef.current = `${s.live?.counted_reps ?? 0}/${s.targetReps || "-"} reps · ${s.live ? s.live.phase.replace("_", " ") : "waiting"}`;
  modeRef.current = s.mode;

  useEffect(() => {
    const xrApi = (navigator as unknown as { xr?: { isSessionSupported?: (m: string) => Promise<boolean> } }).xr;
    if (!xrApi?.isSessionSupported) { setXr("unsupported"); return; }
    xrApi.isSessionSupported("immersive-ar").then((ok) => setXr(ok ? "supported" : "unsupported")).catch(() => setXr("unsupported"));
  }, []);

  const running = s.mode !== "idle";
  return (
    <>
      <h1>AR mode (camera overlay)</h1>
      <p className="notice">
        <strong>This is a camera overlay, not immersive AR.</strong> Guidance is drawn over your camera picture in the browser. Works on a laptop or a phone browser.
        Immersive WebXR AR: {xr === "checking" ? "checking this device..." : xr === "supported"
          ? "this device reports support, but an immersive AR session is not implemented in this version and has not been tested."
          : "not available on this device or browser."}
      </p>
      <div className="row">
        <label>Exercise{" "}
          <select value={exerciseId} disabled={running} onChange={(e) => setExerciseId(e.target.value)}>
            {exercises.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
          </select>
        </label>
        <button className="primary" onClick={s.startCamera} disabled={running}>Start camera</button>
        <button onClick={s.startDemo} disabled={running}>Synthetic demo</button>
        <button onClick={() => void s.stopAndSave()} disabled={!running}>Stop and save</button>
      </div>
      {s.error && <p className="error" role="alert">{s.error}</p>}
      <div className="stage" style={{ maxWidth: 720 }}>
        <video ref={videoRef} className={s.mode === "camera" ? "mirror" : "hidden"} playsInline muted />
        <canvas ref={canvasRef} className="overlay" width={640} height={480} />
      </div>
      <p className="muted">Dashed amber line: the illustrative target for the joint. Green skeleton: your tracked pose; amber parts are low confidence. No video is stored or uploaded.</p>
      {s.result && <RecommendationCard result={s.result} sessionId={s.sessionId} />}
    </>
  );
}
