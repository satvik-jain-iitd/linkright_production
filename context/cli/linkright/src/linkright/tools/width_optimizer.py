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


def _score(html: str, cfg: dict, ideal, ok):
    """Rank key for a bullet, higher is better. Content first, then in-band,
    then closeness to the ideal midpoint. Lets us pick a global best and never
    regress below the input."""
    m = _measure(html, cfg)
    fill = m.fill_percentage
    mid = (ideal[0] + ideal[1]) / 2.0
    passed = 1 if check_bullet(html).passed else 0
    in_ideal = 1 if ideal[0] <= fill <= ideal[1] else 0
    in_ok = 1 if ok[0] <= fill <= ok[1] else 0
    return (passed, in_ideal, in_ok, -abs(mid - fill)), fill, m


_CACHE: dict = {}


def optimize_bullet(
    html: str,
    template_config: dict,
    *,
    llm_fn: Optional[Callable[[str, object], list[str]]] = None,
    ideal: tuple[float, float] = (95.0, 100.0),
    ok: tuple[float, float] = (90.0, 100.0),
    relaxed: tuple[float, float] = (85.0, 105.0),
    max_iters: int = 4,
    use_cache: bool = True,
) -> OptResult:
    """Cached entry point. The same bullet and bands returns the prior result,
    skipping recompute and a repeat model call. Pass use_cache=False to force.
    """
    key = (html, ideal, ok, relaxed, max_iters)
    if use_cache and key in _CACHE:
        return _CACHE[key]
    result = _optimize_uncached(
        html, template_config, llm_fn=llm_fn, ideal=ideal, ok=ok,
        relaxed=relaxed, max_iters=max_iters,
    )
    if use_cache:
        _CACHE[key] = result
    return result


def _tune(start, template_config, *, metric_ref, target, ok, llm_fn, max_iters):
    """Move ``start`` toward the ``target`` band. Global-best, never-regress,
    metric-safe against ``metric_ref`` (the true original, not an intermediate).
    Returns (best_html, used_llm, candidates_tried).
    """
    cur = start
    best_key, _, _ = _score(start, template_config, target, ok)
    best_html = start
    tried = 0
    used_llm = False

    for _ in range(max_iters):
        key, fill, m = _score(cur, template_config, target, ok)
        if key[0] == 1 and key[1] == 1:   # content clean and inside target
            best_html, best_key = cur, key
            break

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

        pool = [cur] + [c for c in candidates if _metrics_preserved(metric_ref, c)]
        ranked = sorted(((_score(c, template_config, target, ok)[0], c) for c in pool),
                        key=lambda x: x[0], reverse=True)
        top_key, top_html = ranked[0]
        if top_key > best_key:
            best_key, best_html = top_key, top_html
        if top_html == cur:
            break
        cur = top_html

    return best_html, used_llm, tried


def _optimize_uncached(
    html: str,
    template_config: dict,
    *,
    llm_fn: Optional[Callable[[str, object], list[str]]] = None,
    ideal: tuple[float, float] = (95.0, 100.0),
    ok: tuple[float, float] = (90.0, 100.0),
    relaxed: tuple[float, float] = (85.0, 105.0),
    overshoot: tuple[float, float] = (100.0, 110.0),
    max_iters: int = 4,
) -> OptResult:
    """Tune one bullet into the width band, keeping content and metrics intact.

    Rules-first: a cheap rules-only pass runs before any model call. If rules
    alone land the bullet in the ok band (90-100) and clean, we stop, no network.
    Only when rules cannot reach the band do we spend the local model.

    When the model is needed, strategy follows the reliable-direction asymmetry:
    compression is deterministic, expansion is not. So a bullet below the band is
    first expanded to a loose overshoot band (100-110, an easy target), then
    deterministically compressed to the ideal 95-100. A bullet in or over the band
    takes a single compress-to-ideal pass. Never returns a bullet worse than input.
    """
    # Phase 0, rules only, no network. Most production bullets land here.
    rules_html, _, t0 = _tune(html, template_config, metric_ref=html,
                              target=ideal, ok=ok, llm_fn=None, max_iters=max_iters)
    rm = _measure(rules_html, template_config)
    if check_bullet(rules_html).passed and ok[0] <= rm.fill_percentage <= ok[1]:
        best_html, used_llm, tried = rules_html, False, t0
    elif llm_fn is not None:
        # Rules fell short, escalate to the model.
        start = _measure(html, template_config)
        if start.fill_percentage < ok[0]:
            over, _u1, t1 = _tune(html, template_config, metric_ref=html,
                                  target=overshoot, ok=overshoot,
                                  llm_fn=llm_fn, max_iters=max_iters)
            llm_html, _u2, t2 = _tune(over, template_config, metric_ref=html,
                                      target=ideal, ok=ok,
                                      llm_fn=llm_fn, max_iters=max_iters)
            tried = t0 + t1 + t2
        else:
            llm_html, _u3, t3 = _tune(html, template_config, metric_ref=html,
                                      target=ideal, ok=ok,
                                      llm_fn=llm_fn, max_iters=max_iters)
            tried = t0 + t3
        # Keep whichever is better, rules result or the model result.
        if _score(rules_html, template_config, ideal, ok)[0] >= _score(llm_html, template_config, ideal, ok)[0]:
            best_html, used_llm = rules_html, False
        else:
            best_html, used_llm = llm_html, True
    else:
        best_html, used_llm, tried = rules_html, False, t0

    # Never regress below the original.
    if _score(html, template_config, ideal, ok)[0] > _score(best_html, template_config, ideal, ok)[0]:
        best_html = html

    # Classify the global best, fully local fallback chain.
    m = _measure(best_html, template_config)
    fill = m.fill_percentage
    passed = check_bullet(best_html).passed
    path = "llm" if used_llm else "rules"
    if best_html == html:
        path = "as_is"
    if passed and ideal[0] <= fill <= ideal[1]:
        return OptResult(best_html, fill, "ideal", path, max_iters, tried)
    if passed and ok[0] <= fill <= ok[1]:
        return OptResult(best_html, fill, "pass", path, max_iters, tried)
    if passed and relaxed[0] <= fill <= relaxed[1]:
        return OptResult(best_html, fill, "relaxed", "relaxed", max_iters, tried)
    return OptResult(best_html, fill, "failed", "failed", max_iters, tried)
