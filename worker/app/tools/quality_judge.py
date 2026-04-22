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
    """Check 1 (weight 0.25): % of JD keywords present in bullet text."""
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
            weight=0.25,
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
        weight=0.25,
        passed=score >= 40,
        detail=f"{matched}/{len(kw_list)} JD keywords found ({score:.0f}%).",
        suggestion=suggestion,
    )


def _check_width_fill(ctx: PipelineContext) -> CheckResult:
    """Check 2 (weight 0.20): Average bullet fill%, penalising over/underflow.

    2026-04-22: target window tightened to [95, 100] for scoring (was [90, 100]).
    Below 95% still scores via the legacy distance-from-95 formula, so a
    90% bullet loses ~10 points not a binary fail.
    """
    bullets = ctx._optimized_bullets or []
    fills = [b.get("fill_percentage", 0) for b in bullets if b.get("fill_percentage")]

    if not fills:
        return CheckResult(
            name="width_fill",
            score=50.0,
            weight=0.20,
            passed=True,
            detail="No fill_percentage data available; score defaulted to 50.",
        )

    avg_fill = sum(fills) / len(fills)
    overflow_count = sum(1 for f in fills if f > 100)
    underflow_count = sum(1 for f in fills if f < 85)

    # Also honour explicit width_failures tracked in ctx.stats
    width_failures = ctx.stats.get("width_failures", [])
    extra_failures = len(width_failures) if isinstance(width_failures, list) else 0

    base = 100 if 95 <= avg_fill <= 100 else max(0.0, 100 - abs(avg_fill - 97.5) * 2)
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
        weight=0.20,
        passed=score >= 60,
        detail="; ".join(details) + ".",
        suggestion=suggestion,
    )


def _check_verb_dedup(ctx: PipelineContext) -> CheckResult:
    """Check 3 (weight 0.10): Unique verb ratio PER section (company).

    2026-04-22: tightened from global dedup to per-section. A resume is
    allowed to repeat "Led" across different companies (natural narrative)
    but repeating within a company reads as padding. Score = min unique
    ratio across all companies.
    """
    bullets = ctx._optimized_bullets or []
    if not bullets:
        return CheckResult(
            name="verb_dedup",
            score=100.0,
            weight=0.10,
            passed=True,
            detail="No bullets found; check skipped.",
        )

    # Group bullets by company_index
    from collections import defaultdict
    by_company: dict[int, list[str]] = defaultdict(list)
    for b in bullets:
        text = _strip_html(b.get("text_html", ""))
        words = text.split()
        if words:
            by_company[b.get("company_index", 0)].append(words[0].lower())

    per_section_ratios: list[float] = []
    dupes_per_section: dict[int, list[str]] = {}
    for idx, verbs in by_company.items():
        if not verbs:
            continue
        ratio = len(set(verbs)) / len(verbs)
        per_section_ratios.append(ratio)
        dupes = [v for v in set(verbs) if verbs.count(v) > 1]
        if dupes:
            dupes_per_section[idx] = sorted(dupes)

    # Worst-section rule: score = min unique ratio × 100
    score = (min(per_section_ratios) if per_section_ratios else 1.0) * 100
    suggestion = None
    if dupes_per_section:
        parts = [f"company {idx}: {', '.join(dupes)}" for idx, dupes in dupes_per_section.items()]
        suggestion = f"Replace duplicate verbs within a section — {'; '.join(parts)}"

    return CheckResult(
        name="verb_dedup",
        score=round(score, 1),
        weight=0.10,
        passed=score >= 70,
        detail=f"min per-section unique-verb ratio = {score:.0f}%",
        suggestion=suggestion,
    )


