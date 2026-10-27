import { MIN_CONFIDENCE } from "./angles";
import { SKELETON, type PoseFrame } from "./types";

/** Draws the skeleton on a canvas. Low-confidence landmarks are drawn in amber so unreliable tracking is visible. */
export function drawSkeleton(canvas: HTMLCanvasElement, frame: PoseFrame | null, mirror: boolean) {
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
