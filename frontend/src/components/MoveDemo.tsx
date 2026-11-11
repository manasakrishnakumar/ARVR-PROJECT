import { useEffect, useRef, useState } from "react";
import { Confetti } from "./Fx";
import { motionOk } from "../motion";

const SX = 150, SY = 110, L = 92; // shoulder position and arm length in the drawing
const UP = 90, DOWN = 20;         // a repetition counts after reaching UP degrees and returning below DOWN
const GOAL = 5;

const tip = (deg: number, side: 1 | -1) => ({ x: SX + side * L * Math.sin((deg * Math.PI) / 180), y: SY + L * Math.cos((deg * Math.PI) / 180) });

/** A small hands-on toy: drag the arms (or use the slider) and watch the same angle-and-counter idea the real tracker uses.
 *  It is only an illustration. It uses no camera and sends nothing anywhere. */
export default function MoveDemo() {
  const [deg, setDeg] = useState(10);
  const [reps, setReps] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [burst, setBurst] = useState(0);
  const [pulse, setPulse] = useState(0);
  const phase = useRef<"rest" | "up">("rest");
  const svg = useRef<SVGSVGElement>(null);

  const move = (d: number) => {
    const a = Math.max(0, Math.min(170, d));
    setDeg(a);
    if (phase.current === "rest" && a >= UP) phase.current = "up";
    else if (phase.current === "up" && a <= DOWN) {
      phase.current = "rest";
      setReps((r) => { const n = r + 1; if (n === GOAL) setBurst((b) => b + 1); return n; });
      setPulse((p) => p + 1);
    }
  };

  useEffect(() => {
    if (!playing) return;
    let raf = 0;
    const t0 = performance.now();
    const loop = (t: number) => { move(85 - 85 * Math.cos(((t - t0) / 1000) * 2.2) + 8); raf = requestAnimationFrame(loop); };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
    // move only touches state setters and a ref, so it is safe to leave out
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing]);

  const drag = (e: React.PointerEvent<SVGSVGElement>) => {
    if (e.buttons !== 1 && e.type !== "pointerdown") return;
    const r = svg.current!.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * 300 - SX;
    const y = ((e.clientY - r.top) / r.height) * 300 - SY;
    setPlaying(false);
    move((Math.atan2(Math.abs(x), y) * 180) / Math.PI);
  };

  const r = tip(deg, 1), l = tip(deg, -1);
  const good = deg >= UP;
  const arc = (side: 1 | -1) => {
    const R = 38, rad = (deg * Math.PI) / 180;
    return `M ${SX} ${SY + R} A ${R} ${R} 0 0 ${side === 1 ? 0 : 1} ${SX + side * R * Math.sin(rad)} ${SY + R * Math.cos(rad)}`;
  };

  return (
    <div className="demo card" aria-label="Interactive movement demo">
      <Confetti fire={burst} />
      <h3 style={{ marginTop: 0 }}>Try it: raise your arms</h3>
      <svg ref={svg} viewBox="0 0 300 260" role="img" aria-label={`Figure with both arms raised ${Math.round(deg)} degrees`}
        onPointerDown={(e) => { (e.target as Element).setPointerCapture?.(e.pointerId); drag(e); }} onPointerMove={drag}>
        <path className="zone" d={`M ${SX} ${SY} L ${tip(UP, 1).x} ${tip(UP, 1).y} A ${L} ${L} 0 0 0 ${tip(170, 1).x} ${tip(170, 1).y} Z`} />
        <path className="zone" d={`M ${SX} ${SY} L ${tip(UP, -1).x} ${tip(UP, -1).y} A ${L} ${L} 0 0 1 ${tip(170, -1).x} ${tip(170, -1).y} Z`} />
        <circle cx={SX} cy={62} r={22} className="joint" />
        <line className="limb" x1={SX} y1={SY} x2={SX} y2={215} />
        <line className="limb" x1={SX} y1={215} x2={128} y2={252} /><line className="limb" x1={SX} y1={215} x2={172} y2={252} />
        <line className={`limb arm${good ? " good" : ""}`} x1={SX} y1={SY} x2={r.x} y2={r.y} />
        <line className={`limb arm${good ? " good" : ""}`} x1={SX} y1={SY} x2={l.x} y2={l.y} />
        <path className="arc" d={arc(1)} /><path className="arc" d={arc(-1)} />
        <circle className="joint" cx={SX} cy={SY} r={7} /><circle className="joint" cx={r.x} cy={r.y} r={6} /><circle className="joint" cx={l.x} cy={l.y} r={6} />
        <text x={SX} y={30} textAnchor="middle" fontSize="13" fill="currentColor" className="muted">shaded area = target (≥ {UP}°)</text>
      </svg>
      <div className="demo-stats" aria-live="polite">
        <span className="muted">Angle<strong>{Math.round(deg)}°</strong></span>
        <span className="muted">Repetitions<strong key={pulse} className={pulse ? "pulse" : ""}>{reps}/{GOAL}</strong></span>
      </div>
      <input type="range" min={0} max={170} value={deg} aria-label="Arm angle in degrees" onChange={(e) => { setPlaying(false); move(Number(e.target.value)); }} />
      <div className="row" style={{ justifyContent: "center" }}>
        <button type="button" onClick={() => setPlaying((p) => !p)} disabled={!motionOk()}>{playing ? "Pause" : "Watch it move"}</button>
        <button type="button" onClick={() => { setPlaying(false); phase.current = "rest"; setReps(0); setDeg(10); }}>Reset</button>
      </div>
      <p className="muted" style={{ fontSize: ".85rem", margin: 0 }}>A toy to show the idea: measure an angle, count a repetition when you reach the target and come back. Reach {GOAL} for a surprise. The real tracker uses your webcam.</p>
    </div>
  );
}
