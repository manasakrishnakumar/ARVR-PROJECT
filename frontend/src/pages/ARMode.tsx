import { useEffect, useRef, useState } from "react";
import RecommendationCard from "../components/RecommendationCard";
import { useExerciseStream } from "../hooks/useExerciseStream";
import { useExercises } from "../hooks/useExercises";
import { isotropic } from "../pose/angles";
import { ghostPose, jointState, JOINT_COLOUR, repFlash, setupHint, type JointState } from "../pose/guidance";
import { repCue, speak } from "../pose/speech";
import { trainerProgress } from "../pose/trainer";
import { LANDMARK_INDEX, SKELETON, type Landmark } from "../pose/types";
import type { Exercise } from "../types/api";

type XrState = "checking" | "supported" | "unsupported";

/** Draws guidance over the camera picture: the skeleton, the exercise joint with the illustrative target ray, the live angle, and progress. */
function drawOverlay(canvas: HTMLCanvasElement, lm: Landmark[] | null, ex: Exercise, angle: number | null, reps: string, tip: string, mirror: boolean,
                     ghost: Landmark[] | null, state: JointState, flash: { text: string; colour: string; alpha: number } | null, progress: number) {
  const ctx = canvas.getContext("2d")!;
  const { width: w, height: h } = canvas;
  ctx.clearRect(0, 0, w, h);
  if (progress > 0) { // repetition progress bar along the top
    ctx.fillStyle = "rgba(255,255,255,.25)"; ctx.fillRect(0, 0, w, 8);
    ctx.fillStyle = progress >= 1 ? "#22c55e" : "#2dd4bf"; ctx.fillRect(0, 0, w * Math.min(1, progress), 8);
  }
  if (flash && flash.alpha > 0) { // large confirmation after each repetition
    ctx.save(); ctx.globalAlpha = flash.alpha; ctx.strokeStyle = flash.colour; ctx.lineWidth = 12; ctx.strokeRect(6, 6, w - 12, h - 12);
    ctx.font = "bold 44px system-ui"; ctx.textAlign = "center"; ctx.fillStyle = flash.colour; ctx.strokeStyle = "rgba(0,0,0,.7)"; ctx.lineWidth = 6;
    ctx.strokeText(flash.text, w / 2, h * 0.2); ctx.fillText(flash.text, w / 2, h * 0.2); ctx.restore();
  }
  ctx.font = "bold 22px system-ui"; ctx.fillStyle = "#fff"; ctx.strokeStyle = "rgba(0,0,0,.6)"; ctx.lineWidth = 4;
  ctx.strokeText(reps, 14, 32); ctx.fillText(reps, 14, 32);
  if (tip) { ctx.font = "18px system-ui"; ctx.strokeText(tip, 14, h - 16); ctx.fillText(tip, 14, h - 16); }
  if (!lm) return;
  const P = (i: number) => ({ x: (mirror ? 1 - lm[i].x : lm[i].x) * w, y: lm[i].y * h, ok: lm[i].visibility >= 0.5 });
  ctx.lineWidth = 3;
  for (const [a, b] of SKELETON) { const p = P(a), q = P(b); ctx.strokeStyle = p.ok && q.ok ? "rgba(45,212,191,.9)" : "rgba(250,204,21,.5)"; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke(); }
  if (ghost) { // translucent virtual trainer to match
    ctx.strokeStyle = "rgba(255,255,255,.45)"; ctx.lineWidth = 8; ctx.lineCap = "round";
    for (const [a, b] of SKELETON) { const p = { x: (mirror ? 1 - ghost[a].x : ghost[a].x) * w, y: ghost[a].y * h }, q = { x: (mirror ? 1 - ghost[b].x : ghost[b].x) * w, y: ghost[b].y * h }; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke(); }
    ctx.lineCap = "butt";
  }
  const [ia, ib, ic] = ex.landmarks.map((n) => LANDMARK_INDEX[n]);
  const A = P(ia), B = P(ib), C = P(ic);
  ctx.fillStyle = JOINT_COLOUR[state]; // exercising joints: green reached, amber moving, red unclear
  for (const q of [A, B, C]) { ctx.beginPath(); ctx.arc(q.x, q.y, 9, 0, 2 * Math.PI); ctx.fill(); }
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
  const [showGhost, setShowGhost] = useState(true);
  const [voice, setVoice] = useState(false);
  const [hint, setHint] = useState({ ok: false, text: "" });
  const [facing, setFacing] = useState<"user" | "environment">("user");
  const flashRef = useRef<{ text: string; colour: string; at: number } | null>(null), progressRef = useRef(0);
  const stageRef = useRef<HTMLDivElement>(null), facingRef = useRef<"user" | "environment">("user");
  facingRef.current = facing; // the back camera is not mirrored
  const ghostRef = useRef(true), lastHint = useRef(""), t0 = useRef(performance.now());
  ghostRef.current = showGhost;
  const s = useExerciseStream(exercise, 1, videoRef, (lm, angle) => {
    const c = canvasRef.current, v = videoRef.current;
    if (!c || !exercise) return;
    if (v && v.videoWidth && c.width !== v.videoWidth) { c.width = v.videoWidth; c.height = v.videoHeight; }
    const iso = lm && v && v.videoHeight && modeRef.current === "camera" ? isotropic(lm, 1) : lm; // overlay is drawn in image coordinates
    const progress = trainerProgress((performance.now() - t0.current) / 1000);
    const ghost = ghostRef.current ? ghostPose(exercise, progress, iso) : null;
    const visible = !!iso && exercise.landmarks.every((n) => iso[LANDMARK_INDEX[n]].visibility >= 0.5);
    const f = flashRef.current, age = f ? (performance.now() - f.at) / 1000 : 9;
    drawOverlay(c, iso, exercise, angle, repsRef.current, tipRef.current, modeRef.current === "camera" && facingRef.current === "user", ghost, jointState(angle, visible, exercise),
                f && age < 1.2 ? { text: f.text, colour: f.colour, alpha: Math.min(1, 1.2 - age) } : null, progressRef.current);
    const h = setupHint(iso, exercise); // updated only when the wording changes, so React is not re-rendered every frame
    if (h.text !== lastHint.current) { lastHint.current = h.text; setHint(h); }
  });
  const voiceRef = useRef(false);
  voiceRef.current = voice;
  useEffect(() => {
    if (s.lastRep) flashRef.current = { ...repFlash(s.lastRep), at: performance.now() };
    if (voiceRef.current && s.lastRep) speak(repCue(s.lastRep, s.live?.counted_reps ?? s.repCount, s.targetReps));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s.lastRep]);
  tipRef.current = s.poseWarn ? "Pose not detected clearly. Adjust your position." : s.lastRep?.feedback ?? "";
  repsRef.current = `${s.live?.counted_reps ?? 0}/${s.targetReps || "-"} reps · ${s.live ? s.live.phase.replace("_", " ") : "waiting"}`;
  modeRef.current = s.mode;
  progressRef.current = s.targetReps ? (s.live?.counted_reps ?? 0) / s.targetReps : 0;

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
        <button className="primary" onClick={() => void s.startCamera(facing)} disabled={running}>Start camera</button>
        <label>Camera{" "}
          <select value={facing} disabled={running} onChange={(e) => setFacing(e.target.value as "user" | "environment")}>
            <option value="user">Front (selfie)</option><option value="environment">Back (phone propped up)</option>
          </select>
        </label>
        <button onClick={s.startDemo} disabled={running}>Synthetic demo</button>
        <button onClick={() => void s.stopAndSave()} disabled={!running}>Stop and save</button>
        <button type="button" onClick={() => { const el = stageRef.current; if (!el) return; if (document.fullscreenElement) void document.exitFullscreen(); else void el.requestFullscreen?.(); }}>Full screen</button>
      </div>
      <div className="row">
        <label><input type="checkbox" checked={showGhost} onChange={(e) => setShowGhost(e.target.checked)} /> Ghost trainer (white translucent figure to match)</label>
        <label><input type="checkbox" checked={voice} onChange={(e) => setVoice(e.target.checked)} /> Voice cues</label>
      </div>
      {s.error && <p className="error" role="alert">{s.error}</p>}
      {running && hint.text && <p className={hint.ok ? "ok" : "notice"} role="status" aria-live="polite"><strong>Setup:</strong> {hint.text}</p>}
      <div className="stage" ref={stageRef} style={{ maxWidth: 720 }}>
        <video ref={videoRef} className={s.mode === "camera" ? (facing === "user" ? "mirror" : "") : "hidden"} playsInline muted />
        <canvas ref={canvasRef} className="overlay" width={640} height={480} />
      </div>
      <p className="muted">Dashed amber line: the illustrative target for the joint. Dots on the exercising joints: green = at the illustrative target, amber = moving, red = not clearly tracked. Green skeleton: your tracked pose; amber parts are low confidence. No video is stored or uploaded.</p>
      {s.result && <RecommendationCard result={s.result} sessionId={s.sessionId} />}
    </>
  );
}
