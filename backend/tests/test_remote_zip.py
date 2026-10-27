import io
import re
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.ml.remote_zip import fetch_entry, list_entries

PAYLOAD = {"Ex1/a.mp4": bytes(range(256)) * 400, "Ex1/b.mp4": b"hello world" * 5000, "Ex2/c.mp4": b"x" * 1234}


def _zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in PAYLOAD.items():
            z.writestr(n, d)
    return buf.getvalue()


@pytest.fixture
def server():
    blob, state = _zip_bytes(), {"ranges": 0, "bytes": 0, "honour_range": True}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_HEAD(self):
            self.send_response(200)
            self.send_header("Content-Length", str(len(blob)))
            self.end_headers()

        def do_GET(self):
            m = re.match(r"bytes=(\d+)-(\d+)", self.headers.get("Range", ""))
            if m and state["honour_range"]:
                a, b = int(m.group(1)), min(int(m.group(2)), len(blob) - 1)
                body = blob[a:b + 1]
                state["ranges"] += 1
                self.send_response(206)
            else:
                body = blob
                self.send_response(200)
            state["bytes"] += len(body)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}/v.zip", state, len(blob)
    srv.shutdown()


def test_list_and_fetch_single_entry_without_downloading_everything(server, tmp_path):
    url, state, total = server
    assert list_entries(url) == {n: len(d) for n, d in PAYLOAD.items()}
    dest = tmp_path / "out" / "Ex2" / "c.mp4"
    assert fetch_entry(url, "Ex2/c.mp4", dest) == 1234
    assert dest.read_bytes() == PAYLOAD["Ex2/c.mp4"] and state["ranges"] > 0
    assert not dest.with_suffix(".mp4.part").exists()
    assert fetch_entry(url, "Ex2/c.mp4", dest) == 0  # already complete -> skipped


def test_fetch_larger_entry_roundtrips(server, tmp_path):
    url, _, _ = server
    dest = tmp_path / "a.mp4"
    fetch_entry(url, "Ex1/a.mp4", dest, chunk=4096)
    assert dest.read_bytes() == PAYLOAD["Ex1/a.mp4"]


def test_transient_failures_are_retried(server, tmp_path, monkeypatch):
    import http.client

    from app.ml import remote_zip

    url, _, _ = server
    real, calls = remote_zip.urllib.request.urlopen, {"n": 0}

    def flaky(req, timeout=None):
        if getattr(req, "headers", {}).get("Range") and calls["n"] < 2:
            calls["n"] += 1
            raise http.client.IncompleteRead(b"partial", 10)  # what killed the real download
        return real(req, timeout=timeout)

    monkeypatch.setattr(remote_zip.urllib.request, "urlopen", flaky)
    monkeypatch.setattr(remote_zip.time, "sleep", lambda s: None)
    dest = tmp_path / "c.mp4"
    assert fetch_entry(url, "Ex2/c.mp4", dest) == 1234 and calls["n"] == 2
    assert dest.read_bytes() == PAYLOAD["Ex2/c.mp4"]


def test_server_ignoring_range_is_detected(server, tmp_path):
    url, state, _ = server
    state["honour_range"] = False
    with pytest.raises((IOError, zipfile.BadZipFile)):  # zipfile re-labels the IOError raised while reading the index
        fetch_entry(url, "Ex1/b.mp4", tmp_path / "b.mp4")
