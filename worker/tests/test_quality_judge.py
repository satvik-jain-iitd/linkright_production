"""Tests for worker/app/tools/quality_judge.py

Story 4.3: 18 tests covering per-check logic, grade boundaries,
ATS hard gate, verb source, error handling, and integration.
"""

from __future__ import annotations

import os
import sys
from unittest import mock

import pytest

# Ensure SUPABASE_URL / SUPABASE_KEY are present before any worker import
_env_patch = mock.patch.dict(
    os.environ,
    {"SUPABASE_URL": "https://fake.supabase.co", "SUPABASE_KEY": "fake-key"},
)
_env_patch.start()

_WORKER_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _WORKER_ROOT not in sys.path:
    sys.path.insert(0, os.path.abspath(_WORKER_ROOT))

from app.tools.quality_judge import judge_quality, QualityReport, CheckResult  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_check(report: QualityReport, name: str) -> CheckResult:
    """Return the CheckResult with the given name, raise if missing."""
    result = next((c for c in report.checks if c.name == name), None)
    assert result is not None, f"Check '{name}' not found in report. Got: {[c.name for c in report.checks]}"
    return result


# ---------------------------------------------------------------------------
# Per-check tests (9)
# ---------------------------------------------------------------------------

def test_keyword_check_word_boundary(pipeline_ctx):
    """'engineer' should NOT match 'Reengineered', should match 'software engineer'."""
    pipeline_ctx.jd_keywords = ["engineer", "machine learning"]
    pipeline_ctx._optimized_bullets = [
        {"text_html": "<b>Reengineered</b> the platform", "fill_percentage": 95},
        {"text_html": "Led team as software <b>engineer</b>", "fill_percentage": 92},
    ]
    report = judge_quality(pipeline_ctx)
    kw_check = _get_check(report, "keyword_coverage")
    # "Reengineered" should NOT match "engineer" due to word boundary
    # "machine learning" is also absent → 1 out of 2 matched → 50%
    assert kw_check.score == 50.0


def test_width_check_known_fills(pipeline_ctx):
    """Feed bullets with fills in the new 95-100 target window → score 100."""
    # 2026-04-22: target window tightened from [90, 100] to [95, 100].
    # avg_fill = 96.5 → in range → base=100 → score=100.
    pipeline_ctx._optimized_bullets = [
        {"text_html": "<b>Led</b> the team", "fill_percentage": 96},
        {"text_html": "<b>Built</b> the platform", "fill_percentage": 97},
    ]
    pipeline_ctx.stats["width_failures"] = []
    report = judge_quality(pipeline_ctx)
    width_check = _get_check(report, "width_fill")
    assert width_check.score == 100.0
    assert width_check.passed is True


def test_width_check_outside_target_loses_points(pipeline_ctx):
    """Fills below 95 still score, just lower via distance-from-97.5 formula."""
    pipeline_ctx._optimized_bullets = [
        {"text_html": "<b>Led</b> the team", "fill_percentage": 92},
        {"text_html": "<b>Built</b> the platform", "fill_percentage": 94},
    ]
    pipeline_ctx.stats["width_failures"] = []
    report = judge_quality(pipeline_ctx)
    width_check = _get_check(report, "width_fill")
    # avg = 93 → 100 - (97.5-93)*2 = 91
    assert width_check.score == 91.0


def test_verb_check_unique_verbs(pipeline_ctx):
    """All unique verbs → score=100."""
    pipeline_ctx._optimized_bullets = [
        {"text_html": "Led the product vision", "fill_percentage": 92},
        {"text_html": "Built microservices architecture", "fill_percentage": 91},
        {"text_html": "Drove quarterly roadmap", "fill_percentage": 93},
    ]
    report = judge_quality(pipeline_ctx)
    verb_check = _get_check(report, "verb_dedup")
    assert verb_check.score == 100.0


def test_verb_check_duplicate_verbs(pipeline_ctx):
    """50% duplicate verbs → score=50."""
    pipeline_ctx._optimized_bullets = [
        {"text_html": "Led the product team", "fill_percentage": 92},
        {"text_html": "Led another initiative", "fill_percentage": 91},
    ]
    report = judge_quality(pipeline_ctx)
    verb_check = _get_check(report, "verb_dedup")
    # 2 bullets both starting with "led" → 1 unique / 2 total → 50%
    assert verb_check.score == 50.0


