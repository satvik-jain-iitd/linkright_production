"""Proactive per-provider rate governor (token buckets + RPD tracking).

Why this exists:
    Previously each provider retried on 429 with exponential backoff. When
    multiple calls queued up, backoff times compounded — a single failing
    call could hold a pipeline job for 5+ minutes. This module replaces
    reactive retry with *proactive throttling*: before dispatching a call,
    acquire a token from the rate bucket. If the bucket is dry, await
    until it refills. Callers never see 429s — only the wait.

Invariants:
    * RPM bucket: capacity=limit_rpm, refills at limit_rpm/60 tokens/sec.
    * RPD bucket: capacity=limit_rpd, refills to full at UTC midnight.
    * Both buckets must have a token before acquire() returns.
    * Usage persisted to Supabase provider_usage on every acquire so
      worker restarts don't lose the day's count.

Usage:
    governor = RateGovernor(sb)
    await governor.acquire("gemini", api_key)   # blocks if needed
    resp = await client.post(...)               # make the API call
    # No explicit release — token is consumed on acquire.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# Default limits — free-tier numbers. Overridable per-key via set_limits().
# ────────────────────────────────────────────────────────────────────────────

DEFAULT_LIMITS: dict[str, dict[str, int]] = {
    "gemini":     {"rpm": 15,  "rpd": 1500},   # per key
    "groq":       {"rpm": 30,  "rpd": 14400},  # shared across models on one key
    "openrouter": {"rpm": 20,  "rpd": 200},
    # F07 tertiary: Cerebras Cloud free tier ≈ 30 RPM; generous RPD. Tune once
    # real-world data lands.
    "cerebras":   {"rpm": 30,  "rpd": 14400},
    "oracle":     {"rpm": 9999, "rpd": 9999999},  # effectively unlimited (homelab)
}


def _key_hash(key: str) -> str:
    """SHA256 prefix for identifying a key in logs/DB without exposing it."""
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


@dataclass
class _Bucket:
    """Simple token bucket with continuous refill."""
    capacity: float
    tokens: float
    refill_rate: float  # tokens per second
    last_refill: float = field(default_factory=lambda: asyncio.get_event_loop().time())

    def _refill(self) -> None:
        now = asyncio.get_event_loop().time()
        delta = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + delta * self.refill_rate)
        self.last_refill = now

    def time_until_token(self) -> float:
        """Seconds until at least one token is available (0 if ready now)."""
        self._refill()
        if self.tokens >= 1:
            return 0.0
        return (1 - self.tokens) / self.refill_rate

    def take(self) -> bool:
        self._refill()
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class RateGovernor:
    """Per-(provider, key) token buckets + per-day usage tracking.

    Thread/asyncio-safe via a single asyncio.Lock per (provider, key) combo.
    Buckets live in-memory (fast path). Daily count is persisted to Supabase
    on every acquire (with a small buffer to avoid write-amplification).
    """

    # Persist to DB every N acquires per key (buffered writes)
    _DB_FLUSH_EVERY = 5

    def __init__(self, sb: Optional[object] = None):
        self._sb = sb
        self._buckets_rpm: dict[tuple[str, str], _Bucket] = {}
        self._buckets_rpd: dict[tuple[str, str], _Bucket] = {}
        self._limits: dict[str, dict[str, int]] = dict(DEFAULT_LIMITS)
        self._key_limits: dict[tuple[str, str], dict[str, int]] = {}
        self._unflushed: dict[tuple[str, str], int] = {}
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}
        self._rehydrated: set[tuple[str, str]] = set()

    # ── public API ──────────────────────────────────────────────────────────

    def set_limits(self, provider: str, api_key: str, rpm: int, rpd: int) -> None:
        """Override default limits for a specific (provider, key)."""
        kh = _key_hash(api_key)
        self._key_limits[(provider, kh)] = {"rpm": rpm, "rpd": rpd}
        # Reset buckets so new limits apply
        self._buckets_rpm.pop((provider, kh), None)
        self._buckets_rpd.pop((provider, kh), None)

    async def time_until_available(self, provider: str, api_key: str) -> float:
        """Returns seconds caller must wait before acquire() would succeed.
        Zero means ready. Does NOT consume a token."""
        provider, kh, rpm_bucket, rpd_bucket = await self._ensure(provider, api_key)
        return max(rpm_bucket.time_until_token(), rpd_bucket.time_until_token())

    async def has_capacity(self, provider: str, api_key: str) -> bool:
        """Non-blocking check. True if both RPM and RPD have a token right now."""
        return await self.time_until_available(provider, api_key) == 0.0

    async def rpd_exhausted(self, provider: str, api_key: str) -> bool:
        """True if today's RPD is fully consumed (different from RPM — permanent until midnight)."""
        provider, kh, _, rpd_bucket = await self._ensure(provider, api_key)
        return rpd_bucket.tokens < 1 and rpd_bucket.refill_rate == 0

    async def acquire(self, provider: str, api_key: str, max_wait: float = 30.0) -> bool:
        """Blocks until one token is available from both buckets, then consumes it.
        Returns True on success, False if max_wait elapsed (means RPD exhausted)."""
        provider, kh, rpm_bucket, rpd_bucket = await self._ensure(provider, api_key)
        async with self._lock_for(provider, kh):
            start = asyncio.get_event_loop().time()
            while True:
                # RPD first — if this is hopeless (no refill till midnight), bail early.
                rpd_wait = rpd_bucket.time_until_token()
                if rpd_wait > max_wait:
                    return False
                rpm_wait = rpm_bucket.time_until_token()
                wait = max(rpm_wait, rpd_wait)
                if wait == 0 and rpm_bucket.take() and rpd_bucket.take():
                    self._record_consumption(provider, kh)
                    return True
                elapsed = asyncio.get_event_loop().time() - start
                if elapsed + wait > max_wait:
                    return False
                if wait > 0:
                    logger.debug(
                        "rate_governor: %s/%s waiting %.1fs (rpm=%s, rpd=%s)",
                        provider, kh, wait, rpm_wait, rpd_wait,
                    )
                    await asyncio.sleep(wait)

    # ── internals ───────────────────────────────────────────────────────────

    def _limits_for(self, provider: str, key_hash: str) -> dict[str, int]:
        return self._key_limits.get((provider, key_hash)) or self._limits.get(
            provider, {"rpm": 10, "rpd": 1000}  # conservative fallback for unknown providers
        )

    def _lock_for(self, provider: str, key_hash: str) -> asyncio.Lock:
        k = (provider, key_hash)
        if k not in self._locks:
            self._locks[k] = asyncio.Lock()
        return self._locks[k]

    async def _ensure(self, provider: str, api_key: str) -> tuple[str, str, _Bucket, _Bucket]:
        kh = _key_hash(api_key)
        limits = self._limits_for(provider, kh)
        k = (provider, kh)

        # Rehydrate today's consumption from DB on first use
        if k not in self._rehydrated:
            await self._rehydrate(provider, kh)
            self._rehydrated.add(k)

        if k not in self._buckets_rpm:
            self._buckets_rpm[k] = _Bucket(
                capacity=limits["rpm"], tokens=limits["rpm"],
                refill_rate=limits["rpm"] / 60.0,
            )
        if k not in self._buckets_rpd:
            # RPD bucket: no continuous refill; we set tokens to remaining quota
            # and only "refill" at midnight UTC (handled by _reset_if_new_day).
            starting = max(0, limits["rpd"] - self._unflushed.get(k, 0))
            self._buckets_rpd[k] = _Bucket(
                capacity=limits["rpd"], tokens=starting,
                refill_rate=0.0,
            )
        self._reset_if_new_day(provider, kh)
        return provider, kh, self._buckets_rpm[k], self._buckets_rpd[k]

    def _reset_if_new_day(self, provider: str, key_hash: str) -> None:
        """Refill RPD bucket to full capacity if it's a new UTC day."""
        k = (provider, key_hash)
        rpd_bucket = self._buckets_rpd.get(k)
        if not rpd_bucket:
            return
        today = _today_utc()
        last_day = getattr(rpd_bucket, "_day_tag", None)
        if last_day is None:
            rpd_bucket._day_tag = today  # type: ignore[attr-defined]
            return
        if last_day != today:
            limits = self._limits_for(provider, key_hash)
            rpd_bucket.tokens = limits["rpd"]
            rpd_bucket.capacity = limits["rpd"]
            rpd_bucket._day_tag = today  # type: ignore[attr-defined]
            self._unflushed[k] = 0

    def _record_consumption(self, provider: str, key_hash: str) -> None:
        k = (provider, key_hash)
        self._unflushed[k] = self._unflushed.get(k, 0) + 1
        if self._unflushed[k] >= self._DB_FLUSH_EVERY:
            # fire-and-forget DB update
            asyncio.create_task(self._flush(provider, key_hash, self._unflushed[k]))
            self._unflushed[k] = 0

    async def _flush(self, provider: str, key_hash: str, increment: int) -> None:
        if not self._sb:
            return
        try:
            # Upsert-style increment: select, add, update. Small race OK
            # (worst case we undercount by a few — safe side).
            today = _today_utc()
            existing = (
                self._sb.table("provider_usage")
                .select("rpd_used")
                .eq("provider", provider)
                .eq("key_hash", key_hash)
                .eq("date_utc", today)
                .execute()
            )
            if existing.data:
                new_count = (existing.data[0].get("rpd_used") or 0) + increment
                self._sb.table("provider_usage").update(
                    {"rpd_used": new_count, "updated_at": datetime.now(timezone.utc).isoformat()}
                ).eq("provider", provider).eq("key_hash", key_hash).eq("date_utc", today).execute()
            else:
                self._sb.table("provider_usage").insert({
                    "provider": provider,
                    "key_hash": key_hash,
                    "date_utc": today,
                    "rpd_used": increment,
                }).execute()
        except Exception as exc:
            logger.warning("rate_governor: flush failed — %s", exc)

    async def _rehydrate(self, provider: str, key_hash: str) -> None:
        if not self._sb:
            return
        try:
            today = _today_utc()
            r = (
                self._sb.table("provider_usage")
                .select("rpd_used")
                .eq("provider", provider)
                .eq("key_hash", key_hash)
                .eq("date_utc", today)
                .execute()
            )
            if r.data:
                self._unflushed[(provider, key_hash)] = r.data[0].get("rpd_used") or 0
        except Exception as exc:
            logger.debug("rate_governor: rehydrate skipped — %s", exc)


# ────────────────────────────────────────────────────────────────────────────
# Module-level singleton (import-time lazy init). Use set_supabase() to wire DB.
# ────────────────────────────────────────────────────────────────────────────

_governor: Optional[RateGovernor] = None


def get_governor() -> RateGovernor:
    global _governor
    if _governor is None:
        _governor = RateGovernor()
    return _governor


def set_supabase(sb) -> None:
    """Wire Supabase client for persistence. Call once at worker startup."""
    get_governor()._sb = sb


class RateLimitExhausted(Exception):
    """Raised when every available provider's RPD is exhausted for today.
    Caller (pipeline) catches and defers job to next UTC midnight."""

    def __init__(self, phase: str, providers_tried: list[str]):
        self.phase = phase
        self.providers_tried = providers_tried
        super().__init__(
            f"Rate limit exhausted for phase={phase}; tried={providers_tried}"
        )
