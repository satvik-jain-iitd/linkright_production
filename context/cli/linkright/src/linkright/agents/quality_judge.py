"""Agent 3: Quality Judge — Programmatic validation of the final resume. No API calls."""
from __future__ import annotations

from linkright.schemas.jd_analysis import JDAnalysis
from linkright.schemas.pipeline_state import WrittenBullet, QualityReport
from linkright.tools.validate_page_fit import validate_page_fit, PageFitInput, SectionSpec
from linkright.tools.validate_contrast import validate_contrast, ContrastInput


def judge_quality(
    written_bullets: list[WrittenBullet],
    jd_analysis: JDAnalysis,
    brand_primary: str = "#0066cc",
    background: str = "#ffffff",
) -> QualityReport:
    """Run all programmatic validation checks and compute a grade.

    Checks:
    1. Keyword coverage: % of P0/P1 keywords found in bullet text
    2. Width fill: average and minimum fill % across all bullets
    3. Verb duplicates: any repeated action verbs
    4. Page fit: will the content fit on one A4 page
    5. Contrast: brand colors pass WCAG AA
    6. ATS issues: common ATS compliance problems

    Args:
        written_bullets: All written bullets from bullet writer.
        jd_analysis: Parsed JD analysis.
        brand_primary: Primary brand color hex.
        background: Background color hex.

    Returns:
        QualityReport with grade and issues.
    """
    suggestions = []
    ats_issues = []

    # 1. Keyword coverage
    all_bullet_text = " ".join(b.plain_text.lower() for b in written_bullets)
    p0_p1_keywords = [
        kw.keyword.lower()
        for kw in jd_analysis.keywords
        if kw.priority in ("P0", "P1")
    ]
    matched = [kw for kw in p0_p1_keywords if kw in all_bullet_text]
    keyword_coverage = (len(matched) / len(p0_p1_keywords) * 100) if p0_p1_keywords else 100.0

    missing_keywords = [kw for kw in p0_p1_keywords if kw not in all_bullet_text]
    if missing_keywords:
        suggestions.append(f"Missing P0/P1 keywords: {', '.join(missing_keywords[:5])}")

    # 2. Width fill stats
    fills = [b.fill_percentage for b in written_bullets]
    width_fill_avg = sum(fills) / len(fills) if fills else 0.0
    width_fill_min = min(fills) if fills else 0.0

    overflow_bullets = [b for b in written_bullets if b.width_status == "OVERFLOW"]
    short_bullets = [b for b in written_bullets if b.width_status == "TOO_SHORT"]
    if overflow_bullets:
        suggestions.append(f"{len(overflow_bullets)} bullets overflow their line budget")
    if short_bullets:
        suggestions.append(f"{len(short_bullets)} bullets are too short (< 90% fill)")

    # 3. Verb duplicates
    verbs = [b.action_verb for b in written_bullets]
    seen = set()
    duplicates = []
    for v in verbs:
        if v in seen:
            duplicates.append(v)
        seen.add(v)

    if duplicates:
        suggestions.append(f"Duplicate verbs: {', '.join(set(duplicates))}")

    # 4. Page fit (estimate based on bullet count)
    experience_entries = len(set(b.signal_id for b in written_bullets))
    bullets_per_entry = len(written_bullets) // max(experience_entries, 1)

    page_fit_result = validate_page_fit(
        PageFitInput(
            sections=[
                SectionSpec(section_type="header"),
                SectionSpec(section_type="summary", summary_lines=2),
                SectionSpec(
                    section_type="experience",
                    entry_count=experience_entries,
                    bullets_per_project=bullets_per_entry,
                    project_count_per_entry=[1] * experience_entries,
                ),
                SectionSpec(section_type="education", entry_count=1, edge_to_edge_lines=1),
                SectionSpec(section_type="skills", edge_to_edge_lines=2),
            ],
            career_level=jd_analysis.career_level,
        )
    )
    page_fits = page_fit_result.fits_one_page
    if not page_fits:
        suggestions.append(f"Content overflows page by {abs(page_fit_result.remaining_mm):.1f}mm")

    # 5. Contrast check
    contrast_result = validate_contrast(ContrastInput(
        foreground_hex=brand_primary,
        background_hex=background,
    ))
    contrast_passes = contrast_result.passes_wcag_aa_normal_text
    if not contrast_passes:
        suggestions.append(f"Brand color {brand_primary} fails WCAG AA. Suggestion: {contrast_result.recommendation}")

    # 6. ATS compliance checks
    for b in written_bullets:
        if "<table" in b.html_text.lower():
            ats_issues.append("Table HTML found in bullet — ATS may not parse")
        if "<img" in b.html_text.lower():
            ats_issues.append("Image tag found in bullet — ATS will skip")

    # Compute grade
    score = 0.0
    score += min(keyword_coverage, 100) * 0.30  # 30% weight
    score += min(width_fill_avg, 100) * 0.25  # 25% weight
    score += (100 if not duplicates else 50) * 0.15  # 15% weight
    score += (100 if page_fits else 0) * 0.15  # 15% weight
    score += (100 if contrast_passes else 50) * 0.10  # 10% weight
    score += (100 if not ats_issues else 50) * 0.05  # 5% weight

    if score >= 90:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 40:
        grade = "D"
    else:
        grade = "F"

    return QualityReport(
        overall_grade=grade,
        keyword_coverage=round(keyword_coverage, 1),
        width_fill_avg=round(width_fill_avg, 1),
        width_fill_min=round(width_fill_min, 1),
        verb_duplicates=list(set(duplicates)),
        page_fits=page_fits,
        contrast_passes=contrast_passes,
        ats_issues=ats_issues,
        suggestions=suggestions,
    )
