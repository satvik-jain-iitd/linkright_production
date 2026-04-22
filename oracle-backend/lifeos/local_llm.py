"""Local LLM inference via Ollama.

Models:
  gemma3:1b — resume bullet rewriting + quick short generation (benchmark winner 2026-04-22:
               100% invariant survival vs llama3.2:1b's 90%; also fixes silent JSON-parse
               bug in /api/resume/gaps that llama3.2:1b caused).

To update model assignments: change the constants below only.
"""
from __future__ import annotations

import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Model assignments — update here to swap models globally.
# Benchmark 2026-04-22: gemma3:1b wins rewrite (score 122 vs llama3.2:1b 104.8) and
# generate (produces valid JSON where llama3.2:1b + smollm2 produced garbage).
REWRITE_MODEL = "gemma3:1b"
GENERATE_MODEL = "gemma3:1b"

# Keep hot in VRAM for 30 minutes between calls so pipeline phases don't pay
# cold-start latency (~8-12s). Raised from Ollama's default 5m on 2026-04-22.
OLLAMA_KEEP_ALIVE = "30m"


class CircuitBreaker:
    """Simple circuit breaker for Ollama calls.
    After `threshold` failures in `window_seconds`, trips open for `recovery_seconds`.
    """
    def __init__(self, threshold=3, window_seconds=300, recovery_seconds=60):
        self.threshold = threshold
        self.window = window_seconds
        self.recovery = recovery_seconds
        self.failures: list[float] = []
        self.tripped_at: float | None = None

    def is_open(self) -> bool:
        if self.tripped_at and (time.time() - self.tripped_at) < self.recovery:
            return True
        if self.tripped_at and (time.time() - self.tripped_at) >= self.recovery:
            self.tripped_at = None  # half-open: allow one attempt
        return False

    def record_failure(self):
        now = time.time()
        self.failures = [t for t in self.failures if now - t < self.window]
        self.failures.append(now)
        if len(self.failures) >= self.threshold:
            self.tripped_at = now

    def record_success(self):
        self.failures.clear()
        self.tripped_at = None


_ollama_breaker = CircuitBreaker()


def _ollama_generate(model: str, prompt: str, system: str = "", temperature: float = 0.2) -> str:
    """Single Ollama generation call with circuit breaker. Returns raw text."""
    if _ollama_breaker.is_open():
        logger.warning("Ollama circuit breaker OPEN — skipping call (model=%s)", model)
        return ""

    payload: dict = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system

    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        _ollama_breaker.record_success()
        return resp.json().get("response", "").strip()
    except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
        _ollama_breaker.record_failure()
        logger.error("Ollama call failed (model=%s): %s", model, exc)
        return ""


def rewrite(
    prompt: str,
    system: str = "",
    temperature: float = 0.2,
    model: str | None = None,
) -> str:
    """Rewrite text via Ollama. Uses `model` if provided, else REWRITE_MODEL default.

    Args:
        model: Optional override. Callers passing a specific pulled model (e.g.,
               "qwen3:1.7b") route to that model instead of REWRITE_MODEL.
               Allow-list enforcement happens at the HTTP route layer.
    """
    chosen = model or REWRITE_MODEL
    return _ollama_generate(chosen, prompt, system=system, temperature=temperature)


def generate(prompt: str, system: str = "", temperature: float = 0.3) -> str:
    """Short generation using GENERATE_MODEL (gemma3:1b) — for quick answers."""
    return _ollama_generate(GENERATE_MODEL, prompt, system=system, temperature=temperature)
