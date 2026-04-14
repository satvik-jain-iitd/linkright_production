"""Local LLM inference via Ollama.

Models:
  llama3.2:1b  — resume bullet rewriting (fast, instruction-following)
  smollm2:135m — quick generation / short answers

To update model assignments: change the constants below only.
"""
from __future__ import annotations

import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Model assignments — update here to swap models globally
REWRITE_MODEL = "llama3.2:1b"      # bullet rewriting / sentence tweaking
GENERATE_MODEL = "smollm2:135m"    # quick short generation


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


def rewrite(prompt: str, system: str = "", temperature: float = 0.2) -> str:
    """Rewrite text using llama3.2:1b — for resume bullets and sentence tweaking."""
    return _ollama_generate(REWRITE_MODEL, prompt, system=system, temperature=temperature)


def generate(prompt: str, system: str = "", temperature: float = 0.3) -> str:
    """Short generation using smollm2:135m — for quick answers."""
    return _ollama_generate(GENERATE_MODEL, prompt, system=system, temperature=temperature)