def _check_bold_metrics(ctx: PipelineContext) -> CheckResult:
    """Check 7 (weight 0.10): Every bullet that contains a metric has that metric bolded.

    Uses METRIC_PATTERNS from tools.bullet_format. A bullet with no metric is
    trivially passing (no-op). Score = % of bullets-with-metrics where the
    metric is wrapped in <b>.
    """
    from .bullet_format import METRIC_PATTERNS, has_bolded_metric

    bullets = ctx._optimized_bullets or []
    if not bullets:
        return CheckResult(
            name="bold_metrics",
            score=100.0,
            weight=0.10,
            passed=True,
            detail="No bullets found; check skipped.",
        )

    with_metrics = 0
    bolded = 0
    for b in bullets:
        html = b.get("text_html", "") or ""
        plain = _strip_html(html)
        has_metric = any(pat.search(plain) for pat in METRIC_PATTERNS)
        if has_metric:
            with_metrics += 1
            if has_bolded_metric(html):
                bolded += 1

    if with_metrics == 0:
        return CheckResult(
            name="bold_metrics",
            score=100.0,
            weight=0.10,
            passed=True,
            detail="No bullets contained metrics; check skipped.",
        )

    score = (bolded / with_metrics) * 100
    return CheckResult(
        name="bold_metrics",
        score=round(score, 1),
        weight=0.10,
        passed=score >= 90,
        detail=f"{bolded}/{with_metrics} bullets have bolded metrics ({score:.0f}%).",
        suggestion=None if score >= 90 else "Run apply_bold_highlight before Phase 5 measurement.",
    )


def _check_keyword_highlight(ctx: PipelineContext) -> CheckResult:
    """Check 8 (weight 0.05): Every experience bullet has at least one <b> tag.

    Ensures color-highlighted content exists (brand-primary colour is applied
    to every <b> inside .li-content per the template CSS). Flags bullets that
    lost formatting during LLM rewrite / synonym swap.
    """
    from .bullet_format import has_any_bold

    bullets = ctx._optimized_bullets or []
    if not bullets:
        return CheckResult(
            name="keyword_highlight",
            score=100.0,
            weight=0.05,
            passed=True,
            detail="No bullets found; check skipped.",
        )

    with_bold = sum(1 for b in bullets if has_any_bold(b.get("text_html", "") or ""))
    score = (with_bold / len(bullets)) * 100
    return CheckResult(
        name="keyword_highlight",
        score=round(score, 1),
        weight=0.05,
        passed=score >= 90,
        detail=f"{with_bold}/{len(bullets)} bullets have at least one <b> tag ({score:.0f}%).",
        suggestion=None if score >= 90 else "Re-run apply_bold_highlight on bullets missing <b>.",
    )


def _check_xyz_format(ctx: PipelineContext) -> CheckResult:
    """Check 9 (weight 0.05): XYZ format — X (impact) + Y (metric) + Z (context).

    2026-04-22: strengthened per user directive — every bullet MUST have all three:
      X: starts with impact verb (past tense)
      Y: contains at least one metric (number/%/$/K/M/B)
      Z: has 5+ additional words providing context (HOW + scale)

    Heuristic, not LLM — the definitive XYZ check happens via Phase 4a prompt's
    xyz object. This is a post-hoc sanity sweep.
    """
    from .bullet_format import METRIC_PATTERNS

    bullets = ctx._optimized_bullets or []
    if not bullets:
        return CheckResult(
            name="xyz_format",
            score=100.0,
            weight=0.05,
            passed=True,
            detail="No bullets found; check skipped.",
        )

    xyz_pass = 0
    missing_components: list[str] = []
    for b in bullets:
        plain = _strip_html(b.get("text_html", "") or "")
        words = plain.split()
        if not words:
            missing_components.append("empty")
            continue
        first = words[0].lower().rstrip(".,:")
        # X: verb-first (past tense ending or common verb)
        has_x = (
            first.endswith("ed") or first.endswith("ied")
            or first in {
                "led", "drove", "built", "grew", "won", "saved", "shipped", "scaled",
                "cut", "ran", "set", "rolled", "oversaw", "managed", "owned",
                "architected", "spearheaded", "launched", "reduced", "increased",
                "delivered", "generated", "secured", "uncovered",
            }
        )
        # Y: at least one concrete metric
        has_y = any(pat.search(plain) for pat in METRIC_PATTERNS)
        # Z: sufficient context words (bullet must be ≥ 8 words to have HOW/scale beyond X + Y)
        has_z = len(words) >= 8

        if has_x and has_y and has_z:
            xyz_pass += 1
        else:
            missing = []
            if not has_x: missing.append("X")
            if not has_y: missing.append("Y")
            if not has_z: missing.append("Z")
            missing_components.append("/".join(missing))

    score = (xyz_pass / len(bullets)) * 100
    miss_summary = {}
    for m in missing_components:
        miss_summary[m] = miss_summary.get(m, 0) + 1
    miss_text = ", ".join(f"{k}={v}" for k, v in miss_summary.items()) if miss_summary else "none"

    return CheckResult(
        name="xyz_format",
        score=round(score, 1),
        weight=0.05,
        passed=score >= 80,  # tighter than before — quality floor
        detail=f"{xyz_pass}/{len(bullets)} bullets pass full XYZ ({score:.0f}%). Missing: {miss_text}",
        suggestion=None if score >= 80 else "Some bullets missing X (impact verb), Y (metric), or Z (context) — strengthen Phase 4a prompt enforcement.",
    )


