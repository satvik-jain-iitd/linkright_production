"""LinkRight Pipeline — Linear orchestrator: JD + Resume → optimized HTML."""
from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

from linkright.schemas.career_signals import CareerSignals
from linkright.schemas.jd_analysis import JDAnalysis
from linkright.schemas.pipeline_state import PipelineState, WrittenBullet

from linkright.agents.jd_parser import parse_jd
from linkright.agents.bullet_writer import write_bullets
from linkright.agents.quality_judge import judge_quality

from linkright.tools.parse_template import parse_template, ParseTemplateInput
from linkright.tools.score_bullets import (
    score_bullets,
    ScoreBulletsInput,
    CandidateBullet,
)
from linkright.tools.assemble_html import (
    assemble_html,
    AssembleInput,
    ThemeColors,
    HeaderData,
    SectionContent,
)


def _save_state(state_dir: Path, filename: str, data: dict):
    """Save pipeline state to JSON file (crash-safe, Rule 8)."""
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / filename
    path.write_text(json.dumps(data, indent=2, default=str))


def _load_template(template_path: str | None = None) -> tuple[str, dict]:
    """Load HTML template and parse it into config."""
    if template_path is None:
        # Use built-in template
        template_path = str(
            Path(__file__).parent / "templates" / "cv-a4-standard.html"
        )

    with open(template_path) as f:
        template_html = f.read()

    result, config = parse_template(ParseTemplateInput(template_html=template_html))
    return template_html, config


def _signals_to_candidate_bullets(signals: CareerSignals) -> list[CandidateBullet]:
    """Convert career signals into CandidateBullet format for scoring."""
    bullets = []
    for entry_idx, signal in enumerate(signals.signals):
        for ach in signal.achievements:
            bullets.append(CandidateBullet(
                project_id=signal.id,
                raw_text=ach.raw,
                interview_data={
                    "entry_index": entry_idx,
                    "tools": signal.context.tech_stack if signal.context else [],
                    "team_size": signal.context.team_size if signal.context else 0,
                    "context": f"{signal.role} at {signal.company}",
                },
            ))
    return bullets


