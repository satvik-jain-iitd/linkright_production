"""Deterministic hard gates for content drafts.

These run as code, before the scored scorecard. A draft that trips a hard gate
is blocked regardless of how well it scores, the same gate-before-rubric split
the LinkRight network skill uses. Gates are config driven, so the engine stays
generic and a user instance can switch on its own house style.

Style config, optional, at ``~/.linkright/content_style.json``::

    {
      "banned_words": ["utilize", "leverage", "ensure", "delve", "robust",
                        "scalable", "paradigm shift", "spearhead", "champion"],
      "allowed_punctuation_only": true,
      "allowed_punctuation": [",", "."],
      "require_signature": true,
      "signature": "‼️",
      "max_sentences_per_paragraph": 2,
      "forbidden_openers": ["excited to share", "in today's fast-paced world"]
    }

With no config file the defaults are permissive, only the voice profile
``avoid_list`` is treated as banned and nothing else blocks. So a fresh install
never gets surprised by gates it did not ask for.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


_STYLE_PATH = Path.home() / ".linkright" / "content_style.json"

# Punctuation that the mobile-syntax rule forbids when allowed_punctuation_only
# is on. Kept here so the check is explicit and testable.
_PUNCT_CANDIDATES = [":", ";", "—", "–", "→", "!", "?", "(", ")", "\"", "/"]


@dataclass
class GateConfig:
    banned_words: list[str] = field(default_factory=list)
    allowed_punctuation_only: bool = False
    allowed_punctuation: list[str] = field(default_factory=lambda: [",", "."])
    require_signature: bool = False
    signature: str = "‼️"  # red double exclamation
    max_sentences_per_paragraph: int = 0  # 0 = unenforced
    forbidden_openers: list[str] = field(default_factory=list)


@dataclass
class GateResult:
    passed: bool
    violations: list[str]

    def as_feedback(self) -> str:
        """One block of plain instructions to feed back into a revise call."""
        if self.passed:
            return ""
        return "Fix these hard rule violations:\n- " + "\n- ".join(self.violations)


def load_gate_config(voice: Optional[dict] = None,
                     style_path: Path = _STYLE_PATH) -> GateConfig:
    """Merge the optional style file with the voice profile avoid_list."""
    cfg = GateConfig()
    if style_path.exists():
        try:
            raw = json.loads(style_path.read_text())
        except Exception:
            raw = {}
        cfg.banned_words = [w.lower() for w in raw.get("banned_words", [])]
        cfg.allowed_punctuation_only = bool(raw.get("allowed_punctuation_only", False))
        cfg.allowed_punctuation = raw.get("allowed_punctuation", [",", "."])
        cfg.require_signature = bool(raw.get("require_signature", False))
        cfg.signature = raw.get("signature", cfg.signature)
        cfg.max_sentences_per_paragraph = int(raw.get("max_sentences_per_paragraph", 0))
        cfg.forbidden_openers = [o.lower() for o in raw.get("forbidden_openers", [])]
    # The voice profile avoid_list is always treated as banned, with or without
    # a style file, so the writer's own stated dislikes are enforced.
    if voice:
        for w in voice.get("avoid_list", []) or []:
            wl = str(w).lower()
            if wl and wl not in cfg.banned_words:
                cfg.banned_words.append(wl)
    return cfg


def _paragraphs(draft: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", draft) if p.strip()]


def _sentences(paragraph: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", paragraph) if s.strip()]


def check(draft: str, config: GateConfig) -> GateResult:
    """Run every enabled gate. Returns a GateResult with a violation list."""
    violations: list[str] = []
    text = draft or ""
    low = text.lower()

    # 1. Banned words. Word-boundary match so "use" inside "because" is safe.
    for w in config.banned_words:
        if not w:
            continue
        if re.search(r"\b" + re.escape(w) + r"\b", low):
            violations.append(f"banned word present: {w!r}")

    # 2. Forbidden openers. Check the first non-empty line.
    paras = _paragraphs(text)
    first_line = (paras[0].splitlines()[0].strip().lower() if paras else "")
    for opener in config.forbidden_openers:
        if first_line.startswith(opener):
            violations.append(f"forbidden opener: {opener!r}")

    # 3. Mobile-syntax punctuation. Only the allowed marks may appear.
    if config.allowed_punctuation_only:
        allowed = set(config.allowed_punctuation)
        # Signature characters are exempt so the hook signature does not trip
        # the punctuation gate.
        sig_chars = set(config.signature)
        for ch in _PUNCT_CANDIDATES:
            if ch in allowed or ch in sig_chars:
                continue
            if ch in text:
                violations.append(f"forbidden punctuation: {ch!r}")

    # 4. Hook signature. The first block's last line must end with it.
    if config.require_signature:
        if config.signature not in text:
            violations.append(f"missing hook signature {config.signature!r}")
        else:
            hook_block = paras[0] if paras else ""
            hook_last = hook_block.splitlines()[-1].strip() if hook_block else ""
            if not hook_last.endswith(config.signature):
                violations.append(
                    f"hook does not end with signature {config.signature!r}"
                )

    # 5. Paragraph length. Each paragraph at most N sentences.
    if config.max_sentences_per_paragraph > 0:
        limit = config.max_sentences_per_paragraph
        for i, p in enumerate(paras, 1):
            n = len(_sentences(p))
            if n > limit:
                violations.append(
                    f"paragraph {i} has {n} sentences, limit is {limit}"
                )

    return GateResult(passed=not violations, violations=violations)


def check_draft(draft: str, voice: Optional[dict] = None) -> GateResult:
    """Convenience, load config then check."""
    return check(draft, load_gate_config(voice))
