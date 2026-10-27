import csv
import io
import json
import os
import tempfile

os.environ.setdefault("ARVR_DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/p6.db")

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.database.db import reset_db
from app.main import app
from tests.test_phase5_api import play, register  # reuse the synthetic-stream helpers


@pytest.fixture
def c():
    reset_db()
    with TestClient(app) as client:
        yield client


def test_session_detail_has_metrics_repetitions_and_decision(c):
    h = register(c, "carol")
    s, done = play(c, h, 1)
    d = c.get(f"/api/sessions/{s['id']}/detail", headers=h).json()
    assert d["summary"]["classification"] == "good" and len(d["repetitions"]) >= 6
    assert d["repetitions"][0]["label"] and d["decision"]["action"] == "maintain" and d["decision"]["reasons"]
    assert c.get(f"/api/sessions/{s['id']}/detail").status_code == 404  # not for strangers
    g = c.post("/api/sessions", json={"exercise_id": "elbow_flexion"}).json()  # guest session: reachable by id, no decision
    assert c.get(f"/api/sessions/{g['id']}/detail").json()["decision"] is None


def test_progress_has_duration_and_range_and_date_filters(c):
    h = register(c, "dave")
    play(c, h, 1)
    p = c.get("/api/analytics/progress", headers=h).json()["points"]
    assert len(p) == 1 and p[0]["duration_s"] >= 0 and p[0]["mean_rom_deg"] > 50
    assert len(c.get("/api/analytics/progress", params={"from": "2000-01-01", "to": "2999-12-31"}, headers=h).json()["points"]) == 1
    assert c.get("/api/analytics/progress", params={"to": "2000-01-01"}, headers=h).json()["points"] == []
    assert c.get("/api/analytics/progress", params={"from": "2999-01-01"}, headers=h).json()["points"] == []
    assert c.get("/api/analytics/summary", params={"to": "2000-01-01"}, headers=h).json()["total_sessions"] == 0
    assert c.get("/api/analytics/progress", params={"from": "not-a-date"}, headers=h).status_code == 422


def test_csv_export_contains_only_own_saved_real_data(c):
    a, b = register(c, "erin"), register(c, "frank")
    play(c, a, 1)
    play(c, a, 1, demo=True)
    play(c, b, 1)
    r = c.get("/api/analytics/export.csv", headers=a)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv") and "attachment" in r.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0][0] == "session_id" and len(rows) == 2  # header + the one real session (demo excluded, other user's excluded)
    with_demo = list(csv.reader(io.StringIO(c.get("/api/analytics/export.csv", params={"include_demo": True}, headers=a).text)))
    assert len(with_demo) == 3
    reps = list(csv.reader(io.StringIO(c.get("/api/analytics/export.csv", params={"kind": "repetitions"}, headers=a).text)))
    assert reps[0][:3] == ["session_id", "exercise_id", "repetition"] and len(reps) >= 7
    assert c.get("/api/analytics/export.csv").status_code == 401
    assert c.get("/api/analytics/export.csv", params={"kind": "passwords"}, headers=a).status_code == 422


def test_research_results_served_from_json_files(c, tmp_path, monkeypatch):
    (tmp_path / "ok.json").write_text(json.dumps({"kind": "external", "title": "T", "caveat": "C", "data": {"x": 1}}))
    (tmp_path / "broken.json").write_text("{not json")
    (tmp_path / "other.json").write_text(json.dumps({"hello": "world"}))  # not a results document
    monkeypatch.setattr(settings, "results_dir", tmp_path)
    r = c.get("/api/research/results").json()
    assert [x["id"] for x in r["results"]] == ["ok"] and r["results"][0]["data"] == {"x": 1}
    monkeypatch.setattr(settings, "results_dir", tmp_path / "missing")
    assert c.get("/api/research/results").json()["results"] == []


def test_committed_result_files_are_valid_results_documents():
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(settings.results_dir.glob("*.json"))]
    assert docs, "expected committed aggregate results"
    for d in docs:
        assert {"kind", "title", "caveat", "data"} <= set(d)
        assert "participant_id" not in json.dumps(d)  # aggregate metrics only: no per-person rows
