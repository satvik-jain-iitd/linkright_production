"""Self-correcting content loop, the CLI side of the LinkRight harness.

One brain across surfaces. This loop runs the same shape the network skill runs,
ground the draft in career memory, draft it, gate it on hard rules, score it on
the rubric, and if it fails feed the exact reasons back and revise. It stops when
the draft clears the hard gates and meets the score threshold, or when it runs
out of iterations.

Deterministic first. The gates are code and the scorecard is heuristic, so most
of each pass costs nothing. The model is only asked to draft and to revise, and
the revise call is given precise instructions, not a vague try again.

Everything heavy is injectable, so the loop runs fully offline in tests.
"""
from __future__ import annotations

import re
import statistics
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from linkright.content import gates
from linkright.content.grounding import Grounding, retrieve_grounding
from linkright.content.scorecard import ContentScorecard

_LENGTH_TARGET = {"short": 600, "medium": 1200, "long": 2000}


@dataclass
class IterationRecord:
    iteration: int
    score: float
    grade: str
    gate_passed: bool
    violations: list[str]


@dataclass
class LoopResult:
    draft: str
    score: float
    grade: str
    passed: bool
    gate_passed: bool
    violations: list[str]
    grounding_mode: str
    iterations: list[IterationRecord]
    provenance: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        head = "PASS" if self.passed else "BELOW THRESHOLD"
        return (f"{head}  score={round(self.score,1)} grade={self.grade}  "
                f"gates={'ok' if self.gate_passed else 'failed'}  "
                f"iters={len(self.iterations)}  grounding={self.grounding_mode}")


# ── scorecard context ───────────────────────────────────────────────────────

def _build_context(draft: str, kind: str, voice: dict, target_len: int) -> dict[str, Any]:
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", draft) if s.strip()]
    lens = [len(s.split()) for s in sentences] or [0]
    sd = statistics.pstdev(lens) if len(lens) > 1 else 0.0

    # Voice overlap, fraction of the writer's tone words and connectives that
    # actually show up in the draft. Cheap proxy for "sounds like them".
    low = draft.lower()
    markers = [m.lower() for m in
               (voice.get("tone_adjectives", []) + voice.get("connectives", []))]
    overlap = (sum(1 for m in markers if m in low) / len(markers) * 100.0) if markers else 50.0

    return {
        "draft": draft,
        "kind": kind,
        "voice_overlap_score": overlap,
        "sentence_length_stddev": sd,
        "target_len": target_len,
        "actual_len": len(draft),
        "hashtag_count": len(re.findall(r"#\w+", draft)),
        "thread_numbered": bool(re.search(r"^\s*1[\.\)]", draft, re.M)),
    }


def _score(draft: str, kind: str, voice: dict, target_len: int) -> ContentScorecard:
    card = ContentScorecard(run_id=uuid.uuid4().hex[:8])
    card.score(_build_context(draft, kind, voice, target_len))
    return card


# ── revise ──────────────────────────────────────────────────────────────────

def _default_llm(system: str, user: str) -> str:
    from linkright.llm.direct import chat_with_fallback, LLMError
    try:
        text, _usage = chat_with_fallback(system, user, temperature=0.3, max_tokens=2500)
        return text
    except LLMError:
        return ""


def _revise(draft: str, voice: dict, evidence: str, gate: gates.GateResult,
            card: ContentScorecard, kind: str, llm_fn: Callable[[str, str], str]) -> str:
    weak = sorted(card.results, key=lambda r: r.score)[:3]
    weak_lines = "\n".join(f"- raise {r.name}, currently {round(r.score)}" for r in weak)
    instructions = []
    if not gate.passed:
        instructions.append(gate.as_feedback())
    if weak_lines:
        instructions.append("Weakest rubric dimensions:\n" + weak_lines)
    if not instructions:
        return draft

    system = (
        "You are revising a piece of content. Keep the writer's voice and every "
        "true claim. Change only what the instructions below require. Return only "
        "the revised piece, no commentary.\n"
        "House style rules are hard, never break them.\n"
        + (("\n" + evidence) if evidence else "")
    )
    user = (
        "Current draft:\n\n" + draft
        + "\n\n---\nRequired fixes:\n" + "\n\n".join(instructions)
    )
    revised = llm_fn(system, user)
    return revised.strip() if revised and len(revised.strip()) > 80 else draft


# ── main entry ───────────────────────────────────────────────────────────────

def run_content_loop(
    topic: str,
    *,
    kind: str = "linkedin_post",
    length: str = "medium",
    max_iters: int = 3,
    threshold: float = 75.0,
    ground: bool = True,
    voice: Optional[dict] = None,
    draft_fn: Optional[Callable[..., str]] = None,
    llm_fn: Optional[Callable[[str, str], str]] = None,
    profile_dir=None,
) -> LoopResult:
    """Run draft, gate, score, revise until the draft passes or iters run out."""
    if voice is None:
        from linkright.content.voice_matcher import extract_voice_profile
        voice = extract_voice_profile()
    if draft_fn is None:
        from linkright.content.drafter import draft_content
        draft_fn = draft_content
    if llm_fn is None:
        llm_fn = _default_llm

    target_len = _LENGTH_TARGET.get(length, 1200)

    grounding: Grounding
    if ground:
        try:
            grounding = retrieve_grounding(topic, profile_dir=profile_dir)
        except Exception:
            grounding = Grounding(facts=[], signals=[], mode="keyword")
    else:
        grounding = Grounding(facts=[], signals=[], mode="off")
    evidence = grounding.as_block()
    gate_cfg = gates.load_gate_config(voice)

    # First draft. Pass evidence if the drafter accepts it, stay compatible if not.
    try:
        draft = draft_fn(topic, kind, voice, length, evidence=evidence)
    except TypeError:
        draft = draft_fn(topic, kind, voice, length)

    records: list[IterationRecord] = []
    card = _score(draft, kind, voice, target_len)
    gate = gates.check(draft, gate_cfg)
    passed = gate.passed and card.overall_score >= threshold

    for i in range(max_iters):
        records.append(IterationRecord(
            iteration=i + 1, score=round(card.overall_score, 1),
            grade=card.overall_grade, gate_passed=gate.passed,
            violations=list(gate.violations),
        ))
        if passed or i == max_iters - 1:
            break
        draft = _revise(draft, voice, evidence, gate, card, kind, llm_fn)
        card = _score(draft, kind, voice, target_len)
        gate = gates.check(draft, gate_cfg)
        passed = gate.passed and card.overall_score >= threshold

    provenance = [{"kind": h.kind, "id": h.id, "confidence": h.confidence}
                  for h in (grounding.signals + grounding.facts)]

    return LoopResult(
        draft=draft, score=round(card.overall_score, 1), grade=card.overall_grade,
        passed=passed, gate_passed=gate.passed, violations=list(gate.violations),
        grounding_mode=grounding.mode, iterations=records, provenance=provenance,
    )