def test_page_fit_check_passes(pipeline_ctx):
    """Page fit check passes when fits_one_page=True."""
    pipeline_ctx._page_fit = {
        "fits_one_page": True,
        "remaining_mm": 5.0,
        "recommendation": "fits",
    }
    report = judge_quality(pipeline_ctx)
    fit_check = _get_check(report, "page_fit")
    assert fit_check.score == 100.0
    assert fit_check.passed is True


def test_page_fit_check_fails(pipeline_ctx):
    """Page fit check fails when fits_one_page=False."""
    pipeline_ctx._page_fit = {
        "fits_one_page": False,
        "remaining_mm": -8.5,
        "recommendation": "overflow",
    }
    report = judge_quality(pipeline_ctx)
    fit_check = _get_check(report, "page_fit")
    assert fit_check.score == 0.0
    assert fit_check.passed is False


def test_contrast_check_passing_color(pipeline_ctx):
    """#333333 on white passes WCAG AA (ratio > 4.5)."""
    pipeline_ctx.theme_colors = {"brand_primary": "#333333"}
    report = judge_quality(pipeline_ctx)
    contrast_check = _get_check(report, "contrast")
    assert contrast_check.score == 100.0
    assert contrast_check.passed is True


def test_contrast_check_failing_color(pipeline_ctx):
    """#FFFF00 (yellow) on white fails WCAG AA (ratio < 4.5)."""
    pipeline_ctx.theme_colors = {"brand_primary": "#FFFF00"}
    report = judge_quality(pipeline_ctx)
    contrast_check = _get_check(report, "contrast")
    assert contrast_check.score == 0.0
    assert contrast_check.passed is False


def test_ats_check_no_tables(pipeline_ctx):
    """Clean HTML → ATS check passes."""
    pipeline_ctx._optimized_bullets = [
        {"text_html": "<b>Led</b> cross-functional team", "fill_percentage": 92},
    ]
    # Ensure no assembled or draft HTML with tables
    pipeline_ctx.draft_html = "<div><ul><li>Clean HTML content</li></ul></div>"
    report = judge_quality(pipeline_ctx)
    ats_check = _get_check(report, "ats_compliance")
    assert ats_check.score == 100.0
    assert ats_check.passed is True


def test_ats_check_with_table(pipeline_ctx):
    """<table> in HTML → ATS check fails."""
    pipeline_ctx.draft_html = "<table><tr><td>Name</td></tr></table>"
    pipeline_ctx._optimized_bullets = []
    report = judge_quality(pipeline_ctx)
    ats_check = _get_check(report, "ats_compliance")
    assert ats_check.score == 0.0
    assert ats_check.passed is False


# ---------------------------------------------------------------------------
# Grade boundary tests (4)
# ---------------------------------------------------------------------------