def run_pipeline(
    resume_path: str,
    jd_path: str,
    output_path: str | None = None,
    template_path: str | None = None,
) -> str:
    """Run the full LinkRight pipeline.

    Steps:
    1. Load inputs (career_signals.yaml + JD text + HTML template)
    2. Parse JD → JDAnalysis
    3. Score existing bullets → ranked + tiered
    4. Write bullets → XYZ format, width-fitted
    5. Assemble HTML → final resume
    6. Quality check → grade + report
    7. Output → final HTML file

    Args:
        resume_path: Path to career_signals.yaml
        jd_path: Path to job description text file
        output_path: Path for output HTML (default: ./output/resume.html)
        template_path: Path to HTML template (default: built-in)

    Returns:
        Path to the generated HTML file.
    """
    state_dir = Path(".linkright") / "state"

    # ── Step 1: Load inputs ──
    print("Step 1/7: Loading inputs...")

    with open(resume_path) as f:
        raw_signals = yaml.safe_load(f)
    career_signals = CareerSignals(**raw_signals)

    with open(jd_path) as f:
        jd_text = f.read()

    template_html, template_config = _load_template(template_path)

    _save_state(state_dir, "1_inputs_loaded.json", {
        "resume_path": resume_path,
        "jd_path": jd_path,
        "signals_count": len(career_signals.signals),
        "achievements_count": sum(len(s.achievements) for s in career_signals.signals),
    })

    # ── Step 2: Parse JD ──
    print("Step 2/7: Parsing job description...")

    jd_analysis = parse_jd(jd_text)

    _save_state(state_dir, "2_jd_analysis.json", jd_analysis.model_dump())
    print(f"  → {jd_analysis.company_name} | {jd_analysis.role_title} | Strategy: {jd_analysis.strategy}")
    print(f"  → {len(jd_analysis.keywords)} keywords extracted")

    # ── Step 3: Score bullets ──
    print("Step 3/7: Scoring bullets against JD...")

    candidate_bullets = _signals_to_candidate_bullets(career_signals)
    jd_kw_dicts = [{"keyword": kw.keyword, "category": kw.category} for kw in jd_analysis.keywords]

    scored_result = score_bullets(ScoreBulletsInput(
        bullets=candidate_bullets,
        jd_keywords=jd_kw_dicts,
        career_level=jd_analysis.career_level,
        total_bullet_budget=8,
    ))

    _save_state(state_dir, "3_scored_bullets.json", scored_result.model_dump())
    print(f"  → Tier 1: {scored_result.tier_1_count} | Tier 2: {scored_result.tier_2_count} | Tier 3: {scored_result.tier_3_count}")

    # ── Step 4: Write bullets ──
    print("Step 4/7: Writing XYZ bullets with width fitting...")

    written_bullets = write_bullets(
        jd_analysis=jd_analysis,
        scored_bullets=scored_result.scored_bullets,
        template_config=template_config,
        max_bullets=8,
    )

    _save_state(state_dir, "4_written_bullets.json", [b.model_dump() for b in written_bullets])
    for b in written_bullets:
        status_icon = "✓" if b.width_status == "PASS" else "✗"
        print(f"  {status_icon} [{b.fill_percentage:.0f}%] {b.plain_text[:70]}...")

    # ── Step 5: Assemble HTML ──
    print("Step 5/7: Assembling HTML resume...")

    # Build sections for the assembler
    section_contents = _build_sections(career_signals, written_bullets, jd_analysis)

    contacts = []
    if career_signals.metadata.phone:
        contacts.append(f"Phone: {career_signals.metadata.phone}")
    if career_signals.metadata.email:
        contacts.append(f"Email: {career_signals.metadata.email}")
    if career_signals.metadata.linkedin_url:
        contacts.append(f"LinkedIn: {career_signals.metadata.linkedin_url}")

    assembled = assemble_html(AssembleInput(
        template_html=template_html,
        theme_colors=ThemeColors(
            brand_primary="#0066cc",
            brand_secondary="#004d99",
        ),
        header=HeaderData(
            name=career_signals.metadata.user,
            role=jd_analysis.role_title,
            contacts=contacts,
        ),
        sections=section_contents,
    ))

    _save_state(state_dir, "5_assembled.json", {"status": "success", "html_length": len(assembled.final_html)})

    # ── Step 6: Quality check ──
    print("Step 6/7: Running quality checks...")

    quality = judge_quality(
        written_bullets=written_bullets,
        jd_analysis=jd_analysis,
    )

    _save_state(state_dir, "6_quality_report.json", quality.model_dump())
    print(f"  → Grade: {quality.overall_grade}")
    print(f"  → Keyword coverage: {quality.keyword_coverage}%")
    print(f"  → Width fill avg: {quality.width_fill_avg}%")
    if quality.suggestions:
        for s in quality.suggestions:
            print(f"  ⚠ {s}")

    # ── Step 7: Output ──
    print("Step 7/7: Writing output...")

    if output_path is None:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_path = str(output_dir / "resume.html")

    Path(output_path).write_text(assembled.final_html)
    print(f"\n  ✓ Resume saved to: {output_path}")
    print(f"  ✓ Grade: {quality.overall_grade} | Keywords: {quality.keyword_coverage}% | Fill: {quality.width_fill_avg}%")

    return output_path


