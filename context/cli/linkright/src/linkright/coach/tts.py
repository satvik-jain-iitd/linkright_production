"""TTS — macOS `say` primary, espeak/spd-say fallbacks for Linux.

Non-blocking by design: we Popen but never wait(). The candidate sees the
question text immediately while audio plays in the background; if they
type `next` mid-speech, the next question's TTS just queues on top.

Per references/tts_protocol.md from the original skill:
- never display the `say` command in chat
- escape single quotes in text
- per-session voice + rate stored in TTSConfig (slower/faster commands
  mutate it)
- silent fallback to text-only when no TTS engine available
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class TTSConfig:
    """Mutable session-level TTS settings."""

    voice: str = "Samantha"        # macOS default; overridden per platform
    rate: int = 175                # WPM — `say -r N`
    enabled: bool = True
    backend: str = ""              # resolved at first call: say|espeak|spd-say|""


# Module-level singleton shared by all coach modules within one session.
_CONFIG: Optional[TTSConfig] = None


def get_config() -> TTSConfig:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = TTSConfig()
        _resolve_backend(_CONFIG)
    return _CONFIG


def reset_config() -> None:
    """Test/utility — drop the cached singleton so re-detection runs."""
    global _CONFIG
    _CONFIG = None


# ── Backend resolution ────────────────────────────────────────────────────

def _resolve_backend(cfg: TTSConfig) -> None:
    """Detect best available TTS backend. Order: macOS say → espeak-ng →
    spd-say → none. Result cached on cfg.backend."""
    if platform.system() == "Darwin" and shutil.which("say"):
        cfg.backend = "say"
        return
    if shutil.which("espeak-ng"):
        cfg.backend = "espeak-ng"
        # espeak rate is in WPM directly; default 160. Match macOS feel.
        cfg.voice = "en"
        return
    if shutil.which("spd-say"):
        cfg.backend = "spd-say"
        cfg.voice = ""  # spd-say uses default voice
        return
    cfg.backend = ""
    cfg.enabled = False


# ── Public API ────────────────────────────────────────────────────────────

def speak(text: str, *, blocking: bool = False) -> None:
    """Speak `text` via the resolved backend. No-op if TTS disabled.

    blocking=False (default): returns immediately, audio plays async.
    blocking=True: waits for audio to finish (used when ordering matters,
    e.g. greeting before first question).
    """
    cfg = get_config()
    if not cfg.enabled or not cfg.backend:
        return

    cleaned = _strip_markdown(text)
    if not cleaned.strip():
        return

    cmd = _build_command(cfg, cleaned)
    if not cmd:
        return

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if blocking:
            proc.wait()
    except FileNotFoundError:
        # Backend disappeared mid-session (unusual). Disable to avoid
        # repeated failures.
        cfg.enabled = False
    except Exception:
        # Never let TTS failure break the interview flow.
        pass


def set_rate(new_rate: int) -> None:
    """Per `slower` / `faster` commands. Clamped to a safe range."""
    cfg = get_config()
    cfg.rate = max(80, min(280, int(new_rate)))


def set_voice(new_voice: str) -> None:
    """Per `change voice` command. Caller validates against backend."""
    cfg = get_config()
    cfg.voice = new_voice


# ── Internals ─────────────────────────────────────────────────────────────

def _build_command(cfg: TTSConfig, text: str) -> list[str]:
    """Build subprocess argv for the resolved backend."""
    if cfg.backend == "say":
        argv = ["say"]
        if cfg.voice:
            argv += ["-v", cfg.voice]
        argv += ["-r", str(cfg.rate), text]
        return argv
    if cfg.backend == "espeak-ng":
        # espeak: -s sets WPM
        return ["espeak-ng", "-s", str(cfg.rate), "-v", cfg.voice or "en", text]
    if cfg.backend == "spd-say":
        # spd-say doesn't take rate as WPM; -r is -100..+100. Approx mapping.
        rel_rate = max(-100, min(100, (cfg.rate - 175) // 2))
        return ["spd-say", "-r", str(rel_rate), text]
    return []


def _strip_markdown(text: str) -> str:
    """Remove markdown / code-fence chars TTS engines mispronounce."""
    chars_to_strip = ("`", "*", "_", "#", "[", "]", "(", ")", ">", "~")
    out = text
    for ch in chars_to_strip:
        out = out.replace(ch, "")
    return out
