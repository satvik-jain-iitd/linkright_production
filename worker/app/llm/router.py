"""Phase-aware LLM provider router.

Every pipeline phase asks the router "give me an LLM for this phase" and
the router returns the cheapest provider that has capacity RIGHT NOW. If
no provider in the preference list has capacity, it awaits until one does
OR raises RateLimitExhausted if even waiting can't help (daily RPD dry).

Routing rules (preference order per phase):
    phase_1_2      → groq-70b, gemini, groq-8b
    phase_3_5a     → oracle, groq-8b
    phase_4a       → groq-70b, gemini
    phase_4c       → oracle, groq-8b
    phase_5        → oracle, groq-8b
    default        → groq-70b, gemini, groq-8b

Gemini is never first choice — its daily quota (1500/key) is the tightest.

Circuit breaker:
    If a provider errors 3x in 60s, the router skips it for the rest of
    the minute. Prevents tight-loop amplification when a provider is down.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional

from .base import LLMProvider
from .rate_governor import RateGovernor, RateLimitExhausted, get_governor

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# Provider identity + keys loaded from env at module import.
# Falls back to ctx.api_key at call time if env keys missing.
# ────────────────────────────────────────────────────────────────────────────

def _load_gemini_keys() -> list[str]:
    keys: list[str] = []
    for n in ("GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GEMINI_API_KEY"):
        v = os.environ.get(n)
        if v and v not in keys:
            keys.append(v)
    return keys


def _load_groq_key() -> str:
    return (
        os.environ.get("PLATFORM_GROQ_API_KEY")
        or os.environ.get("GROQ_API_KEY", "")
    )


def _load_oracle() -> tuple[str, str]:
    return (
        os.environ.get("ORACLE_BACKEND_URL", ""),
        os.environ.get("ORACLE_BACKEND_SECRET", ""),
    )


def _load_openrouter_key() -> str:
    """OpenRouter tertiary fallback (F07). Uses Llama 3.3 70B (same class as Groq primary)."""
    return os.environ.get("OPENROUTER_API_KEY", "")


def _load_cerebras_key() -> str:
    """Cerebras quaternary fallback (F07). Llama 3.3 70B via OpenAI-compatible endpoint."""
    return os.environ.get("CEREBRAS_API_KEY", "")


# ────────────────────────────────────────────────────────────────────────────
# Provider preference list per phase
# Each entry: (kind, model_id) — the router hydrates into a real provider.
# "kind" maps to the factory below.
# ────────────────────────────────────────────────────────────────────────────

# Quality-first routing — user's stated goal: 20 high-quality resumes/user/day
# (2026-04-17). Oracle 1B demoted to LAST RESORT because its JSON output was
# unreliable in testing. Gemini preferred for reasoning-heavy phases (1+2, 4a)
# because it's smarter at structured output than Groq 70B.
#
# Capacity math (worst case 10 active users × 20 resumes × ~7 LLM calls):
#   Per resume:  2 Gemini (phase_1_2 + phase_4a) + 3 Groq 70B (3_5a, 4a-fallback, 4c)
#   Daily total: 400 Gemini calls (in 4500 RPD × 3 keys) ✓
#                600 Groq calls (in 14400 RPD) ✓
_PHASE_ROUTES: dict[str, list[tuple[str, str]]] = {
    # Parse JD + strategy: Gemini is best at JSON + structured output.
    # F07 tertiary/quaternary: OpenRouter + Cerebras with Llama 3.3 70B keeps the
    # pipeline alive when Groq + free-tier Gemini keys are both exhausted.
    "phase_1_2":    [
        ("gemini", "gemini-2.0-flash"),
        ("groq", "llama-3.3-70b-versatile"),
        ("openrouter", "meta-llama/llama-3.3-70b-instruct"),
        ("cerebras", "llama-3.3-70b"),
    ],
    "phase_3_5a":   [
        ("groq", "llama-3.3-70b-versatile"),
        ("gemini", "gemini-2.0-flash"),
        ("openrouter", "meta-llama/llama-3.3-70b-instruct"),
        ("cerebras", "llama-3.3-70b"),
    ],
    "phase_4a":     [
        ("gemini", "gemini-2.0-flash"),
        ("groq", "llama-3.3-70b-versatile"),
        ("openrouter", "meta-llama/llama-3.3-70b-instruct"),
        ("cerebras", "llama-3.3-70b"),
    ],
    "phase_4c":     [
        ("groq", "llama-3.3-70b-versatile"),
        ("gemini", "gemini-2.0-flash"),
        ("openrouter", "meta-llama/llama-3.3-70b-instruct"),
        ("cerebras", "llama-3.3-70b"),
    ],
    "phase_5":      [
        ("groq", "llama-3.3-70b-versatile"),
        ("gemini", "gemini-2.0-flash"),
        ("openrouter", "meta-llama/llama-3.3-70b-instruct"),
        ("cerebras", "llama-3.3-70b"),
    ],
    "default":      [
        ("gemini", "gemini-2.0-flash"),
        ("groq", "llama-3.3-70b-versatile"),
        ("openrouter", "meta-llama/llama-3.3-70b-instruct"),
        ("cerebras", "llama-3.3-70b"),
    ],
}


# ────────────────────────────────────────────────────────────────────────────
# Circuit breaker state
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class _CircuitState:
    recent_errors: list[float] = field(default_factory=list)  # timestamps
    open_until: float = 0.0  # epoch seconds


_circuits: dict[tuple[str, str], _CircuitState] = {}
_CIRCUIT_WINDOW_S = 60.0
_CIRCUIT_THRESHOLD = 3
_CIRCUIT_TRIP_DURATION_S = 60.0


def _circuit_for(provider_kind: str, key_hash: str) -> _CircuitState:
    k = (provider_kind, key_hash)
    if k not in _circuits:
        _circuits[k] = _CircuitState()
    return _circuits[k]


def _circuit_open(state: _CircuitState) -> bool:
    return time.time() < state.open_until


def record_provider_error(provider_kind: str, api_key: str) -> None:
    """Call this on any non-retryable provider error (5xx, repeated 429, auth)."""
    from .rate_governor import _key_hash  # local import to avoid cycle
    state = _circuit_for(provider_kind, _key_hash(api_key))
    now = time.time()
    state.recent_errors = [t for t in state.recent_errors if now - t < _CIRCUIT_WINDOW_S]
    state.recent_errors.append(now)
    if len(state.recent_errors) >= _CIRCUIT_THRESHOLD:
        state.open_until = now + _CIRCUIT_TRIP_DURATION_S
        state.recent_errors.clear()
        logger.warning(
            "router: circuit OPEN for %s (next %.0fs)", provider_kind, _CIRCUIT_TRIP_DURATION_S
        )


# ────────────────────────────────────────────────────────────────────────────
# Provider factory cache
# ────────────────────────────────────────────────────────────────────────────

_provider_cache: dict[tuple[str, str, str], LLMProvider] = {}


def _make_provider(kind: str, model_id: str, api_key: str) -> Optional[LLMProvider]:
    """Instantiate (and cache) a provider for a (kind, model, key) triple."""
    cache_key = (kind, model_id, api_key)
    if cache_key in _provider_cache:
        return _provider_cache[cache_key]

    p: Optional[LLMProvider] = None
    if kind == "groq":
        if not api_key:
            return None
        from .groq import GroqProvider
        p = GroqProvider(api_key=api_key, model_id=model_id)
    elif kind == "gemini":
        if not api_key:
            return None
        from .gemini import GeminiProvider
        p = GeminiProvider(api_key=api_key, model_id=model_id)
    elif kind == "oracle":
        base_url, secret = _load_oracle()
        if not base_url or not secret:
            return None
        from .oracle import OracleProvider
        p = OracleProvider(base_url=base_url, secret=secret, endpoint="rewrite")
    elif kind == "openrouter":
        if not api_key:
            return None
        from .openrouter import OpenRouterProvider
        p = OpenRouterProvider(api_key=api_key, model_id=model_id)
    elif kind == "cerebras":
        if not api_key:
            return None
        from .openai_compat import OpenAICompatProvider
        p = OpenAICompatProvider(
            api_key=api_key,
            model_id=model_id,
            base_url="https://api.cerebras.ai/v1",
        )

    if p is not None:
        _provider_cache[cache_key] = p
    return p


# ────────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────────

async def pick_for(
    phase: str,
    *,
    fallback_key: Optional[str] = None,
    max_wait: float = 30.0,
) -> tuple[LLMProvider, str, str]:
    """Return (provider, kind, key_used) that has capacity for this phase.

    Walks the phase's preference list, checking rate-governor capacity on each.
    The first provider that either (a) has a token right now or (b) will have
    one within max_wait seconds is chosen. For Gemini specifically, each of
    the 3 rotation keys is checked individually.

    If all candidates have exhausted their RPD for the day → RateLimitExhausted.

    If all candidates are rate-limited within the minute but RPD isn't dry,
    this awaits on the best option (shortest wait).
    """
    routes = _PHASE_ROUTES.get(phase, _PHASE_ROUTES["default"])
    governor = get_governor()
    tried: list[str] = []

    # Expand "gemini" entries into one per rotation key
    expanded: list[tuple[str, str, str]] = []  # (kind, model, key)
    gemini_keys = _load_gemini_keys()
    groq_key = _load_groq_key()
    oracle_url, oracle_secret = _load_oracle()

    openrouter_key = _load_openrouter_key()
    cerebras_key = _load_cerebras_key()

    for kind, model in routes:
        if kind == "gemini":
            for k in gemini_keys:
                expanded.append((kind, model, k))
        elif kind == "groq":
            if groq_key:
                expanded.append((kind, model, groq_key))
        elif kind == "oracle":
            if oracle_url and oracle_secret:
                # Oracle uses secret-as-key for bucket identity
                expanded.append((kind, model, oracle_secret))
        elif kind == "openrouter":
            if openrouter_key:
                expanded.append((kind, model, openrouter_key))
        elif kind == "cerebras":
            if cerebras_key:
                expanded.append((kind, model, cerebras_key))

    # Fallback key as last resort if nothing wired
    if fallback_key and not expanded:
        expanded.append(("groq", "llama-3.3-70b-versatile", fallback_key))

    from .rate_governor import _key_hash

    # Filter out circuit-open providers
    live = []
    for kind, model, key in expanded:
        circuit = _circuit_for(kind, _key_hash(key))
        if _circuit_open(circuit):
            tried.append(f"{kind}(circuit-open)")
            continue
        live.append((kind, model, key))

    if not live:
        raise RateLimitExhausted(phase, tried)

    # Pick the candidate with the shortest wait (ideally 0)
    best: Optional[tuple[float, str, str, str]] = None
    all_rpd_dry = True
    for kind, model, key in live:
        wait = await governor.time_until_available(kind, key)
        # Distinguish "rate limited this minute" from "RPD dry today"
        # RPD dry = wait is effectively infinite; we detect via rpd_exhausted
        if wait < 3600:  # within an hour = not RPD dry
            all_rpd_dry = False
        if best is None or wait < best[0]:
            best = (wait, kind, model, key)

    if all_rpd_dry:
        raise RateLimitExhausted(phase, [f"{k}:{m}" for k, m, _ in live])

    assert best is not None
    wait, kind, model, key = best
    # Acquire token (will await the wait if any)
    acquired = await governor.acquire(kind, key, max_wait=max_wait)
    if not acquired:
        raise RateLimitExhausted(phase, [f"{k}:{m}" for k, m, _ in live])

    provider = _make_provider(kind, model, key)
    if provider is None:
        raise RuntimeError(f"router: could not instantiate {kind}:{model}")

    logger.info("router: phase=%s → %s:%s (wait=%.1fs)", phase, kind, model, wait)
    return provider, kind, key
