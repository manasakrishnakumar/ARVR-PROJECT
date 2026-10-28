import os
import tempfile

os.environ.setdefault("ARVR_DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/cal.db")

import pytest
from fastapi.testclient import TestClient

from app.exercises.library import get_exercise
from app.main import app
from app.repetition_detection.calibration import estimate_range
from app.services.analysis import StreamAnalyzer, analyze_series
from app.synthetic.sequences import make_sequence

ABD = get_exercise("shoulder_abduction")  # illustrative 20 -> 90
ELBOW = get_exercise("elbow_flexion")  # illustrative 160 -> 50


def test_estimate_range_follows_the_movement_direction_and_refuses_when_still():
    up = estimate_range([a for _, a in make_sequence(40, 70, 6, fps=15)], ABD)
    assert up and up[0] < up[1] and 35 < up[0] < 50 and 60 < up[1] < 72
    down = estimate_range([a for _, a in make_sequence(170, 100, 6, fps=15)], ELBOW)
    assert down and down[0] > down[1]
    assert estimate_range([80.0] * 200, ABD) is None and estimate_range([], ABD) is None
    assert estimate_range([a for _, a in make_sequence(80, 90, 6, fps=15)], ABD) is None  # 10 degrees: not enough movement


def test_without_calibration_a_person_with_a_smaller_range_is_never_counted():
    # this user's abduction only spans 40 -> 70 degrees in the image, but the illustrative range is 20 -> 90
    samples = make_sequence(40, 70, 8, period_s=3, fps=15)
    assert analyze_series(ABD, 1, samples).counted_reps == 0


def test_calibration_counts_the_same_user_including_repetitions_done_while_calibrating():
    samples = make_sequence(40, 70, 8, period_s=3, fps=15)
    res = analyze_series(ABD, 1, samples, calibrate=True)
    assert res.counted_reps == 8  # replay: the first repetitions are not lost
    assert all(r.assessment.label == "acceptable" for r in res.attempts)


def test_stream_reports_calibrating_then_calibrated_once():
    sa = StreamAnalyzer(ABD, 1, calibrate=True)
    seen, calibrated = [], []
    for t, a in make_sequence(40, 70, 6, period_s=3, fps=15):
        u = sa.push(t, a)
        seen.append(u.calibrating)
        if u.calibrated:
            calibrated.append((t, u.calibrated))
    assert seen[0] is True and seen[-1] is False and len(calibrated) == 1
    assert calibrated[0][0] >= 5.0  # never before the minimum observation time
    assert sa.calibrated_range is not None and not sa.calibrating


def test_a_person_who_does_not_move_stays_in_calibration_and_gets_no_fake_range():
    sa = StreamAnalyzer(ABD, 1, calibrate=True)
    for i in range(600):
        u = sa.push(i / 15, 60.0)
    assert u.calibrating and sa.calibrated_range is None and u.counted_reps == 0


def test_missing_data_does_not_calibrate_on_nothing():
    sa = StreamAnalyzer(ABD, 1, calibrate=True)
    for i in range(300):
        u = sa.push(i / 15, None)
    assert u.calibrating and sa.calibrated_range is None


def test_uncalibrated_behaviour_is_unchanged():
    res = analyze_series(ELBOW, 1, make_sequence(160, 50, 4, period_s=3, fps=15))
    assert res.counted_reps == 4


def test_websocket_calibrate_option_sends_calibrated_message_and_all_repetitions():
    seq = make_sequence(40, 70, 6, period_s=3, fps=15)
    with TestClient(app) as c, c.websocket_connect("/api/ws/analysis?exercise_id=shoulder_abduction&difficulty=1&calibrate=auto") as ws:
        hello = ws.receive_json()
        assert hello["calibrating"] is True
        for t, a in seq:
            ws.send_json({"t": t, "angle": a})
        types, states = [], 0
        while states < len(seq):
            m = ws.receive_json()
            states += m["type"] == "state"
            types.append(m)
    cal = [m for m in types if m["type"] == "calibrated"]
    reps = [m for m in types if m["type"] == "rep"]
    assert len(cal) == 1 and cal[0]["start"] < cal[0]["target"]
    assert len(reps) >= 5 and all(r["label"] == "acceptable" for r in reps)
    assert types[0]["calibrating"] is True and [m for m in types if m["type"] == "state"][-1]["calibrating"] is False
