from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from time import monotonic

from app.core.config import settings
from app.exceptions.base import AppError
from app.exceptions.codes import ErrorCode


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str, limit: int | None = None, window: int | None = None) -> None:
        if not settings.rate_limit_enabled:
            return
        limit = limit or settings.rate_limit_requests
        window = window or settings.rate_limit_window_seconds
        now = monotonic()
        async with self._lock:
            events = self._events[key]
            while events and now - events[0] >= window:
                events.popleft()
            if len(events) >= limit:
                raise AppError(ErrorCode.RATE_LIMITED, "Too many requests", 429)
            events.append(now)


rate_limiter = InMemoryRateLimiter()
