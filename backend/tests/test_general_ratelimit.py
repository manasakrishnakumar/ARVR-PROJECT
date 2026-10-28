from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.ratelimit import RateLimitMiddleware


def make(max_requests=3, window_s=10.0):
    clock = {"t": 0.0}
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, max_requests=max_requests, window_s=window_s, now=lambda: clock["t"])

    @app.get("/x")
    def x():
        return {"ok": True}

    return TestClient(app), clock


def test_requests_over_the_limit_get_429_with_retry_after():
    c, _ = make()
    assert [c.get("/x").status_code for _ in range(3)] == [200] * 3
    r = c.get("/x")
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0


def test_limit_resets_after_the_window():
    c, clock = make()
    for _ in range(4):
        c.get("/x")
    clock["t"] += 11
    assert c.get("/x").status_code == 200


def test_normal_use_is_not_limited_by_default_settings():
    from app.core import ratelimit
    assert ratelimit.MAX_REQUESTS >= 120
