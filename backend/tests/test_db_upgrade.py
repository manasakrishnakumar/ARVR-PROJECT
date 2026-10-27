import os
import tempfile

os.environ.setdefault("ARVR_DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/up.db")

from sqlalchemy import create_engine, inspect, text

from app.database.db import init_db


def test_old_prototype_database_is_upgraded_in_place_without_losing_rows(tmp_path):
    eng = create_engine(f"sqlite:///{(tmp_path / 'old.db').as_posix()}")
    with eng.begin() as c:  # the schema from the first prototype: no ws_key / counted / reliable
        c.execute(text("CREATE TABLE users (id VARCHAR(32) PRIMARY KEY, username VARCHAR(64) UNIQUE, password_hash VARCHAR(256), "
                       "age_range VARCHAR(16), goals VARCHAR(256), preferences JSON, created_at DATETIME)"))
        c.execute(text("CREATE TABLE sessions (id VARCHAR(32) PRIMARY KEY, user_id VARCHAR(32), exercise_id VARCHAR(64), "
                       "is_demo BOOLEAN, difficulty INTEGER, started_at DATETIME, ended_at DATETIME, summary JSON)"))
        c.execute(text("CREATE TABLE repetitions (id VARCHAR(32) PRIMARY KEY, session_id VARCHAR(32), \"index\" INTEGER, "
                       "range_of_motion_deg FLOAT, duration_s FLOAT, quality_label VARCHAR(64), quality_score FLOAT, features JSON)"))
        c.execute(text("INSERT INTO sessions (id, exercise_id, is_demo, difficulty) VALUES ('s1', 'elbow_flexion', 0, 1)"))
        c.execute(text("INSERT INTO repetitions (id, session_id, \"index\", quality_label) VALUES ('r1', 's1', 1, 'acceptable')"))
    init_db(eng)
    init_db(eng)  # idempotent
    insp = inspect(eng)
    assert "ws_key" in {c["name"] for c in insp.get_columns("sessions")}
    assert {"counted", "reliable"} <= {c["name"] for c in insp.get_columns("repetitions")}
    assert {"auth_tokens", "adaptive_decisions"} <= set(insp.get_table_names())
    with eng.connect() as c:
        assert c.execute(text("SELECT exercise_id FROM sessions")).scalar() == "elbow_flexion"
        assert c.execute(text("SELECT quality_label FROM repetitions")).scalar() == "acceptable"
