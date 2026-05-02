"""LinkRight Agent-Assisted Pipeline — Zero API calls. Reads pre-computed JSON inputs."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from linkright.schemas.career_signals import CareerSignals
from linkright.schemas.jd_analysis import JDAnalysis, JDKeyword
from linkright.schemas.pipeline_state import WrittenBullet

from linkright.tools.parse_template import parse_template, ParseTemplateInput
from linkright.tools.score_bullets import (
    score_bullets, ScoreBulletsInput, CandidateBullet,
)
from linkright.tools.measure_width import measure_width, MeasureWidthInput
from linkright.tools.track_verbs import track_verbs, TrackVerbsInput, TrackVerbsState
from linkright.tools.assemble_html import (
    assemble_html, AssembleInput, ThemeColors, HeaderData, SectionContent,
)
from linkright.agents.quality_judge import judge_quality


def _save_state(state_dir: Path, filename: str, data):
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / filename).write_text(json.dumps(data, indent=2, default=str))


def _build_sections(
    career_signals: CareerSignals,
    written_bullets: list[WrittenBullet],
    jd_analysis: JDAnalysis,
) -> list[SectionContent]:
    """Build SectionContent objects with bullet groups and extra sections."""
    sections = []
    order = 1

    # Summary
    if career_signals.metadata.summary:
        sections.append(SectionContent(
            section_html=(
                '<div class="section"><div class="section-title">Professional Summary</div>'
                f'<p class="summary-line">{career_signals.metadata.summary}</p></div>'
            ),
            section_order=order,
        ))
        order += 1

    # Experience with bullet groups
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
                    exp_html_parts.append(f'<li><span class="li-content">{b.html_text}</span></li>')
                exp_html_parts.append('</ul></div>')
        if ungrouped:
            exp_html_parts.append('<div class="bullet-group"><ul>')
            for b in ungrouped:
                exp_html_parts.append(f'<li><span class="li-content">{b.html_text}</span></li>')
            exp_html_parts.append('</ul></div>')

        exp_html_parts.append("</div>")
    exp_html_parts.append("</div>")

    if bullet_map:
        sections.append(SectionContent(
            section_html="\n".join(exp_html_parts),
            section_order=order,
        ))
        order += 1

    # Skills
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
            vol_parts.append(f'<ul><li><span class="li-content">{vw.description}</span></li></ul>')
            vol_parts.append('</div>')
        vol_parts.append('</div>')
        sections.append(SectionContent(
            section_html="\n".join(vol_parts),
            section_order=order,
        ))
        order += 1

    # Education
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
        # Group in pairs for bullet groups
        achs = career_signals.static.achievements
        for i in range(0, len(achs), 2):
            ach_parts.append('<div class="bullet-group"><ul>')
            for a in achs[i:i+2]:
                ach_parts.append(f'<li><span class="li-content">{a}</span></li>')
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


def run_assisted_pipeline(
    resume_path: str,
    jd_path: str,
    jd_analysis_path: str,
    bullets_path: str,
    output_path: str | None = None,
    template_path: str | None = None,
) -> dict:
    """Run pipeline in agent-assisted mode. Zero API calls.

    Args:
        resume_path: Path to career_signals.yaml
        jd_path: Path to JD text (for reference)
        jd_analysis_path: Path to JSON with pre-computed JDAnalysis
        bullets_path: Path to JSON with pre-written bullets
        output_path: Output HTML path
        template_path: Custom template path

    Returns:
        Dict with width_report and quality_report
    """
    state_dir = Path(".linkright") / "state"

    # ── Step 1: Load inputs ──
    print("Step 1/7: Loading inputs...")
    with open(resume_path) as f:
        career_signals = CareerSignals(**yaml.safe_load(f))

    if template_path is None:
        template_path = str(Path(__file__).parent / "templates" / "cv-a4-standard.html")
    with open(template_path) as f:
        template_html = f.read()
    _, template_config = parse_template(ParseTemplateInput(template_html=template_html))

    print(f"  -> {len(career_signals.signals)} signals, {sum(len(s.achievements) for s in career_signals.signals)} achievements")

    # ── Step 2: Load JD Analysis ──
    print("Step 2/7: Loading JD analysis...")
    with open(jd_analysis_path) as f:
        jd_data = json.load(f)
    # Convert keywords
    keywords = [JDKeyword(**kw) for kw in jd_data.get("keywords", [])]
    jd_analysis = JDAnalysis(
        company_name=jd_data["company_name"],
        role_title=jd_data["role_title"],
        career_level=jd_data.get("career_level", "mid"),
        strategy=jd_data.get("strategy", "BALANCED"),
        keywords=keywords,
        requirements_p0=jd_data.get("requirements_p0", []),
        requirements_p1=jd_data.get("requirements_p1", []),
        requirements_p2=jd_data.get("requirements_p2", []),
        summary=jd_data.get("summary"),
    )
    print(f"  -> {jd_analysis.company_name} | {jd_analysis.role_title} | {len(jd_analysis.keywords)} keywords")

    # ── Step 3: Score raw bullets ──
    print("Step 3/7: Scoring bullets against JD...")
    candidate_bullets = []
    for signal in career_signals.signals:
        for ach in signal.achievements:
            candidate_bullets.append(CandidateBullet(
                project_id=signal.id,
                raw_text=ach.raw,
                interview_data={
                    "tools": signal.context.tech_stack if signal.context else [],
                    "team_size": signal.context.team_size if signal.context else 0,
                    "context": f"{signal.role} at {signal.company}",
                },
            ))
    jd_kw_dicts = [{"keyword": kw.keyword, "category": kw.category} for kw in jd_analysis.keywords]
    scored = score_bullets(ScoreBulletsInput(
        bullets=candidate_bullets,
        jd_keywords=jd_kw_dicts,
        career_level=jd_analysis.career_level,
        total_bullet_budget=12,
    ))
    print(f"  -> Tier 1: {scored.tier_1_count} | Tier 2: {scored.tier_2_count} | Tier 3: {scored.tier_3_count}")

    # ── Step 4: Width-check bullets ──
    print("Step 4/7: Width-checking bullets...")
    with open(bullets_path) as f:
        bullet_inputs = json.load(f)

    verb_state = TrackVerbsState()
    written_bullets = []
    width_pass = []
    width_fail = []

    for idx, bi in enumerate(bullet_inputs):
        html = bi["html"]
        signal_id = bi["signal_id"]
        group = bi.get("group", "")

        result = measure_width(
            MeasureWidthInput(text_html=html, line_type="bullet"),
            template_config=template_config,
        )

        first_word = result.rendered_text.split()[0].lower() if result.rendered_text else "unknown"
        track_verbs(TrackVerbsInput(action="register", verbs=[first_word]), state=verb_state)

        icon = "PASS" if result.status == "PASS" else "FAIL"
        print(f"  [{icon} {result.fill_percentage:.0f}%] {result.rendered_text[:80]}...")

        entry = {
            "index": idx,
            "fill": round(result.fill_percentage, 1),
            "status": result.status,
            "text": result.rendered_text,
            "signal_id": signal_id,
        }
        if result.status == "PASS":
            width_pass.append(entry)
        else:
            deficit = result.target_95 - result.weighted_total
            entry["suggestion"] = f"{'add' if deficit > 0 else 'trim'} ~{abs(int(deficit * 2))} chars"
            width_fail.append(entry)

        written_bullets.append(WrittenBullet(
            signal_id=signal_id,
            group=group,
            html_text=html,
            plain_text=result.rendered_text,
            width_total=result.weighted_total,
            fill_percentage=result.fill_percentage,
            width_status=result.status,
            action_verb=first_word,
        ))

    width_report = {
        "all_pass": len(width_fail) == 0,
        "pass_count": len(width_pass),
        "fail_count": len(width_fail),
        "pass": width_pass,
        "fail": width_fail,
    }
    _save_state(state_dir, "width_report.json", width_report)

    if width_fail:
        print(f"\n  WARNING: {len(width_fail)} bullets failed width check. See .linkright/state/width_report.json")

    # ── Step 5: Assemble HTML ──
    print("Step 5/7: Assembling HTML...")
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
        theme_colors=ThemeColors(brand_primary="#0066cc", brand_secondary="#004d99"),
        header=HeaderData(
            name=career_signals.metadata.user,
            role=jd_analysis.role_title,
            contacts=contacts,
        ),
        sections=section_contents,
    ))

    # ── Step 6: Quality check ──
    print("Step 6/7: Quality check...")
    quality = judge_quality(written_bullets=written_bullets, jd_analysis=jd_analysis)
    _save_state(state_dir, "quality_report.json", quality.model_dump())

    print(f"  -> Grade: {quality.overall_grade} | Keywords: {quality.keyword_coverage}% | Fill: {quality.width_fill_avg}%")
    if quality.suggestions:
        for s in quality.suggestions:
            print(f"  ! {s}")

    # ── Step 7: Output ──
    print("Step 7/7: Writing output...")
    if output_path is None:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        output_path = str(output_dir / "resume.html")

    Path(output_path).write_text(assembled.final_html)
    print(f"\n  -> Resume: {output_path}")
    print(f"  -> Grade: {quality.overall_grade} | Width: {len(width_fail)} fails | Keywords: {quality.keyword_coverage}%")

    return {
        "output_path": output_path,
        "width_report": width_report,
        "quality": quality.model_dump(),
    }
