"""Deterministic per-answer gate for generated ideal answers.

Runs as code before the answer is shown, the same gate-before-the-model-call
discipline the content harness uses. A generated ideal answer that trips a gate
is sent back for one revision with the named issues, instead of being presented
as-is. Cheap, no LLM, no network.

The checks encode what a strong interview answer needs: first person ownership, a
concrete number, enough structure to carry a situation, action, and result, and
real grounding in the candidate's own career facts (not a generic essay).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_STOP = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "is",
    "was", "were", "are", "i", "we", "my", "our", "that", "this", "it", "as",
    "at", "by", "from", "they", "them", "he", "she", "you", "your",
}


@dataclass
class AnswerGate:
    passed: bool
    violations: list[str] = field(default_factory=list)

    def as_feedback(self) -> str:
        return "" if self.passed else "- " + "\n- ".join(self.violations)


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP and len(t) > 2}


def check_ideal_answer(prose: str, grounding_text: str, *, min_overlap: int = 3) -> AnswerGate:
    """Gate a generated ideal answer against the candidate's grounding facts."""
    v: list[str] = []
    text = prose or ""

    # Strip the optional non-resume tier banner so it does not skew the checks.
    body = text.split("\n\n", 1)[-1] if text.startswith("⚑") else text

    if not re.search(r"\bI\b", body):
        v.append("not first person, use I for decisions you owned")

    if not re.search(r"\d", body):
        v.append("no concrete number, an interview answer needs a real metric")

    sentences = [s for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
    if len(sentences) < 3:
        v.append("too thin, carry a situation, the actions you took, and the result")

    g = _tokens(grounding_text)
    if g:
        overlap = len(g & _tokens(body))
        if overlap < min_overlap:
            v.append("not grounded in your career facts, anchor it to a real project and its numbers")

    return AnswerGate(passed=not v, violations=v)