def _check_html_integrity(ctx: PipelineContext) -> CheckResult:
    """Check 10 (weight 0.05): <b> tag balance + no stray `<`.

    Catches bullets where LLM rewrite broke markup. Template rendering can
    fail silently on unclosed tags; this surfaces it before render.
    """
    from .bullet_format import html_integrity_ok

    bullets = ctx._optimized_bullets or []
    if not bullets:
        return CheckResult(
            name="html_integrity",
            score=100.0,
            weight=0.05,
            passed=True,
            detail="No bullets found; check skipped.",
        )

    ok_count = sum(1 for b in bullets if html_integrity_ok(b.get("text_html", "") or ""))
    score = (ok_count / len(bullets)) * 100
    broken = len(bullets) - ok_count
    return CheckResult(
        name="html_integrity",
        score=round(score, 1),
        weight=0.05,
        passed=broken == 0,
        detail=f"{ok_count}/{len(bullets)} bullets pass HTML integrity ({score:.0f}%).",
        suggestion=None if broken == 0 else f"{broken} bullets have unbalanced <b> or stray '<' — inspect Phase 5 output.",
    )


def _check_page_fit(ctx: PipelineContext) -> CheckResult:
    """Check 4 (weight 0.10): Whether all sections fit on one page."""
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
            weight=0.10,
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
        weight=0.10,
        passed=fits,
        detail="Page fits one page." if fits else "Content overflows page.",
        suggestion="Remove or shorten sections to avoid page overflow." if not fits else None,
    )


def _check_contrast(ctx: PipelineContext) -> CheckResult:
    """Check 5 (weight 0.05): WCAG AA contrast for brand_primary on white."""
    colors = ctx.theme_colors or {}
    brand_primary = colors.get("brand_primary")

    if not brand_primary:
        return CheckResult(
            name="contrast",
            score=100.0,
            weight=0.05,
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
            weight=0.05,
            passed=passes,
            detail=detail,
            suggestion=suggestion,
        )
    except ValueError as exc:
        return CheckResult(
            name="contrast",
            score=0.0,
            weight=0.05,
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
        _check_bold_metrics,
        _check_keyword_highlight,
        _check_xyz_format,
        _check_html_integrity,
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
                # Re-normalized 2026-04-22 to make room for 4 new checks.
                "_check_keyword_coverage": 0.25,
                "_check_width_fill": 0.20,
                "_check_verb_dedup": 0.10,
                "_check_page_fit": 0.10,
                "_check_contrast": 0.05,
                "_check_ats_compliance": 0.05,
                "_check_bold_metrics": 0.10,
                "_check_keyword_highlight": 0.05,
                "_check_xyz_format": 0.05,
                "_check_html_integrity": 0.05,
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
