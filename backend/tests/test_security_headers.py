from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.security_headers import HEADERS, SecurityHeadersMiddleware


def client(base="http://testserver"):
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/x")
    def x():
        return {"ok": True}

    return TestClient(app, base_url=base)


def test_headers_are_added_on_http_without_hsts():
    r = client().get("/x")
    for k, v in HEADERS.items():
        assert r.headers[k] == v
    assert "strict-transport-security" not in r.headers


def test_hsts_only_over_https():
    r = client("https://testserver").get("/x")
    assert r.headers["strict-transport-security"].startswith("max-age=")


def test_the_real_app_sends_them_and_the_camera_policy_allows_only_this_site():
    from app.main import app

    with TestClient(app) as c:
        r = c.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "camera=(self)" in r.headers["permissions-policy"]