def _build_sections(
    career_signals: CareerSignals,
    written_bullets: list[WrittenBullet],
    jd_analysis: JDAnalysis,
) -> list[SectionContent]:
    """Build SectionContent objects for the HTML assembler."""
    sections = []
    order = 1

    # Summary section
    if career_signals.metadata.summary:
        sections.append(SectionContent(
            section_html=(
                '<div class="section"><div class="section-title">Professional Summary</div>'
                f'<p class="summary-line">{career_signals.metadata.summary}</p></div>'
            ),
            section_order=order,
        ))
        order += 1

    # Experience section — group bullets by signal, then by bullet group
    bullet_map = {}
    for b in written_bullets:
        bullet_map.setdefault(b.signal_id, []).append(b)

    exp_html_parts = ['<div class="section"><div class="section-title">Professional Experience</div>']
    for signal in career_signals.signals:
        if signal.id not in bullet_map:
            continue
        exp_html_parts.append(f'<div class="entry">')
        exp_html_parts.append(f'<div class="entry-header"><span>{signal.role}</span><span>{signal.tenure or ""}</span></div>')
        exp_html_parts.append(f'<div class="entry-subhead"><span>{signal.company}</span></div>')

        # Group bullets by group field
        groups = {}
        ungrouped = []
        for b in bullet_map[signal.id]:
            if b.group:
                groups.setdefault(b.group, []).append(b)
            else:
                ungrouped.append(b)

        if groups:
            for group_name, group_bullets in groups.items():
                exp_html_parts.append('<div class="bullet-group"><ul>')
                for b in group_bullets:
                    # Only justify when fill ≥98% — below that, word-spacing looks artificial
                    css_class = "li-content" if b.fill_percentage >= 98 else "li-content-natural"
                    exp_html_parts.append(f'<li><span class="{css_class}">{b.html_text}</span></li>')
                exp_html_parts.append('</ul></div>')
        if ungrouped:
            exp_html_parts.append('<div class="bullet-group"><ul>')
            for b in ungrouped:
                css_class = "li-content" if b.fill_percentage >= 98 else "li-content-natural"
                exp_html_parts.append(f'<li><span class="{css_class}">{b.html_text}</span></li>')
            exp_html_parts.append('</ul></div>')

        exp_html_parts.append("</div>")
    exp_html_parts.append("</div>")

    if bullet_map:
        sections.append(SectionContent(
            section_html="\n".join(exp_html_parts),
            section_order=order,
        ))
        order += 1

    # Skills section
    if career_signals.static and career_signals.static.skills:
        skills_text = ", ".join(career_signals.static.skills)
        sections.append(SectionContent(
            section_html=(
                '<div class="section"><div class="section-title">Core Competencies &amp; Skills</div>'
                f'<p class="edge-to-edge-line">{skills_text}</p></div>'
            ),
            section_order=order,
        ))
        order += 1

    # Voluntary Work
    if career_signals.static and career_signals.static.voluntary_work:
        vol_parts = ['<div class="section"><div class="section-title">Voluntary Work</div>']
        for vw in career_signals.static.voluntary_work:
            title = f"{vw.org}, {vw.role}" if vw.role else vw.org
            vol_parts.append(f'<div class="entry">')
            vol_parts.append(f'<div class="entry-header"><span>{title}</span><span>{vw.tenure or ""}</span></div>')
            vol_parts.append(f'<ul><li><span class="li-content-natural">{vw.description}</span></li></ul>')
            vol_parts.append('</div>')
        vol_parts.append('</div>')
        sections.append(SectionContent(
            section_html="\n".join(vol_parts),
            section_order=order,
        ))
        order += 1

    # Education section
    if career_signals.static and career_signals.static.education:
        edu = career_signals.static.education
        edu_title = f"{edu.degree}, {edu.field}" if edu.field else (edu.degree or "")
        sections.append(SectionContent(
            section_html=(
                '<div class="section"><div class="section-title">Education</div>'
                f'<div class="entry"><div class="entry-header"><span>{edu.institution}</span><span>{edu.year}</span></div>'
                f'<div class="entry-subhead"><span>{edu_title}</span></div></div></div>'
            ),
            section_order=order,
        ))
        order += 1

    # Scholastic Achievements
    if career_signals.static and career_signals.static.achievements:
        ach_parts = ['<div class="section"><div class="section-title">Scholastic Achievements</div>']
        achs = career_signals.static.achievements
        for i in range(0, len(achs), 2):
            ach_parts.append('<div class="bullet-group"><ul>')
            for a in achs[i:i+2]:
                ach_parts.append(f'<li><span class="li-content-natural">{a}</span></li>')
            ach_parts.append('</ul></div>')
        ach_parts.append('</div>')
        sections.append(SectionContent(
            section_html="\n".join(ach_parts),
            section_order=order,
        ))
        order += 1

    # Interests
    if career_signals.static and career_signals.static.interests:
        interests_text = ", ".join(career_signals.static.interests)
        sections.append(SectionContent(
            section_html=(
                '<div class="section"><div class="section-title">Interests</div>'
                f'<p class="edge-to-edge-line">{interests_text}</p></div>'
            ),
            section_order=order,
        ))
        order += 1

    return sections
