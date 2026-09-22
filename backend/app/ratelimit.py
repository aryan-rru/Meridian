"""A small in-process rate limiter for the auth and import endpoints (§13).

Deliberately simple: a fixed-window counter per (key, client) held in memory. That
is the right scope for a single-instance prototype; a multi-instance deployment
would move this to Redis.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

_lock = threading.Lock()
_hits: dict[tuple[str, str], list[float]] = defaultdict(list)
WINDOW_SECONDS = 60.0


def _client_key(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def enforce(request: Request, bucket: str, limit: int) -> None:
    """Raise 429 when ``bucket`` has been hit more than ``limit`` times this minute."""
    if limit <= 0:
        return
    key = (bucket, _client_key(request))
    now = time.monotonic()
    with _lock:
        recent = [t for t in _hits[key] if now - t < WINDOW_SECONDS]
        if len(recent) >= limit:
            retry_after = int(WINDOW_SECONDS - (now - recent[0])) + 1
            _hits[key] = recent
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests — please wait a moment and try again.",
                headers={"Retry-After": str(retry_after)},
            )
        recent.append(now)
        _hits[key] = recent


def reset() -> None:
    """Test helper."""
    with _lock:
        _hits.clear()
