"""Backend performance measurements for the thesis (evaluation section 6.7).

Measures only what runs in the backend, on the machine it is run on:
  1. analysis cost per angle sample (smoothing, counting, assessment), no network;
  2. round-trip time of one angle sample over the WebSocket, using the in-process test client (so it EXCLUDES the real network and the browser).
It says nothing about browser pose-estimation frame rate (that needs a camera) or about other computers."""
import math
import statistics
import time

from app.exercises.library import get_exercise
from app.services.analysis import StreamAnalyzer


def _pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def _series(n: int, hz: int = 15, period: float = 3.0, start: float = 170.0, target: float = 50.0):
    return [(i / hz, start + (target - start) * (1 - math.cos(2 * math.pi * i / hz / period)) / 2) for i in range(n)]


def analysis_cost(exercise_id: str = "elbow_flexion", n: int = 20000) -> dict:
    ex = get_exercise(exercise_id)
    assert ex is not None
    sa = StreamAnalyzer(ex, 1, calibrate=False)
    samples = _series(n)
    lat = []
    for t, a in samples:
        t0 = time.perf_counter()
        sa.push(t, a)
        lat.append((time.perf_counter() - t0) * 1000)
    return {"samples": n, "mean_ms": statistics.fmean(lat), "p95_ms": _pct(lat, 0.95), "p99_ms": _pct(lat, 0.99), "max_ms": max(lat)}


def websocket_roundtrip(n: int = 600) -> dict:
    from fastapi.testclient import TestClient

    from app.main import app

    lat = []
    with TestClient(app) as c, c.websocket_connect("/api/ws/analysis?exercise_id=elbow_flexion&difficulty=1") as ws:
        ws.receive_json()  # hello
        counted = 0
        for t, a in _series(n):
            t0 = time.perf_counter()
            ws.send_json({"t": t, "angle": a})
            msg = ws.receive_json()
            if msg["counted_reps"] > counted:  # a rep message follows the state message
                counted = msg["counted_reps"]
                ws.receive_json()
            lat.append((time.perf_counter() - t0) * 1000)
    return {"messages": n, "mean_ms": statistics.fmean(lat), "p95_ms": _pct(lat, 0.95), "p99_ms": _pct(lat, 0.99), "max_ms": max(lat)}


def run_perf() -> dict:
    import platform

    a, w = analysis_cost(), websocket_roundtrip()
    return {
        "kind": "performance",
        "title": "Backend performance (analysis cost and WebSocket round trip)",
        "caveat": "Measured on one computer with the in-process test client: excludes the real network and the browser's pose estimation. "
                  "Browser frame rate and end-to-end latency need a real camera and were not measured here.",
        "machine": {"python": platform.python_version(), "platform": platform.platform(), "processor": platform.processor()},
        "data": {"analysis_cost_per_sample": a, "websocket_round_trip": w,
                 "budget": {"sample_interval_ms": 66, "note": "the browser sends one angle about every 66 ms (15 Hz)"},
                 "within_budget": w["p99_ms"] < 66},
    }