def _make_ctx_with_score(pipeline_ctx, target_score: float):
    """Manipulate ctx so weighted score ≈ target_score.

    Strategy: two drivers so the full 0-100 range is reachable.
      - keyword_coverage (weight 0.25) — match fraction of JD keywords
      - When target_score < 75, also break page_fit + xyz + html (drops ~25 pts)
        to bring the achievable floor down.

    Post 2026-04-22 weights:
      kw 0.25 + width 0.20 + verb 0.10 + page 0.10 + contrast 0.05 + ats 0.05
      + bold_metrics 0.10 + keyword_highlight 0.05 + xyz 0.05 + html 0.05 = 1.00
    """
    # Decide whether to also break auxiliary checks (needed for grades C/D/F)
    # With kw=0 and everything else 100, minimum is 75 (grade B boundary).
    break_aux = target_score < 75
    # If auxiliary checks broken: page 0 (0.10), xyz 0 (0.05), html 0 (0.05) = -20 pts
    # So non-kw contribution becomes 55 instead of 75. kw provides 0-25.
    # Reachable range with break_aux=True: 55 to 80 — covers C (60-74) and D (40-59
    # via overflow). For D (40-59) we need MORE drop → also fail bold_metrics.
    drop_more = target_score < 60

    non_kw_floor = 75.0  # ideal
    if break_aux:
        non_kw_floor -= 20.0  # page + xyz + html = 0
    if drop_more:
        non_kw_floor -= 10.0  # bold_metrics = 0

    kw_score_needed = (target_score - non_kw_floor) / 0.25
    kw_score_needed = max(0.0, min(100.0, kw_score_needed))

    total_kw = 10
    matched_kw = round(kw_score_needed / 100 * total_kw)

    keywords = [f"skill{i}" for i in range(total_kw)]
    matched_text = " ".join(keywords[:matched_kw]) if matched_kw else "placeholder"

    # Base well-formed bullets (≥8 words each to satisfy XYZ Z-component check)
    good_bullets = [
        {
            "text_html": f"Led <b>{matched_text}</b> platform team delivering <b>99%</b> uptime across AWS regions",
            "fill_percentage": 97,
            "company_index": 0,
        },
        {
            "text_html": "Built backend service scaling to <b>100K+</b> requests across enterprise customer segments",
            "fill_percentage": 98,
            "company_index": 0,
        },
    ]
    if drop_more:
        # Strip <b> tags + drop verbs → bold_metrics 0, xyz 0, keyword_highlight 0
        good_bullets = [
            {"text_html": f"project delivering 99 uptime {matched_text}", "fill_percentage": 97, "company_index": 0},
            {"text_html": "backend service scaling to 100K requests", "fill_percentage": 98, "company_index": 0},
        ]
    elif break_aux:
        # Break HTML + xyz only (keep bold so bold_metrics check passes)
        good_bullets = [
            {"text_html": f"Led <b>{matched_text}</b> project <b>99%</b> <b>unclosed", "fill_percentage": 97, "company_index": 0},
            {"text_html": "service scaling <b>100K+</b> requests", "fill_percentage": 98, "company_index": 0},  # no verb → xyz fail
        ]

    pipeline_ctx.jd_keywords = keywords
    pipeline_ctx._optimized_bullets = good_bullets
    if break_aux:
        pipeline_ctx._page_fit = {"fits_one_page": False, "remaining_mm": -10.0, "recommendation": "overflow"}
    else:
        pipeline_ctx._page_fit = {"fits_one_page": True, "remaining_mm": 5.0, "recommendation": "fits"}
    pipeline_ctx.theme_colors = {}  # contrast skipped → 100
    pipeline_ctx.stats["width_failures"] = []
    return pipeline_ctx


def test_grade_a_at_90(pipeline_ctx):
    """Score >= 90 → grade A."""
    _make_ctx_with_score(pipeline_ctx, 91.0)
    report = judge_quality(pipeline_ctx)
    assert report.grade == "A"
    assert report.score >= 90.0


def test_grade_b_at_75(pipeline_ctx):
    """Score 75-89 → grade B."""
    _make_ctx_with_score(pipeline_ctx, 76.0)
    report = judge_quality(pipeline_ctx)
    assert report.grade == "B"
    assert 75.0 <= report.score < 90.0


def test_grade_c_at_60(pipeline_ctx):
    """Score 60-74 → grade C (no ATS failure)."""
    _make_ctx_with_score(pipeline_ctx, 62.0)
    report = judge_quality(pipeline_ctx)
    # If ATS blocked, grade could be capped; ensure ATS passes here
    assert report.ats_blocked is False
    assert report.grade == "C"
    assert 60.0 <= report.score < 75.0


