"""In-memory throttle for failed logins.

Per instance only (Cloud Run runs at most 2), which is enough to make guessing a 12+
character password impractical for a single-user app without adding a datastore.
"""

import time
from collections import defaultdict, deque


class LoginThrottle:
    def __init__(self, max_failures: int = 5, window_seconds: int = 900) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque[float]:
        attempts = self._failures[key]
        while attempts and attempts[0] <= now - self.window_seconds:
            attempts.popleft()
        return attempts

    def retry_after(self, key: str, now: float | None = None) -> int:
        """Seconds until another attempt is allowed; 0 if allowed now."""
        current = time.monotonic() if now is None else now
        attempts = self._prune(key, current)
        if len(attempts) < self.max_failures:
            return 0
        return max(1, int(attempts[0] + self.window_seconds - current))

    def record_failure(self, key: str, now: float | None = None) -> None:
        current = time.monotonic() if now is None else now
        self._prune(key, current).append(current)

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
