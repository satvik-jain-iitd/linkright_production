"""Local LLM inference via Ollama.

Models:
  llama3.2:1b  — resume bullet rewriting (fast, instruction-following)
  smollm2:135m — quick generation / short answers

To update model assignments: change the constants below only.
"""
from __future__ import annotations

import os
import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Model assignments — update here to swap models globally
REWRITE_MODEL = "llama3.2:1b"      # bullet rewriting / sentence tweaking
GENERATE_MODEL = "smollm2:135m"    # quick short generation


def _ollama_generate(model: str, prompt: str, system: str = "", temperature: float = 0.2) -> str:
    """Single Ollama generation call. Returns raw text."""
    payload: dict = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["system"] = system

    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def rewrite(prompt: str, system: str = "", temperature: float = 0.2) -> str:
    """Rewrite text using llama3.2:1b — for resume bullets and sentence tweaking."""
    return _ollama_generate(REWRITE_MODEL, prompt, system=system, temperature=temperature)


def generate(prompt: str, system: str = "", temperature: float = 0.3) -> str:
    """Short generation using smollm2:135m — for quick answers."""
    return _ollama_generate(GENERATE_MODEL, prompt, system=system, temperature=temperature)