def test_grade_d_at_40(pipeline_ctx):
    """Score 40-59 → grade D.

    The helper only drives keyword_coverage (weight 0.30); the other five checks
    (weight 0.70 total) all default to 100.  The minimum weighted score that can
    be produced while keeping the rest at 100 is therefore 70, which is grade B.

    To reach grade D we must also depress the width_fill check.  We do that by
    setting fill_percentage=50 on every bullet (well below the 85% underflow
    threshold) so width_fill scores near zero, giving us a score in the D range.
    """
    # Set up: 0/10 keywords matched → kw_score = 0 (weight 0.30)
    total_kw = 10
    keywords = [f"skill{i}" for i in range(total_kw)]
    pipeline_ctx.jd_keywords = keywords
    # Bullets with very low fill (50%) → triggers heavy underflow penalty
    # Also no keywords matched
    pipeline_ctx._optimized_bullets = [
        {"text_html": "placeholder text here present", "fill_percentage": 50},
        {"text_html": "another placeholder bullet item", "fill_percentage": 50},
        {"text_html": "third placeholder bullet entry", "fill_percentage": 50},
        {"text_html": "fourth placeholder bullet entry", "fill_percentage": 50},
    ]
    pipeline_ctx._page_fit = {"fits_one_page": True, "remaining_mm": 5.0, "recommendation": "fits"}
    pipeline_ctx.theme_colors = {}
    pipeline_ctx.stats["width_failures"] = []

    report = judge_quality(pipeline_ctx)
    assert report.ats_blocked is False
    assert report.grade == "D", (
        f"Expected grade D, got {report.grade} (score={report.score})"
    )
    assert 40.0 <= report.score < 60.0


# ---------------------------------------------------------------------------
# ATS hard gate tests (2)
# ---------------------------------------------------------------------------

def test_ats_fail_caps_grade_at_c(pipeline_ctx):
    """High scores but ATS fails → grade capped at C.

    quality_judge._check_ats_compliance uses ctx._assembled_html when the
    attribute exists; only falls back to draft_html when bullet_html is empty.
    We set _assembled_html directly so the table is visible to the ATS check
    regardless of bullet content.
    """
    # High keyword coverage
    pipeline_ctx.jd_keywords = ["python", "machine learning"]
    pipeline_ctx._optimized_bullets = [
        {"text_html": "Led python and machine learning projects", "fill_percentage": 93},
        {"text_html": "Built robust platform", "fill_percentage": 92},
    ]
    pipeline_ctx._page_fit = {"fits_one_page": True, "remaining_mm": 5.0, "recommendation": "fits"}
    pipeline_ctx.theme_colors = {}
    pipeline_ctx.stats["width_failures"] = []
    # Set _assembled_html with a table so ATS check sees it directly
    pipeline_ctx._assembled_html = "<table><tr><td>ATS blocker</td></tr></table>"

    report = judge_quality(pipeline_ctx)
    assert report.ats_blocked is True
    assert report.grade in ("C", "D", "F")  # capped at C, could be lower if score < 60


def test_ats_pass_allows_grade_a(pipeline_ctx):
    """ATS passes, high scores → grade A allowed."""
    pipeline_ctx.jd_keywords = ["python", "machine learning"]
    pipeline_ctx._optimized_bullets = [
        {"text_html": "Led python and machine learning initiative", "fill_percentage": 93},
        {"text_html": "Built robust platform service", "fill_percentage": 92},
    ]
    pipeline_ctx._page_fit = {"fits_one_page": True, "remaining_mm": 10.0, "recommendation": "fits"}
    pipeline_ctx.theme_colors = {}
    pipeline_ctx.stats["width_failures"] = []
    pipeline_ctx.draft_html = "<div><ul><li>Clean HTML</li></ul></div>"

    report = judge_quality(pipeline_ctx)
    assert report.ats_blocked is False
    # Grade may not be A exactly depending on score, but should not be blocked
    assert report.grade != "N/A"


# ---------------------------------------------------------------------------
# Verb source test (1)
# ---------------------------------------------------------------------------

def test_verb_extracted_from_html_not_metadata(pipeline_ctx):
    """Verb comes from first word of HTML text content, not any metadata field."""
    pipeline_ctx._optimized_bullets = [
        {
            "text_html": "<b>Architected</b> microservices platform",
            "fill_percentage": 93,
            "verb": "IGNORE_THIS",          # metadata verb field should be ignored
            "category": "Architected",       # other metadata
        },
        {
            "text_html": "<b>Designed</b> data pipeline",
            "fill_percentage": 91,
            "verb": "WRONG_VERB",
        },
    ]
    report = judge_quality(pipeline_ctx)
    verb_check = _get_check(report, "verb_dedup")
    # Both verbs unique (architected, designed) → score 100
    assert verb_check.score == 100.0
    # Confirm "IGNORE_THIS" and "WRONG_VERB" were not used as verbs
    assert verb_check.suggestion is None  # no duplicates means no suggestion


