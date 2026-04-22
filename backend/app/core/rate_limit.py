"""Simple in-memory IP rate limiter for development usage."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock


class InMemoryRateLimiter:
    """Sliding-window rate limiter keyed by client IP."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> tuple[bool, int]:
        """
        Return (allowed, retry_after_seconds).
        retry_after_seconds is 0 when request is allowed.
        """
        now = time.time()
        with self._lock:
            bucket = self._events[key]
            cutoff = now - self.window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
                return False, retry_after

            bucket.append(now)
            return True, 0


_limiter: InMemoryRateLimiter | None = None


def get_rate_limiter(max_requests: int, window_seconds: int = 60) -> InMemoryRateLimiter:
    """Singleton-ish limiter shared across app workers (process-local)."""
    global _limiter
    if _limiter is None:
        _limiter = InMemoryRateLimiter(max_requests=max_requests, window_seconds=window_seconds)
    return _limiter
