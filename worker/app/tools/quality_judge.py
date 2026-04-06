"""Tool: quality_judge — Pure-Python resume quality assessment.

Runs 6 weighted checks against PipelineContext to produce a QualityReport
with a letter grade (A/B/C/D/F).  No LLM calls — deterministic and fast.

Grade boundaries:
    A: score >= 90
    B: score >= 75
    C: score >= 60
    D: score >= 40
    F: score < 40

ATS hard gate: if ats_compliance check score == 0, grade is capped at "C".
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("worker")

from ..context import PipelineContext
from ..utils.color_utils import contrast_ratio


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    name: str
    score: float      # 0–100
    weight: float     # e.g. 0.30, 0.25 …
    passed: bool
    detail: str       # human-readable explanation
    suggestion: Optional[str] = None


@dataclass
class QualityReport:
    grade: str                    # A / B / C / D / F  or "N/A"
    score: float                  # weighted total 0–100
    checks: list[CheckResult] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    ats_blocked: bool = False     # True if ATS hard gate triggered


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _strip_html(html: str) -> str:
    """Remove HTML tags and return plain text."""
    return re.sub(r"<[^>]+>", " ", html).strip()


def _score_to_grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_keyword_coverage(ctx: PipelineContext) -> CheckResult:
    """Check 1 (weight 0.30): % of JD keywords present in bullet text."""
    bullets = ctx._optimized_bullets or []
    all_bullet_text = " ".join(b.get("text_html", "") for b in bullets)

    kw_list = [
        kw["keyword"] if isinstance(kw, dict) else kw
        for kw in (ctx.jd_keywords or [])
    ]

    if not kw_list:
        return CheckResult(
            name="keyword_coverage",
            score=100.0,
            weight=0.30,
            passed=True,
            detail="No JD keywords provided; check skipped.",
        )

    matched = sum(
        1 for kw in kw_list
        if re.search(r"\b" + re.escape(kw) + r"\b", all_bullet_text, re.IGNORECASE)
    )
    score = matched / len(kw_list) * 100

    missing = [
        kw for kw in kw_list
        if not re.search(r"\b" + re.escape(kw) + r"\b", all_bullet_text, re.IGNORECASE)
    ]
    suggestion = (
        f"Add missing keywords: {', '.join(missing[:5])}" if missing else None
    )

    return CheckResult(
        name="keyword_coverage",
        score=round(score, 1),
        weight=0.30,
        passed=score >= 40,
        detail=f"{matched}/{len(kw_list)} JD keywords found ({score:.0f}%).",
        suggestion=suggestion,
    )


def _check_width_fill(ctx: PipelineContext) -> CheckResult:
    """Check 2 (weight 0.25): Average bullet fill%, penalising over/underflow."""
    bullets = ctx._optimized_bullets or []
    fills = [b.get("fill_percentage", 0) for b in bullets if b.get("fill_percentage")]

    if not fills:
        return CheckResult(
            name="width_fill",
            score=50.0,
            weight=0.25,
            passed=True,
            detail="No fill_percentage data available; score defaulted to 50.",
        )

    avg_fill = sum(fills) / len(fills)
    overflow_count = sum(1 for f in fills if f > 100)
    underflow_count = sum(1 for f in fills if f < 85)

    # Also honour explicit width_failures tracked in ctx.stats
    width_failures = ctx.stats.get("width_failures", [])
    extra_failures = len(width_failures) if isinstance(width_failures, list) else 0

    base = 100 if 90 <= avg_fill <= 100 else max(0.0, 100 - abs(avg_fill - 95) * 2)
    score = max(0.0, base - (overflow_count + extra_failures) * 5 - underflow_count * 2)

    details = [f"avg fill {avg_fill:.1f}%"]
    if overflow_count:
        details.append(f"{overflow_count} overflow bullet(s)")
    if underflow_count:
        details.append(f"{underflow_count} short bullet(s) (<85%)")

    suggestion = None
    if overflow_count:
        suggestion = "Shorten overflowing bullets to stay within line width."
    elif underflow_count:
        suggestion = "Expand short bullets to at least 85% line fill."

    return CheckResult(
        name="width_fill",
        score=round(score, 1),
        weight=0.25,
        passed=score >= 60,
        detail="; ".join(details) + ".",
        suggestion=suggestion,
    )


def _check_verb_dedup(ctx: PipelineContext) -> CheckResult:
    """Check 3 (weight 0.15): Unique verb ratio across all bullets."""
    bullets = ctx._optimized_bullets or []

    verbs: list[str] = []
    for b in bullets:
        text = _strip_html(b.get("text_html", ""))
        words = text.split()
        if words:
            verbs.append(words[0].lower())

    if not verbs:
        return CheckResult(
            name="verb_dedup",
            score=100.0,
            weight=0.15,
            passed=True,
            detail="No bullets found; check skipped.",
        )

    unique_ratio = len(set(verbs)) / len(verbs)
    score = unique_ratio * 100

    dupes = [v for v in set(verbs) if verbs.count(v) > 1]
    suggestion = (
        f"Replace duplicate verbs: {', '.join(sorted(dupes))}" if dupes else None
    )

    return CheckResult(
        name="verb_dedup",
        score=round(score, 1),
        weight=0.15,
        passed=score >= 70,
        detail=f"{len(set(verbs))}/{len(verbs)} unique opening verbs ({score:.0f}%).",
        suggestion=suggestion,
    )


def _check_page_fit(ctx: PipelineContext) -> CheckResult:
    """Check 4 (weight 0.15): Whether all sections fit on one page."""
    # Primary source: ctx._page_fit (set by orchestrator after validate_page_fit)
    page_fit = ctx._page_fit
    if page_fit:
        fits = page_fit.get("fits_one_page", True)
        remaining = page_fit.get("remaining_mm", 0.0)
        rec = page_fit.get("recommendation", "fits")
        score = 100.0 if fits else 0.0
        detail = (
            f"Page fit: {rec}. Remaining: {remaining:.1f}mm."
            if fits
            else f"Page overflow: {abs(remaining):.1f}mm over limit."
        )
        suggestion = (
            "Remove or shorten sections to avoid page overflow." if not fits else None
        )
        return CheckResult(
            name="page_fit",
            score=score,
            weight=0.15,
            passed=fits,
            detail=detail,
            suggestion=suggestion,
        )

    # Fallback: check stats set by orchestrator
    fits = ctx.stats.get("final_fits_page", True)
    score = 100.0 if fits else 0.0
    return CheckResult(
        name="page_fit",
        score=score,
        weight=0.15,
        passed=fits,
        detail="Page fits one page." if fits else "Content overflows page.",
        suggestion="Remove or shorten sections to avoid page overflow." if not fits else None,
    )


def _check_contrast(ctx: PipelineContext) -> CheckResult:
    """Check 5 (weight 0.10): WCAG AA contrast for brand_primary on white."""
    colors = ctx.theme_colors or {}
    brand_primary = colors.get("brand_primary")

    if not brand_primary:
        return CheckResult(
            name="contrast",
            score=100.0,
            weight=0.10,
            passed=True,
            detail="No brand_primary color defined; check skipped.",
        )

    try:
        ratio = contrast_ratio(brand_primary, "#FFFFFF")
        passes = ratio >= 4.5
        score = 100.0 if passes else 0.0
        detail = (
            f"brand_primary {brand_primary} contrast ratio {ratio:.2f}:1 "
            f"({'passes' if passes else 'fails'} WCAG AA 4.5:1)."
        )
        suggestion = (
            f"Darken {brand_primary} to achieve at least 4.5:1 contrast on white."
            if not passes
            else None
        )
        return CheckResult(
            name="contrast",
            score=score,
            weight=0.10,
            passed=passes,
            detail=detail,
            suggestion=suggestion,
        )
    except ValueError as exc:
        return CheckResult(
            name="contrast",
            score=0.0,
            weight=0.10,
            passed=False,
            detail=f"Invalid color value: {exc}",
            suggestion="Ensure brand_primary is a valid #RRGGBB hex color.",
        )


def _check_ats_compliance(ctx: PipelineContext) -> CheckResult:
    """Check 6 (weight 0.05): No ATS-breaking HTML elements (tables, images)."""
    bullets = ctx._optimized_bullets or []
    bullet_html = " ".join(b.get("text_html", "") for b in bullets)

    # Use assembled HTML if available (set by assemble_html phase)
    full_html = (
        ctx._assembled_html  # type: ignore[attr-defined]
        if hasattr(ctx, "_assembled_html")
        else bullet_html
    )
    # Also check draft_html as fallback
    if not full_html and ctx.draft_html:
        full_html = ctx.draft_html

    has_table = bool(re.search(r"<table", full_html, re.IGNORECASE))
    has_img = bool(re.search(r"<img", full_html, re.IGNORECASE))
    ats_pass = not (has_table or has_img)
    score = 100.0 if ats_pass else 0.0

    issues: list[str] = []
    if has_table:
        issues.append("<table> elements detected")
    if has_img:
        issues.append("<img> elements detected")

    detail = (
        "No ATS-blocking elements found."
        if ats_pass
        else f"ATS issues: {'; '.join(issues)}."
    )
    suggestion = (
        "Replace tables with plain text/CSS layouts and remove images for ATS compatibility."
        if not ats_pass
        else None
    )

    return CheckResult(
        name="ats_compliance",
        score=score,
        weight=0.05,
        passed=ats_pass,
        detail=detail,
        suggestion=suggestion,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def judge_quality(ctx: PipelineContext) -> QualityReport:
    """Run all 6 quality checks and return a QualityReport.

    This function is synchronous — no LLM calls, pure Python.

    Args:
        ctx: PipelineContext populated at least through Phase 6.

    Returns:
        QualityReport with grade, weighted score, per-check results,
        aggregated suggestions, and ATS block flag.
    """
    CHECK_FUNCTIONS = [
        _check_keyword_coverage,
        _check_width_fill,
        _check_verb_dedup,
        _check_page_fit,
        _check_contrast,
        _check_ats_compliance,
    ]

    results: list[CheckResult] = []
    failed_checks = 0

    for fn in CHECK_FUNCTIONS:
        try:
            result = fn(ctx)
            results.append(result)
        except Exception as exc:
            logger.warning("quality_judge: %s check failed: %s", fn.__name__, exc)
            # Derive check name from function name (strip leading "_check_")
            name = fn.__name__.replace("_check_", "").replace("_", "_")
            # Map weight from expected order (fallback 0.0)
            weight_map = {
                "_check_keyword_coverage": 0.30,
                "_check_width_fill": 0.25,
                "_check_verb_dedup": 0.15,
                "_check_page_fit": 0.15,
                "_check_contrast": 0.10,
                "_check_ats_compliance": 0.05,
            }
            weight = weight_map.get(fn.__name__, 0.0)
            results.append(CheckResult(
                name=name,
                score=0.0,
                weight=weight,
                passed=False,
                detail=f"Check failed with error: {exc}",
            ))
            failed_checks += 1

    # All checks failed → N/A
    if failed_checks == len(CHECK_FUNCTIONS):
        return QualityReport(grade="N/A", score=0.0)

    # Weighted total score
    total_score = sum(r.score * r.weight for r in results)
    total_score = round(total_score, 1)

    # Derive grade
    grade = _score_to_grade(total_score)

    # ATS hard gate: cap grade at "C" if ATS compliance failed
    ats_blocked = False
    ats_result = next((r for r in results if r.name == "ats_compliance"), None)
    if ats_result and ats_result.score == 0.0:
        ats_blocked = True
        grade_order = ["F", "D", "C", "B", "A"]
        c_index = grade_order.index("C")
        current_index = grade_order.index(grade) if grade in grade_order else 0
        if current_index > c_index:
            grade = "C"

    # Collect non-None suggestions
    suggestions = [r.suggestion for r in results if r.suggestion]

    return QualityReport(
        grade=grade,
        score=total_score,
        checks=results,
        suggestions=suggestions,
        ats_blocked=ats_blocked,
    )
