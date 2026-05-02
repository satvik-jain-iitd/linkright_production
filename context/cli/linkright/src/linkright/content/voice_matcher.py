"""Extract a voice profile from ~/.linkright/profile/voice-samples.md.

Structural stats via regex + statistics; tone adjectives + avoid_list via one
Gemini JSON call. Returns a dict ready to inject into drafter prompts.
"""
from __future__ import annotations

import re
import statistics
from pathlib import Path
from typing import Optional

from linkright.config import Config
from linkright.llm.direct import gemini_chat_json, LLMError


_NEUTRAL = {
    "tone_adjectives": ["clear", "direct", "thoughtful"],
    "avoid_list": [],
    "sentence_length_mean": 16.0,
    "exclamation_ratio": 0.02,
    "question_ratio": 0.05,
    "hook_style": "observation",
    "connectives": [],
    "samples_found": 0,
}


def _stats(text: str) -> dict:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        return {"sentence_length_mean": 16.0, "exclamation_ratio": 0.0, "question_ratio": 0.0, "connectives": []}
    lens = [len(s.split()) for s in sentences]
    exc = sum(1 for s in sentences if s.endswith("!"))
    q = sum(1 for s in sentences if s.endswith("?"))
    # Favorite connectives (case-insensitive)
    conn_pool = ["because", "so that", "but here's", "the thing is", "honestly", "turns out", "which means"]
    lower = text.lower()
    connectives = [c for c in conn_pool if lower.count(c) >= 2]
    return {
        "sentence_length_mean": round(statistics.mean(lens), 1),
        "exclamation_ratio": round(exc / len(sentences), 3),
        "question_ratio": round(q / len(sentences), 3),
        "connectives": connectives,
    }


def _hook_style(text: str) -> str:
    first_lines = [ln.strip() for ln in text.splitlines() if ln.strip()][:20]
    if any(ln.endswith("?") for ln in first_lines):
        return "question"
    if any(re.match(r"^(I|We|My)\b", ln) for ln in first_lines):
        return "first_person_story"
    if any(re.match(r"^\d", ln) for ln in first_lines):
        return "stat_led"
    return "observation"


def extract_voice_profile(voice_samples_path: Optional[Path] = None) -> dict:
    """Read voice samples, derive heuristic stats + LLM-tone adjectives.

    If the file is missing, returns a neutral profile so downstream drafters
    still work.
    """
    if voice_samples_path is None:
        voice_samples_path = Config.load().profile_dir() / "voice-samples.md"
    if not voice_samples_path.exists():
        return dict(_NEUTRAL)

    text = voice_samples_path.read_text(encoding="utf-8")
    if not text.strip():
        return dict(_NEUTRAL)

    profile = dict(_NEUTRAL)
    profile.update(_stats(text))
    profile["hook_style"] = _hook_style(text)
    profile["samples_found"] = len([p for p in text.split("\n\n") if p.strip()])

    # Single Gemini JSON call for tone adjectives + avoid_list
    schema = {
        "type": "object",
        "properties": {
            "tone_adjectives": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 5},
            "avoid_list": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["tone_adjectives", "avoid_list"],
    }
    try:
        raw, _ = gemini_chat_json(
            system=(
                "You analyze a writer's voice from their samples. "
                "Return 3-5 tone adjectives and a short list of clichés/phrases "
                "this writer notably avoids."
            ),
            user=f"Voice samples:\n\n{text[:8000]}",
            response_schema=schema,
            temperature=0.2,
            max_output_tokens=800,
        )
        import json as _json
        parsed = _json.loads(raw)
        profile["tone_adjectives"] = parsed.get("tone_adjectives") or _NEUTRAL["tone_adjectives"]
        profile["avoid_list"] = parsed.get("avoid_list") or []
    except (LLMError, KeyError, ValueError, Exception):
        # Keep neutral defaults on any failure.
        pass

    return profile