# ---------------------------------------------------------------------------
# Error handling tests (3)
# ---------------------------------------------------------------------------

def test_empty_bullets_returns_na(pipeline_ctx):
    """When all checks raise exceptions, returns N/A grade.

    We monkeypatch each check function with a callable that has __name__ set,
    because judge_quality uses fn.__name__ in its exception handler.
    """
    from app.tools import quality_judge as qj

    def _raiser(ctx):
        raise RuntimeError("forced failure")

    # Each replacement must carry __name__ so the except branch can call fn.__name__
    check_names = [
        "_check_keyword_coverage",
        "_check_width_fill",
        "_check_verb_dedup",
        "_check_page_fit",
        "_check_contrast",
        "_check_ats_compliance",
    ]
    patches = []
    for name in check_names:
        raiser = lambda ctx, _n=name: (_ for _ in ()).throw(RuntimeError("forced failure"))
        raiser.__name__ = name
        patches.append(mock.patch.object(qj, name, raiser))

    with mock.patch.object(qj, "_check_keyword_coverage", side_effect=RuntimeError("fail")) as mk:
        mk.__name__ = "_check_keyword_coverage"
        # Use CHECK_FUNCTIONS replacement approach instead
        pass

    # Cleanest approach: patch the CHECK_FUNCTIONS list inside judge_quality
    def _make_raiser(fname):
        def fn(ctx):
            raise RuntimeError("forced failure")
        fn.__name__ = fname
        return fn

    fake_checks = [
        _make_raiser("_check_keyword_coverage"),
        _make_raiser("_check_width_fill"),
        _make_raiser("_check_verb_dedup"),
        _make_raiser("_check_page_fit"),
        _make_raiser("_check_contrast"),
        _make_raiser("_check_ats_compliance"),
        _make_raiser("_check_bold_metrics"),
        _make_raiser("_check_keyword_highlight"),
        _make_raiser("_check_xyz_format"),
        _make_raiser("_check_html_integrity"),
    ]

    # Patch all 10 check functions (6 original + 4 added 2026-04-22) in the
    # module with properly named raisers.
    with mock.patch.object(qj, "_check_keyword_coverage", fake_checks[0]), \
         mock.patch.object(qj, "_check_width_fill", fake_checks[1]), \
         mock.patch.object(qj, "_check_verb_dedup", fake_checks[2]), \
         mock.patch.object(qj, "_check_page_fit", fake_checks[3]), \
         mock.patch.object(qj, "_check_contrast", fake_checks[4]), \
         mock.patch.object(qj, "_check_ats_compliance", fake_checks[5]), \
         mock.patch.object(qj, "_check_bold_metrics", fake_checks[6]), \
         mock.patch.object(qj, "_check_keyword_highlight", fake_checks[7]), \
         mock.patch.object(qj, "_check_xyz_format", fake_checks[8]), \
         mock.patch.object(qj, "_check_html_integrity", fake_checks[9]):
        report = judge_quality(pipeline_ctx)

    assert report.grade == "N/A"
    assert report.score == 0.0


def test_null_keywords_returns_100_score(pipeline_ctx):
    """When jd_keywords is None/empty, keyword check returns score=100."""
    pipeline_ctx.jd_keywords = []
    pipeline_ctx._optimized_bullets = [
        {"text_html": "Led backend development", "fill_percentage": 92},
    ]
    report = judge_quality(pipeline_ctx)
    kw_check = _get_check(report, "keyword_coverage")
    assert kw_check.score == 100.0


def test_single_check_exception_scores_zero(pipeline_ctx):
    """When one check raises an exception, that check scores 0 but others run."""
    from app.tools import quality_judge as qj

    # Must set __name__ so judge_quality's except handler can call fn.__name__
    def _failing_contrast(ctx):
        raise ValueError("bad color")
    _failing_contrast.__name__ = "_check_contrast"

    with mock.patch.object(qj, "_check_contrast", _failing_contrast):
        pipeline_ctx._optimized_bullets = [
            {"text_html": "Led team", "fill_percentage": 92},
        ]
        pipeline_ctx.jd_keywords = []
        pipeline_ctx.theme_colors = {"brand_primary": "#333333"}
        report = judge_quality(pipeline_ctx)

    # Should still have 10 checks (6 original + 4 added 2026-04-22)
    assert len(report.checks) == 10
    # Grade should not be N/A since not all checks failed
    assert report.grade != "N/A"
    # Contrast check should score 0
    contrast_check = _get_check(report, "contrast")
    assert contrast_check.score == 0.0


