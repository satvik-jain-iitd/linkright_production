"""1-page fitness loop — strategy selection + config mutation for pipeline re-routing.

The pipeline wraps steps 12-15 in an iterative loop. After each attempt, measures:
  - page_count (via pypdf)
  - per-bullet wrap (via width_poc's final_cu > LINE_WRAP_CU_LIMIT)

If page_count != 1 or any bullet wraps, picks a strategy from the escalating ladder
and mutates `parsed_p12` for the next iteration. Max 5 iterations per job.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader

from .width_config import STEP13_TARGET_CU_MAX


LINE_WRAP_CU_LIMIT: float = 108.0  # Iter-08: actual wrap point is ~108 CU (bullets 105-108
                                    # fit on one line in Roboto 10pt). Previous 105 caused
                                    # fit_loop L1 to over-tighten on borderline bullets.
MAX_FIT_ITERATIONS: int = 3        # Hard cap: 3 = success-path + 2 retries (cost guardrail)

# Drop priority: smallest visual loss first, most-useful content last.
# Section names MUST match the <div class="section-title">NAME<...> text in
# cv-a4-mid-career.html EXACTLY (case-sensitive, including "&amp;" encoding).
DROP_SECTION_ORDER: list[str] = [
    "Interests",
    "Certifications",
    "Projects",
    "Skills &amp; Competencies",
]


def _estimate_util_from_html(html_path: Path) -> float:
    """Estimate page utilization (%) from rendered HTML using same heuristic as
    scorecard_context. 2026-05-02: added because pypdf-based page-count check
    misses silent overflow behind .page { overflow: hidden } — heuristic catches
    overflow before the user sees a clipped PDF.

    Returns 0.0 on parse error (treat as no signal — don't trigger escalation
    on heuristic failure alone).
    """
    if not html_path or not html_path.exists():
        return 0.0
    try:
        import re
        h = html_path.read_text(encoding="utf-8", errors="ignore")
        plain = lambda s: re.sub(r"<[^>]+>", "", s)
        # 2026-05-02 corrected: CHARS_PER_LINE = 120 to match width target band
        # (108-120c). In-band bullets count as 1 line. See memory
        # `feedback_width_band_one_line_per_bullet` for rationale.
        CHARS_PER_LINE = 120
        ELEM = {
            "header_block": 21.34, "summary_line": 4.02, "section_title": 7.68,
            "section_spacing": 4.0, "entry_header": 4.44, "entry_subhead": 5.24,
            "entry_spacing": 2.5, "bullet_line": 4.52, "skills_line": 4.0,
        }
        total = ELEM["header_block"]
        m_sum = re.search(r'<div class="summary-line">(.*?)</div>', h, re.DOTALL)
        if m_sum:
            sc = len(plain(m_sum.group(1)))
            total += max(1, sc // CHARS_PER_LINE + (1 if sc % CHARS_PER_LINE else 0)) * ELEM["summary_line"]
        n_sec = len(re.findall(r'<div class="section-title">', h))
        total += n_sec * (ELEM["section_title"] + ELEM["section_spacing"])
        n_ent = len(re.findall(r'<div class="entry">', h))
        total += n_ent * (ELEM["entry_header"] + ELEM["entry_subhead"] + ELEM["entry_spacing"])
        nbl = 0
        for m in re.finditer(r"<li(?:\s[^>]*)?>(.*?)</li>", h, re.DOTALL):
            c = len(plain(m.group(1)))
            nbl += max(1, c // CHARS_PER_LINE + (1 if c % CHARS_PER_LINE else 0))
        total += nbl * ELEM["bullet_line"]
        sl = 0
        for m in re.finditer(r'<span class="text-line">([^<]+)</span>', h):
            c = len(m.group(1).strip())
            if c:
                sl += max(1, c // CHARS_PER_LINE + (1 if c % CHARS_PER_LINE else 0))
        total += sl * ELEM["skills_line"]
        return min(150.0, 100.0 * total / 271.6)  # cap at 150% (overflow signal)
    except Exception:
        return 0.0


def evaluate_fit(pdf_path: Path, width_poc_results: dict | None,
                 html_path: Path | None = None) -> dict:
    """Run fitness checks on the produced PDF + width telemetry + util heuristic.

    Args:
        pdf_path: path to step_15's PDF output
        width_poc_results: step_12b's width POC telemetry dict (or None if disabled)
        html_path: path to step_14's HTML (for util estimate). Optional but
                   strongly recommended — without it the silent-overflow check
                   doesn't fire.

    Returns:
        dict with keys: page_count, any_wrap, wrap_bullets, util_pct,
        util_overflow, success.

    2026-05-02: util_overflow flag added — triggers when heuristic says >100%
    even if pypdf reports 1 page. This catches silent clip behind
    `.page { overflow: hidden }` that the user surfaced manually.
    """
    try:
        reader = PdfReader(str(pdf_path))
        page_count = len(reader.pages)
    except Exception:
        page_count = -1  # error signal

    wrap_bullets: list[str] = []
    if width_poc_results:
        for entry in width_poc_results.get("per_bullet_log", []):
            if entry.get("final_cu", 0) > LINE_WRAP_CU_LIMIT:
                wrap_bullets.append(f"{entry.get('company','?')}:{entry.get('idx','?')}")

    util_pct = _estimate_util_from_html(html_path) if html_path else 0.0
    # 2026-05-02 update: target 90% util (band 85-92% IDEAL per scorer). Trigger
    # active trim when util > 92% — gives breathing space at bottom even if
    # PDF render says 1 page (avoids the cluttered "fits exactly to edge" look
    # the user surfaced in 1:54 AM screenshot).
    UTIL_OVERFLOW_THRESHOLD = 92.0
    util_overflow = util_pct > UTIL_OVERFLOW_THRESHOLD

    return {
        "page_count": page_count,
        "any_wrap": bool(wrap_bullets),
        "wrap_bullets": wrap_bullets,
        "util_pct": util_pct,
        "util_overflow": util_overflow,
        "success": page_count == 1 and not wrap_bullets and not util_overflow,
    }


def choose_strategy(
    fit_result: dict,
    parsed_p12: dict,
    condensed: dict,
    iter_n: int,
) -> str:
    """Pick the next fitness strategy based on current pipeline state.

    Returns a strategy string that `apply_strategy` knows how to mutate for.
    """
    dropped = set(parsed_p12.get("dropped_sections", []))
    page_count = fit_result.get("page_count", 0)
    any_wrap = fit_result.get("any_wrap", False)
    util_overflow = fit_result.get("util_overflow", False)
    skills_max_chars = int(parsed_p12.get("skills_max_chars") or 480)

    # 2026-05-02: L0 — Skills trim is the EASIEST space-saving lever. Fire it
    # FIRST when util > 92% but page still fits. Per memory
    # `feedback_skills_trim_before_width_fill`: trim Skills (drop generics,
    # keep JD-matched) before bullet width-fill or section drops.
    # Progressive: 480c (4 lines) → 360c (3 lines) → 240c (2 lines).
    if util_overflow and not any_wrap and page_count == 1 and skills_max_chars > 240:
        return "L0_trim_skills"

    # Path 1: only wrap problem, page + util fine -> tighten width
    if any_wrap and page_count == 1 and not util_overflow:
        return "L1_tighten_width"

    # Path 2: page overflow OR util overflow (silent clip behind overflow:hidden)
    # -> escalate. 2026-05-02: util_overflow added so silent clips also trigger
    # shrink strategies (was only triggering on pypdf page_count > 1).
    total_bullets = sum(len(v) for v in (condensed or {}).values())

    # L2: first iteration + plenty of bullets -> drop one
    if iter_n == 0 and total_bullets >= 8:
        return "L2_drop_one_bullet"

    # L3-L5: drop the next optional section in order
    for section in DROP_SECTION_ORDER:
        if section not in dropped:
            return f"L3_drop_section:{section}"

    # L6: all sections dropped, still overflow -> compound drop
    return "L6_drop_one_bullet_combined"


def apply_strategy(
    strategy: str,
    parsed_p12: dict,
    condensed: dict,
) -> tuple[dict, dict]:
    """Mutate parsed_p12 (and optionally condensed) in place per chosen strategy.

    Returns (parsed_p12, condensed) for chaining — but mutations are applied in place.
    """
    if strategy == "L1_tighten_width":
        # Lower target_max_cu by 2 CU — signals next width POC pass to trim harder
        override = parsed_p12.setdefault("width_override", {})
        current = override.get("target_max_cu", STEP13_TARGET_CU_MAX)
        # Floor at 95 CU — below that, bullets look too thin
        override["target_max_cu"] = max(95.0, current - 2.0)

    elif strategy == "L2_drop_one_bullet":
        bb = parsed_p12.setdefault("bullet_budget", {})
        # Find longest-output company and decrement its cap
        if condensed:
            companies_sorted = sorted(condensed.items(), key=lambda kv: -len(kv[1]))
            if companies_sorted:
                longest_co_name = companies_sorted[0][0]
                # Map company name back to company_i_total budget key
                for i, c in enumerate(parsed_p12.get("companies", [])):
                    if c.get("name") == longest_co_name:
                        key = f"company_{i+1}_total"
                        bb[key] = max(1, bb.get(key, 4) - 1)
                        break

    elif strategy.startswith("L3_drop_section:"):
        section = strategy.split(":", 1)[1]
        dropped = parsed_p12.setdefault("dropped_sections", [])
        if section not in dropped:
            dropped.append(section)

    elif strategy == "L6_drop_one_bullet_combined":
        # Apply L2 plus add next droppable section
        apply_strategy("L2_drop_one_bullet", parsed_p12, condensed)
        dropped = parsed_p12.setdefault("dropped_sections", [])
        for section in DROP_SECTION_ORDER:
            if section not in dropped:
                dropped.append(section)
                break

    return parsed_p12, condensed
