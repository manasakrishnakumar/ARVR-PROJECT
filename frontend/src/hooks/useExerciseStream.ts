import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { isotropic, jointAngle, MIN_CONFIDENCE } from "../pose/angles";
import { DemoEstimator } from "../pose/demo";
import { MediaPipeEstimator } from "../pose/mediapipe";
import { LANDMARK_INDEX, type Landmark, type PoseEstimator } from "../pose/types";
import { api } from "../services/api";
import { AnalysisSocket, type RepMsg, type SocketStatus, type StateMsg } from "../services/analysisSocket";
import type { CompleteOut, Exercise, SessionCreated } from "../types/api";

type Mode = "idle" | "camera" | "demo";
const SEND_MS = 66;

/** Live pipeline for the 3D room and AR pages: pose estimation in the browser, joint angle to the backend, results back.
 *  Landmarks are exposed through a ref (and an optional per-frame callback) so rendering does not re-render React every frame. */
export function useExerciseStream(exercise: Exercise | null, level: number, videoRef: RefObject<HTMLVideoElement | null>,
                                  onFrame?: (lm: Landmark[] | null, angle: number | null) => void) {
  const estRef = useRef<PoseEstimator | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const sockRef = useRef<AnalysisSocket | null>(null);
  const sessionRef = useRef<SessionCreated | null>(null);
  const repsRef = useRef(0);
  const rafRef = useRef(0);
  const t0 = useRef(0), lastSend = useRef(0), nullSince = useRef<number | null>(null);
  const landmarksRef = useRef<Landmark[] | null>(null);
  const angleRef = useRef<number | null>(null);
  const frameCb = useRef(onFrame);
  frameCb.current = onFrame;

  const [mode, setMode] = useState<Mode>("idle");
  const [error, setError] = useState<string | null>(null);
  const [sock, setSock] = useState<SocketStatus | "none">("none");
  const [live, setLive] = useState<StateMsg | null>(null);
  const [targetReps, setTargetReps] = useState(0);
  const [lastRep, setLastRep] = useState<RepMsg | null>(null);
  const [repCount, setRepCount] = useState(0);
  const [poseWarn, setPoseWarn] = useState(false);
  const [result, setResult] = useState<CompleteOut | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const stop = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop()); // camera shutdown
    streamRef.current = null;
    sockRef.current?.close(); sockRef.current = null;
    estRef.current?.close(); estRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    landmarksRef.current = null;
    setMode("idle"); setSock("none"); setLive(null); setPoseWarn(false);
  }, [videoRef]);

  const stopAndSave = useCallback(async () => {
    stop();
    const s = sessionRef.current;
    sessionRef.current = null;
    if (!s || repsRef.current === 0) return;
    try { setResult(await api.completeSession(s.id)); setSessionId(s.id); } catch (e) { setError(`Could not save the session: ${(e as Error).message}`); }
  }, [stop]);

  useEffect(() => stop, [stop]);

  const open = async (isDemo: boolean) => {
    if (!exercise) return;
    t0.current = performance.now(); lastSend.current = 0; repsRef.current = 0;
    setRepCount(0); setLastRep(null); setResult(null); setSessionId(null);
    sessionRef.current = await api.createSession(exercise.id, level, isDemo).catch(() => null); // the pose stream works without it
    const s = sessionRef.current;
    sockRef.current = new AnalysisSocket(exercise.id, level, (m) => {
      if (m.type === "hello") setTargetReps(m.target_reps);
      else if (m.type === "state") setLive(m);
      else if (m.type === "rep") { repsRef.current += 1; setRepCount(repsRef.current); setLastRep(m); }
    }, setSock, s ? { id: s.id, key: s.ws_key } : undefined);
  };

  const loop = useCallback((m: Mode) => {
    const tick = () => {
      rafRef.current = requestAnimationFrame(tick);
      const est = estRef.current, video = videoRef.current;
      if (!est || !exercise) return;
      if (m === "camera" && (!video || video.readyState < 2)) return;
      const ts = performance.now();
      const frame = est.detect(video, ts);
      landmarksRef.current = frame.landmarks;
      const aspect = m === "camera" && video && video.videoHeight ? video.videoWidth / video.videoHeight : 1;
      let angle: number | null = null;
      if (frame.landmarks) {
        const iso = isotropic(frame.landmarks, aspect);
        const [a, b, c] = exercise.landmarks.map((n) => iso[LANDMARK_INDEX[n]]);
        angle = jointAngle(a, b, c);
      }
      angleRef.current = angle;
      frameCb.current?.(frame.landmarks, angle);
      if (ts - lastSend.current >= SEND_MS) { lastSend.current = ts; sockRef.current?.send((ts - t0.current) / 1000, angle); }
      if (angle === null) { nullSince.current ??= ts; if (ts - nullSince.current > 1000) setPoseWarn(true); }
      else { nullSince.current = null; setPoseWarn((w) => (w ? false : w)); }
    };
    tick();
  }, [exercise, videoRef]);

  const startDemo = async () => { stop(); setError(null); await open(true); estRef.current = new DemoEstimator(); setMode("demo"); loop("demo"); };

  const startCamera = async () => {
    stop(); setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
      streamRef.current = stream;
      stream.getVideoTracks()[0].addEventListener("ended", () => { void stopAndSave(); setError("Camera disconnected."); });
      const v = videoRef.current!;
      v.srcObject = stream; await v.play();
      estRef.current = await MediaPipeEstimator.create();
      await open(false);
      setMode("camera"); loop("camera");
    } catch (e) {
      stop();
      const err = e as Error;
      setError(err.name === "NotAllowedError" ? "Camera permission denied." : err.name === "NotFoundError" ? "No camera found. Try the synthetic demo." : err.message);
    }
  };

  return { mode, error, sock, live, targetReps, lastRep, repCount, poseWarn, result, sessionId, landmarksRef, angleRef,
           startCamera, startDemo, stopAndSave, minConfidence: MIN_CONFIDENCE };
}
