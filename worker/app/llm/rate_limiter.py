"""Per-user rate limiter for Gemini API calls.

Ensures calls are spaced apart to stay within RPM limits, scoped per user
so concurrent users don't block each other.

Free tier: 15 RPM → ≥4s between calls (per user).
Paid tier: 1500 RPM → no throttle needed.

Uses per-user asyncio locks to prevent concurrent calls from violating the spacing.
"""

from __future__ import annotations

import asyncio
import logging
import time

logger = logging.getLogger(__name__)

_CLEANUP_AFTER_S = 300  # 5 minutes


class _UserEntry:
    """Tracks last call time and lock for a single user."""

    __slots__ = ("last_call_time", "lock")

    def __init__(self):
        self.last_call_time: float = 0.0
        self.lock = asyncio.Lock()


class UserGeminiLimiter:
    """Per-user async-safe rate limiter for Gemini API calls.

    Each user_id gets independent spacing so 10 concurrent users
    can all make calls without queuing behind each other.

    Usage:
        limiter = UserGeminiLimiter(min_spacing_ms=4000)
        async with limiter(user_id):
            result = await gemini_provider.complete(...)
    """

    def __init__(self, min_spacing_ms: int = 4000):
        self._min_spacing_s = min_spacing_ms / 1000.0
        self._users: dict[str, _UserEntry] = {}
        self._map_lock = asyncio.Lock()

    def __call__(self, user_id: str) -> "_UserLimiterCtx":
        """Return an async context manager scoped to *user_id*."""
        return _UserLimiterCtx(self, user_id)

    async def _get_entry(self, user_id: str) -> _UserEntry:
        async with self._map_lock:
            # Lazy cleanup of stale entries while we hold the lock
            now = time.time()
            stale = [
                uid
                for uid, entry in self._users.items()
                if now - entry.last_call_time > _CLEANUP_AFTER_S
                and not entry.lock.locked()
            ]
            for uid in stale:
                del self._users[uid]

            if user_id not in self._users:
                self._users[user_id] = _UserEntry()
            return self._users[user_id]


class _UserLimiterCtx:
    """Async context manager for a single user's rate-limit window."""

    __slots__ = ("_limiter", "_user_id", "_entry")

    def __init__(self, limiter: UserGeminiLimiter, user_id: str):
        self._limiter = limiter
        self._user_id = user_id
        self._entry: _UserEntry | None = None

    async def __aenter__(self):
        entry = await self._limiter._get_entry(self._user_id)
        self._entry = entry
        await entry.lock.acquire()
        elapsed = time.time() - entry.last_call_time
        if elapsed < self._limiter._min_spacing_s:
            wait = self._limiter._min_spacing_s - elapsed
            logger.debug(
                "GeminiRateLimiter[%s]: waiting %.1fs before next call",
                self._user_id,
                wait,
            )
            await asyncio.sleep(wait)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        assert self._entry is not None
        self._entry.last_call_time = time.time()
        self._entry.lock.release()
        return False


# Singleton instance — shared across all scoring/cover-letter/prep calls
# Callers: `async with gemini_limiter(user_id): ...`
gemini_limiter = UserGeminiLimiter(min_spacing_ms=4000)
