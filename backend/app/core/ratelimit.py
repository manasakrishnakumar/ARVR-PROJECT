import time
from collections import deque

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

MAX_REQUESTS = 300  # per address per window: far above normal use of the app, low enough to blunt a runaway client
WINDOW_S = 60.0
MAX_TRACKED = 10000


class RateLimitMiddleware:
    """Sliding-window limit on HTTP requests per client address. WebSockets are not limited here (the relay has its own caps)."""

    def __init__(self, app: ASGIApp, max_requests: int = MAX_REQUESTS, window_s: float = WINDOW_S, now=time.monotonic):
        self.app, self.max, self.window, self.now = app, max_requests, window_s, now
        self.hits: dict[str, deque[float]] = {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        key = (scope.get("client") or ("?", 0))[0]
        t = self.now()
        if len(self.hits) > MAX_TRACKED:
            self.hits.clear()
        q = self.hits.setdefault(key, deque())
        while q and t - q[0] > self.window:
            q.popleft()
        if len(q) >= self.max:
            retry = int(self.window - (t - q[0])) + 1
            resp = JSONResponse({"detail": "Too many requests. Slow down."}, status_code=429, headers={"Retry-After": str(retry)})
            return await resp(scope, receive, send)
        q.append(t)
        await self.app(scope, receive, send)
