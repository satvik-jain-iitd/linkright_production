"""Hybrid bullet width optimizer, generate-then-verify.

Width measurement is exact math, so the model never judges width. Candidates are
generated (rule swaps first, an optional local LLM second) and then the
deterministic measurer plus the content gate plus a metric-integrity check pick
the winner. The constraint is always enforced by code, the LLM only widens the
language coverage that rules miss.

Order, for latency: rules first, only fall to the LLM when rules cannot reach the
band. Final fallback is rules plus accept-relaxed, fully local, no cloud.

``llm_fn`` is injectable: ``llm_fn(html, measure_result) -> list[str]`` returns
candidate rewrites. None means rules-only (W2). The real local-model generator is
wired in W3.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

from linkright.tools.measure_width import measure_width, MeasureWidthInput
from linkright.tools.suggest_synonyms import suggest_synonyms, SynonymInput
from linkright.tools.bullet_quality import check_bullet


@dataclass
class OptResult:
    html: str
    fill: float            # final fill percentage
    status: str            # "ideal" 95-100 | "pass" 90-100 | "relaxed" 85-105 | "failed"
    path: str              # "as_is" | "rules" | "llm" | "relaxed" | "failed"
    iterations: int
    candidates_tried: int


_NUM = re.compile(r"\d+(?:\.\d+)?")


def _strip(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html or "")


def _numbers(s: str) -> set[str]:
    return set(_NUM.findall(_strip(s)))


def _metrics_preserved(original: str, candidate: str) -> bool:
    """Candidate may not introduce or change a number, only keep or drop one.

    This is the deterministic guard against a weak model inventing a metric.
    """
    return _numbers(candidate) <= _numbers(original)


def _measure(html: str, cfg: dict):
    return measure_width(MeasureWidthInput(text_html=html, line_type="bullet"),
                         template_config=cfg)


def _rule_candidates(html: str, m, cfg: dict) -> list[str]:
    if m.status == "OVERFLOW":
        direction = "trim"
    elif m.status == "TOO_SHORT":
        direction = "expand"
    else:
        return []
    syn = suggest_synonyms(SynonymInput(
        text=m.rendered_text,
        current_width=m.weighted_total,
        target_width=m.target_95,
        direction=direction,
    ))
    cands: list[str] = []
    for s in syn.suggestions[:6]:
        c = re.sub(r"\b" + re.escape(s.original_word) + r"\b",
                   s.replacement_word, html, count=1)
        if c != html and c not in cands:
            cands.append(c)
    return cands


def optimize_bullet(
    html: str,
    template_config: dict,
    *,
    llm_fn: Optional[Callable[[str, object], list[str]]] = None,
    ideal: tuple[float, float] = (95.0, 100.0),
    ok: tuple[float, float] = (90.0, 100.0),
    relaxed: tuple[float, float] = (85.0, 105.0),
    max_iters: int = 4,
) -> OptResult:
    """Tune one bullet into the width band, keeping content and metrics intact."""
    mid = (ideal[0] + ideal[1]) / 2.0
    cur = html
    tried = 0
    used_llm = False

    for it in range(max_iters):
        m = _measure(cur, template_config)
        if ideal[0] <= m.fill_percentage <= ideal[1] and check_bullet(cur).passed:
            return OptResult(cur, m.fill_percentage, "ideal",
                             "as_is" if it == 0 else ("llm" if used_llm else "rules"),
                             it, tried)

        candidates = _rule_candidates(cur, m, template_config)
        if llm_fn is not None:
            try:
                llm_cands = llm_fn(cur, m) or []
            except Exception:
                llm_cands = []
            if llm_cands:
                used_llm = True
            candidates += [c for c in llm_cands if c and c != cur]
        tried += len(candidates)

        best = None
        for c in candidates:
            if not check_bullet(c).passed:
                continue
            if not _metrics_preserved(html, c):
                continue
            mc = _measure(c, template_config)
            dist = abs(mid - mc.fill_percentage)
            if best is None or dist < best[0]:
                best = (dist, c)
        if best is None:
            break
        cur = best[1]

    # Final classification, fully local fallback chain.
    m = _measure(cur, template_config)
    fill = m.fill_percentage
    passed = check_bullet(cur).passed
    path = "llm" if used_llm else "rules"
    if passed and ideal[0] <= fill <= ideal[1]:
        return OptResult(cur, fill, "ideal", path, max_iters, tried)
    if passed and ok[0] <= fill <= ok[1]:
        return OptResult(cur, fill, "pass", path, max_iters, tried)
    if passed and relaxed[0] <= fill <= relaxed[1]:
        return OptResult(cur, fill, "relaxed", "relaxed", max_iters, tried)
    return OptResult(cur, fill, "failed", "failed", max_iters, tried)