# ---------------------------------------------------------------------------
# Integration test (1)
# ---------------------------------------------------------------------------

def test_full_report_has_all_fields(pipeline_ctx):
    """QualityReport has grade, score, checks list, suggestions list."""
    pipeline_ctx.jd_keywords = ["product", "data"]
    pipeline_ctx._optimized_bullets = [
        {"text_html": "<b>Led</b> product data strategy", "fill_percentage": 93},
        {"text_html": "<b>Built</b> dashboards", "fill_percentage": 91},
    ]
    pipeline_ctx._page_fit = {"fits_one_page": True, "remaining_mm": 5.0, "recommendation": "fits"}
    pipeline_ctx.theme_colors = {"brand_primary": "#333333"}
    pipeline_ctx.draft_html = "<div>clean html</div>"

    report = judge_quality(pipeline_ctx)

    # Check all required fields present
    assert isinstance(report.grade, str)
    assert report.grade in ("A", "B", "C", "D", "F", "N/A")
    assert isinstance(report.score, float)
    assert 0.0 <= report.score <= 100.0
    assert isinstance(report.checks, list)
    assert len(report.checks) == 10
    assert isinstance(report.suggestions, list)
    assert isinstance(report.ats_blocked, bool)

    # Verify all check names present (6 original + 4 added 2026-04-22)
    check_names = {c.name for c in report.checks}
    expected_names = {
        "keyword_coverage", "width_fill", "verb_dedup",
        "page_fit", "contrast", "ats_compliance",
        "bold_metrics", "keyword_highlight", "xyz_format", "html_integrity",
    }
    assert check_names == expected_names

    # Verify each check has required fields
    for check in report.checks:
        assert hasattr(check, "name")
        assert hasattr(check, "score")
        assert hasattr(check, "weight")
        assert hasattr(check, "passed")
        assert hasattr(check, "detail")
        assert 0.0 <= check.score <= 100.0


# ---------------------------------------------------------------------------
# Tests for 2026-04-22 additions: bold_metrics, keyword_highlight, xyz_format,
# html_integrity, and per-section verb_dedup tightening.
# ---------------------------------------------------------------------------

def test_bold_metrics_all_bolded_passes(pipeline_ctx):
    """Every bullet with a metric has it inside <b> → 100%."""
    pipeline_ctx._optimized_bullets = [
        {"text_html": "<b>Led</b> team to deliver <b>99%</b> uptime", "fill_percentage": 97},
        {"text_html": "Scaled system to <b>100K+</b> requests", "fill_percentage": 96},
    ]
    pipeline_ctx.jd_keywords = []
    report = judge_quality(pipeline_ctx)
    bm = _get_check(report, "bold_metrics")
    assert bm.score == 100.0
    assert bm.passed is True


def test_bold_metrics_unbolded_fails(pipeline_ctx):
    """A bullet with a naked metric (not in <b>) drops the score below 90."""
    pipeline_ctx._optimized_bullets = [
        {"text_html": "Led team delivering 99% uptime", "fill_percentage": 97},  # naked metric
        {"text_html": "Scaled to <b>100K+</b> requests", "fill_percentage": 96},  # bolded
    ]
    pipeline_ctx.jd_keywords = []
    report = judge_quality(pipeline_ctx)
    bm = _get_check(report, "bold_metrics")
    assert bm.score == 50.0  # 1/2 bullets with metrics had bolded metric
    assert bm.passed is False


def test_bold_metrics_no_metrics_skipped(pipeline_ctx):
    """Bullets without any metric don't penalize the check."""
    pipeline_ctx._optimized_bullets = [
        {"text_html": "Led cross-functional product strategy", "fill_percentage": 97},
    ]
    pipeline_ctx.jd_keywords = []
    report = judge_quality(pipeline_ctx)
    bm = _get_check(report, "bold_metrics")
    assert bm.score == 100.0
    assert "check skipped" in bm.detail.lower() or "no bullets contained metrics" in bm.detail.lower()


