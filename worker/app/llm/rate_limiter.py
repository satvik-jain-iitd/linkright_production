"""Rate limiter for Gemini API calls.

Ensures calls are spaced apart to stay within RPM limits.
Free tier: 15 RPM → ≥4s between calls.
Paid tier: 1500 RPM → no throttle needed.

Uses an asyncio lock to prevent concurrent calls from violating the spacing.
"""

from __future__ import annotations

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class GeminiRateLimiter:
    """Async-safe rate limiter for Gemini API calls.

    Usage:
        limiter = GeminiRateLimiter(min_spacing_ms=4000)
        async with limiter:
            result = await gemini_provider.complete(...)
    """

    def __init__(self, min_spacing_ms: int = 4000):
        self._min_spacing_s = min_spacing_ms / 1000.0
        self._last_call_time: float = 0.0
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        await self._lock.acquire()
        elapsed = time.time() - self._last_call_time
        if elapsed < self._min_spacing_s:
            wait = self._min_spacing_s - elapsed
            logger.debug("GeminiRateLimiter: waiting %.1fs before next call", wait)
            await asyncio.sleep(wait)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._last_call_time = time.time()
        self._lock.release()
        return False


# Singleton instance — shared across all scoring/cover-letter/prep calls
gemini_limiter = GeminiRateLimiter(min_spacing_ms=4000)
