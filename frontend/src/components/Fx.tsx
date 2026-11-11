import { useEffect, useRef, useState, type ReactNode } from "react";
import { motionOk } from "../motion";

/** Fades its children in when they scroll into view. Shows immediately where IntersectionObserver is missing. */
export function Reveal({ children, delay = 0, className = "" }: { children: ReactNode; delay?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [seen, setSeen] = useState(() => !motionOk() || typeof IntersectionObserver === "undefined");
  useEffect(() => {
    const el = ref.current;
    if (seen || !el) return;
    const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { setSeen(true); io.disconnect(); } }, { threshold: 0.15 });
    io.observe(el);
    return () => io.disconnect();
  }, [seen]);
  return <div ref={ref} className={`reveal${seen ? " in" : ""} ${className}`} style={{ "--d": `${delay}ms` } as React.CSSProperties}>{children}</div>;
}

/** Counts a whole number up from zero. Renders the final value straight away when motion is off. */
export function CountUp({ value, ms = 900 }: { value: number; ms?: number }) {
  const [shown, setShown] = useState(() => (motionOk() ? 0 : value));
  useEffect(() => {
    if (!motionOk()) { setShown(value); return; }
    let raf = 0;
    const t0 = performance.now();
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / ms);
      setShown(Math.round(value * (1 - Math.pow(1 - k, 3))));
      if (k < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value, ms]);
  return <>{shown}</>;
}

/** A short burst of confetti each time `fire` changes to a new truthy number. */
export function Confetti({ fire }: { fire: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const cv = ref.current;
    if (!fire || !cv || !motionOk()) return;
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    cv.width = innerWidth; cv.height = innerHeight;
    const colors = ["#2dd4bf", "#fbbf24", "#60a5fa", "#fb7185", "#4ade80"];
    const bits = Array.from({ length: 120 }, () => ({
      x: cv.width / 2, y: cv.height * 0.35, vx: (Math.random() - 0.5) * 14, vy: -Math.random() * 12 - 3,
      r: Math.random() * 6 + 3, a: Math.random() * 6, va: (Math.random() - 0.5) * 0.4, c: colors[Math.floor(Math.random() * colors.length)],
    }));
    let raf = 0;
    const t0 = performance.now();
    const draw = (t: number) => {
      const age = t - t0;
      ctx.clearRect(0, 0, cv.width, cv.height);
      for (const b of bits) {
        b.vy += 0.35; b.x += b.vx; b.y += b.vy; b.a += b.va;
        ctx.save(); ctx.translate(b.x, b.y); ctx.rotate(b.a); ctx.globalAlpha = Math.max(0, 1 - age / 2400);
        ctx.fillStyle = b.c; ctx.fillRect(-b.r, -b.r / 2, b.r * 2, b.r); ctx.restore();
      }
      if (age < 2400) raf = requestAnimationFrame(draw); else ctx.clearRect(0, 0, cv.width, cv.height);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [fire]);
  return <canvas ref={ref} className="confetti" aria-hidden="true" />;
}