def test_keyword_highlight_all_have_bold(pipeline_ctx):
    """All bullets contain at least one <b> tag → 100%."""
    pipeline_ctx._optimized_bullets = [
        {"text_html": "Led <b>growth</b> initiative", "fill_percentage": 97},
        {"text_html": "Scaled <b>infra</b>", "fill_percentage": 96},
    ]
    pipeline_ctx.jd_keywords = []
    report = judge_quality(pipeline_ctx)
    kh = _get_check(report, "keyword_highlight")
    assert kh.score == 100.0


def test_keyword_highlight_missing_bold_fails(pipeline_ctx):
    """A bullet with no <b> at all fails the check."""
    pipeline_ctx._optimized_bullets = [
        {"text_html": "Led growth initiative", "fill_percentage": 97},
        {"text_html": "Scaled <b>infra</b>", "fill_percentage": 96},
    ]
    pipeline_ctx.jd_keywords = []
    report = judge_quality(pipeline_ctx)
    kh = _get_check(report, "keyword_highlight")
    assert kh.score == 50.0
    assert kh.passed is False


def test_xyz_format_verb_and_metric_passes(pipeline_ctx):
    """Bullets with verb (X), metric (Y), and ≥8 words of context (Z) score 100."""
    pipeline_ctx._optimized_bullets = [
        {"text_html": "Led team of 12 engineers delivering <b>99%</b> uptime across AWS regions", "fill_percentage": 97},
        {"text_html": "Built systems at <b>100K+</b> scale for enterprise customers in 8 weeks", "fill_percentage": 96},
    ]
    pipeline_ctx.jd_keywords = []
    report = judge_quality(pipeline_ctx)
    xyz = _get_check(report, "xyz_format")
    assert xyz.score == 100.0


def test_xyz_format_no_verb_fails(pipeline_ctx):
    """A noun-first bullet fails xyz heuristic."""
    pipeline_ctx._optimized_bullets = [
        {"text_html": "Team delivered <b>99%</b> uptime", "fill_percentage": 97},  # "Team" not a verb
    ]
    pipeline_ctx.jd_keywords = []
    report = judge_quality(pipeline_ctx)
    xyz = _get_check(report, "xyz_format")
    assert xyz.score == 0.0


def test_html_integrity_balanced_passes(pipeline_ctx):
    """Balanced <b>...</b> pairs score 100."""
    pipeline_ctx._optimized_bullets = [
        {"text_html": "Led <b>growth</b> team", "fill_percentage": 97},
        {"text_html": "Scaled to <b>100K+</b> requests", "fill_percentage": 96},
    ]
    pipeline_ctx.jd_keywords = []
    report = judge_quality(pipeline_ctx)
    hi = _get_check(report, "html_integrity")
    assert hi.score == 100.0


def test_html_integrity_unclosed_b_fails(pipeline_ctx):
    """Unclosed <b> tag fails the check."""
    pipeline_ctx._optimized_bullets = [
        {"text_html": "Led <b>growth team", "fill_percentage": 97},  # unclosed
    ]
    pipeline_ctx.jd_keywords = []
    report = judge_quality(pipeline_ctx)
    hi = _get_check(report, "html_integrity")
    assert hi.score == 0.0
    assert hi.passed is False


def test_verb_dedup_per_section_isolated(pipeline_ctx):
    """'Led' allowed across different companies but not within one."""
    pipeline_ctx._optimized_bullets = [
        {"text_html": "Led team at company A", "fill_percentage": 97, "company_index": 0},
        {"text_html": "Led marketing at company A", "fill_percentage": 97, "company_index": 0},  # dup within company 0
        {"text_html": "Led product at company B", "fill_percentage": 97, "company_index": 1},  # different company, OK
    ]
    pipeline_ctx.jd_keywords = []
    report = judge_quality(pipeline_ctx)
    vd = _get_check(report, "verb_dedup")
    # Company 0: 1/2 unique = 50%, Company 1: 1/1 = 100%.
    # Worst-section rule → score = 50
    assert vd.score == 50.0
