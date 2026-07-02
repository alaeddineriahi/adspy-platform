"""
Rate limiting — fixed-window counters, in-process.

Pure ASGI middleware (no response buffering, so streaming endpoints keep
streaming). Keys on the bearer token when present, else client IP. Windows
are per-minute; AI endpoints get a tight budget since they cost real LLM
tokens, everything else gets a generous one that only stops abuse.

In-memory is fine while the API is a single uvicorn process; move the
counters to Redis if this ever runs multi-worker.
"""

import hashlib
import time

from starlette.responses import JSONResponse

# (path prefix, max requests per 60s window) — first match wins.
RULES = [
    ("/api/ai", 20),
    ("/api/mediabuyer", 20),
    ("/api/payments", 30),
    ("/api/ingestion/run", 6),
    ("/api/", 240),
]


class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app
        self._counts: dict[tuple, int] = {}
        self._window_start = 0

    def _client_key(self, scope) -> str:
        for name, value in scope.get("headers") or []:
            if name == b"authorization" and value:
                return hashlib.sha1(value).hexdigest()[:16]
        client = scope.get("client")
        return client[0] if client else "unknown"

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("method") == "OPTIONS":
            return await self.app(scope, receive, send)

        path = scope.get("path", "")
        rule = next((r for r in RULES if path.startswith(r[0])), None)
        if rule is None:
            return await self.app(scope, receive, send)

        window = int(time.time() // 60)
        if window != self._window_start:  # new minute — drop all old counters
            self._counts.clear()
            self._window_start = window

        key = (self._client_key(scope), rule[0])
        count = self._counts.get(key, 0) + 1
        self._counts[key] = count

        if count > rule[1]:
            response = JSONResponse(
                {"detail": "Rate limit exceeded — slow down and retry in a minute."},
                status_code=429,
                headers={"Retry-After": str(60 - int(time.time() % 60))},
            )
            return await response(scope, receive, send)

        return await self.app(scope, receive, send)
