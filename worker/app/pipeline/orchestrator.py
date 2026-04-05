"""8-phase pipeline orchestrator.

Runs JD → resume generation using the user's LLM (BYOK) + local Python tools.
Each phase updates Supabase with progress for the frontend to display.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from supabase import Client

from ..context import PipelineContext
from ..db import update_job
from ..llm import get_provider
from ..data.strategies import STRATEGIES
from ..tools.parse_template import resume_parse_template, ParseTemplateInput
from ..tools.measure_width import resume_measure_width, MeasureWidthInput
from ..tools.validate_contrast import resume_validate_contrast, ContrastInput
from ..tools.validate_page_fit import resume_validate_page_fit, PageFitInput, SectionSpec
from ..tools.suggest_synonyms import resume_suggest_synonyms, SynonymInput
from ..tools.track_verbs import resume_track_verbs, TrackVerbsInput
from ..tools.assemble_html import (
    resume_assemble_html, AssembleInput, ThemeColors, HeaderData, SectionContent,
)
from ..tools.score_bullets import resume_score_bullets, ScoreBulletsInput, CandidateBullet
from . import prompts


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
MAX_WIDTH_RETRIES = 3


async def run_pipeline(ctx: PipelineContext, sb: Client) -> None:
    """Execute all 8 phases sequentially."""
    llm = get_provider(ctx.model_provider, ctx.api_key, ctx.model_id)

    await phase_1_parse(ctx, sb, llm)
    await phase_2_strategy(ctx, sb, llm)
    await phase_3_page_fit(ctx, sb)
    await phase_4_bullets(ctx, sb, llm)
    await phase_5_width_opt(ctx, sb, llm)
    await phase_6_scoring(ctx, sb)
    await phase_7_validation(ctx, sb)
    await phase_8_assembly(ctx, sb, llm)


# ── Helpers ──────────────────────────────────────────────────────────────

async def _progress(ctx: PipelineContext, sb: Client, phase: int, msg: str, pct: int):
    ctx.current_phase = phase
    ctx.phase_message = msg
    await update_job(sb, ctx.job_id, current_phase=msg, phase_number=phase, progress_pct=pct)


def _parse_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code fences."""
    text = text.strip()
    if text.startswith("```"):
        # Remove ```json ... ``` wrapper
        lines = text.split("\n")
        start = 1 if lines[0].startswith("```") else 0
        end = -1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[start:end])
    return json.loads(text)


def _load_template(template_id: str) -> str:
    path = TEMPLATES_DIR / f"{template_id}.html"
    return path.read_text()


# ── Phase 1: JD + Career Profile Parsing ─────────────────────────────────

async def phase_1_parse(ctx: PipelineContext, sb: Client, llm):
    await _progress(ctx, sb, 1, "Analyzing job description", 5)

    # Load and parse template first
    template_html = _load_template(ctx.template_id)
    parse_result = json.loads(
        await resume_parse_template(ParseTemplateInput(template_html=template_html), ctx=ctx)
    )

    # Call LLM to analyze JD + career profile
    user_msg = prompts.PHASE_1_USER.format(jd_text=ctx.jd_text, career_text=ctx.career_text)
    resp = await llm.complete(prompts.PHASE_1_SYSTEM, user_msg)
    data = _parse_json(resp.text)

    ctx.career_level = data["career_level"]
    ctx.jd_keywords = data["jd_keywords"]
    ctx._parsed = data  # stash for later phases

    await _progress(ctx, sb, 1, "JD analysis complete", 12)


# ── Phase 2: Strategy + Brand Colors ─────────────────────────────────────

async def phase_2_strategy(ctx: PipelineContext, sb: Client, llm):
    await _progress(ctx, sb, 2, "Picking strategy & colors", 15)

    parsed = ctx._parsed
    user_msg = prompts.PHASE_2_USER.format(
        jd_keywords_json=json.dumps(ctx.jd_keywords, indent=2),
        career_summary=parsed.get("career_summary", ""),
        target_role=parsed.get("target_role", ""),
        company_name=parsed.get("company_name", ""),
    )
    system_msg = prompts.PHASE_2_SYSTEM.format(
        strategies_json=json.dumps(
            {k: {"description": v["description"], "trigger": v["trigger"]} for k, v in STRATEGIES.items()},
            indent=2,
        ),
        career_level=ctx.career_level,
        company_name=parsed.get("company_name", ""),
    )
    resp = await llm.complete(system_msg, user_msg)
    data = _parse_json(resp.text)

    ctx.strategy = data["strategy"]
    ctx.theme_colors = data["theme_colors"]
    ctx._section_order = data.get("section_order", [])
    ctx._bullet_budget = data.get("bullet_budget", {})

    await _progress(ctx, sb, 2, f"Strategy: {ctx.strategy}", 25)


# ── Phase 3: Page Fit Planning ────────────────────────────────────────────

async def phase_3_page_fit(ctx: PipelineContext, sb: Client):
    await _progress(ctx, sb, 3, "Planning page layout", 30)

    # LLM already gave us section_order + bullet_budget in Phase 2.
    # We build SectionSpec objects and validate with the tool.
    budget = ctx._bullet_budget
    section_order = ctx._section_order

    # Build section specs from the budget
    sections = [SectionSpec(section_type="header", entry_count=1)]

    for section_name in section_order:
        s_lower = section_name.lower()
        if "experience" in s_lower or "professional" in s_lower:
            # Experience section: derive from budget
            company_keys = sorted([k for k in budget if k.startswith("company_")], key=lambda x: x)
            entry_count = len(company_keys)
            project_counts = []
            for ck in company_keys:
                total = budget.get(ck, 4)
                # Split bullets into groups of 2-3
                if total <= 3:
                    project_counts.append(1)
                elif total <= 6:
                    project_counts.append(2)
                else:
                    project_counts.append(3)
            sections.append(SectionSpec(
                section_type="experience",
                entry_count=entry_count,
                project_count_per_entry=project_counts,
                bullets_per_project=max(budget.get("company_1_total", 4) // max(project_counts[0] if project_counts else 1, 1), 2),
                has_entry_subhead=True,
            ))
        elif "award" in s_lower or "recognition" in s_lower:
            sections.append(SectionSpec(
                section_type="awards",
                entry_count=1,
                bullets_per_project=budget.get("awards", 2),
                has_entry_subhead=False,
            ))
        elif "voluntary" in s_lower or "project" in s_lower:
            sections.append(SectionSpec(
                section_type="voluntary",
                entry_count=1,
                bullets_per_project=budget.get("voluntary", 2),
                has_entry_subhead=False,
            ))
        elif "education" in s_lower or "academic" in s_lower:
            sections.append(SectionSpec(
                section_type="education",
                entry_count=1,
                edge_to_edge_lines=1,
                has_entry_subhead=True,
            ))
        elif "skill" in s_lower or "competenc" in s_lower:
            sections.append(SectionSpec(
                section_type="skills",
                entry_count=1,
                edge_to_edge_lines=1,
                has_entry_subhead=False,
            ))
        elif "interest" in s_lower:
            sections.append(SectionSpec(
                section_type="interests",
                entry_count=1,
                edge_to_edge_lines=1,
                has_entry_subhead=False,
            ))

    fit_result = json.loads(
        await resume_validate_page_fit(
            PageFitInput(sections=sections, career_level=ctx.career_level),
            template_config=ctx.template_config,
        )
    )

    ctx._page_fit = fit_result
    ctx._section_specs = sections
    ctx.stats["fits_one_page"] = fit_result.get("fits_one_page", False)
    ctx.stats["remaining_mm"] = fit_result.get("remaining_mm", 0)

    await _progress(ctx, sb, 3, "Layout planned", 35)


# ── Phase 4: Bullet Writing + Verb Tracking ───────────────────────────────

async def phase_4_bullets(ctx: PipelineContext, sb: Client, llm):
    await _progress(ctx, sb, 4, "Writing bullets", 40)

    parsed = ctx._parsed
    strategy_info = STRATEGIES.get(ctx.strategy, STRATEGIES["HYBRID_BALANCED"])

    user_msg = prompts.PHASE_4_USER.format(
        jd_keywords_json=json.dumps(ctx.jd_keywords, indent=2),
        career_text=ctx.career_text,
        bullet_budget_json=json.dumps(ctx._bullet_budget, indent=2),
        sections_json=json.dumps([s.model_dump() for s in ctx._section_specs], indent=2),
    )
    system_msg = prompts.PHASE_4_SYSTEM.format(
        strategy=ctx.strategy,
        strategy_description=strategy_info["description"],
        career_level=ctx.career_level,
    )
    resp = await llm.complete(system_msg, user_msg, temperature=0.4)
    data = _parse_json(resp.text)

    ctx._raw_bullets = data.get("bullets", [])

    # Register all verbs
    verbs = [b["verb"] for b in ctx._raw_bullets if b.get("verb")]
    await resume_track_verbs(
        TrackVerbsInput(action="register", verbs=verbs),
        ctx=ctx,
    )

    await _progress(ctx, sb, 4, f"Wrote {len(ctx._raw_bullets)} bullets", 50)


# ── Phase 5: Width Optimization Loop ─────────────────────────────────────

async def phase_5_width_opt(ctx: PipelineContext, sb: Client, llm):
    await _progress(ctx, sb, 5, "Optimizing bullet widths", 55)

    optimized = []
    total = len(ctx._raw_bullets)

    for i, bullet in enumerate(ctx._raw_bullets):
        text_html = bullet["text_html"]

        for attempt in range(MAX_WIDTH_RETRIES):
            # Measure width
            measure_result = json.loads(
                await resume_measure_width(
                    MeasureWidthInput(text_html=text_html, line_type="bullet"),
                    template_config=ctx.template_config,
                )
            )

            status = measure_result.get("status", "PASS")
            fill_pct = measure_result.get("fill_percentage", 95)

            if status == "PASS" or (95 <= fill_pct <= 100):
                break  # Good enough

            # Get synonym suggestions
            suggestions = "[]"
            if status in ("TOO_SHORT", "OVERFLOW"):
                direction = "expand" if status == "TOO_SHORT" else "shrink"
                try:
                    syn_result = json.loads(
                        await resume_suggest_synonyms(SynonymInput(
                            text=text_html,
                            current_width=measure_result.get("weighted_total", 0),
                            target_width=measure_result.get("budget", 0),
                            direction=direction,
                        ))
                    )
                    suggestions = json.dumps(syn_result.get("suggestions", []))
                except Exception:
                    pass

            # Ask LLM to revise
            user_msg = prompts.PHASE_5_USER.format(
                text_html=text_html,
                weighted_total=measure_result.get("weighted_total", 0),
                budget=measure_result.get("budget", 0),
                fill_percentage=fill_pct,
                status=status,
                suggestions_json=suggestions,
            )
            system_msg = prompts.PHASE_5_SYSTEM.format(
                fill_percentage=fill_pct,
                status=status,
            )
            resp = await llm.complete(system_msg, user_msg, temperature=0.2)
            try:
                revised = _parse_json(resp.text)
                text_html = revised["revised_text_html"]
            except (json.JSONDecodeError, KeyError):
                break  # Can't parse revision — keep current

        bullet["text_html"] = text_html
        bullet["fill_percentage"] = fill_pct
        optimized.append(bullet)

        if (i + 1) % 3 == 0:
            pct = 55 + int((i + 1) / total * 15)
            await _progress(ctx, sb, 5, f"Optimized {i + 1}/{total} bullets", pct)

    ctx._optimized_bullets = optimized
    await _progress(ctx, sb, 5, "Width optimization complete", 70)


# ── Phase 6: BRS Scoring ──────────────────────────────────────────────────

async def phase_6_scoring(ctx: PipelineContext, sb: Client):
    await _progress(ctx, sb, 6, "Scoring bullets", 72)

    candidate_bullets = []
    for i, b in enumerate(ctx._optimized_bullets):
        candidate_bullets.append(CandidateBullet(
            project_id=f"bullet_{i}",
            raw_text=b["text_html"],
            group_id=f"company_{b.get('company_index', 0)}",
            group_theme=b.get("project_title", ""),
            position_in_group=b.get("project_group", 0),
        ))

    score_result = json.loads(
        await resume_score_bullets(ScoreBulletsInput(
            bullets=candidate_bullets,
            jd_keywords=ctx.jd_keywords,
            career_level=ctx.career_level,
            total_bullet_budget=len(ctx._optimized_bullets),
        ))
    )

    ctx.bullet_scores = score_result.get("scored_bullets", [])
    ctx.stats["avg_brs"] = (
        sum(b["brs"] for b in ctx.bullet_scores) / len(ctx.bullet_scores)
        if ctx.bullet_scores else 0
    )
    ctx.stats["tier_1_count"] = score_result.get("tier_1_count", 0)

    await _progress(ctx, sb, 6, f"Avg BRS: {ctx.stats['avg_brs']:.0%}", 78)


# ── Phase 7: Validation ──────────────────────────────────────────────────

async def phase_7_validation(ctx: PipelineContext, sb: Client):
    await _progress(ctx, sb, 7, "Validating colors & layout", 80)

    colors = ctx.theme_colors or {}
    warnings = []

    # Validate contrast for brand_primary on white
    if colors.get("brand_primary"):
        contrast_result = json.loads(
            await resume_validate_contrast(ContrastInput(
                foreground_hex=colors["brand_primary"],
                background_hex="#FFFFFF",
            ))
        )
        if not contrast_result.get("passes_aa_normal", True):
            warnings.append(f"Primary color {colors['brand_primary']} fails WCAG AA contrast")
            # Use the suggested fix if available
            if contrast_result.get("suggested_fix"):
                colors["brand_primary"] = contrast_result["suggested_fix"]

    # Re-validate page fit with final bullet counts
    fit_result = json.loads(
        await resume_validate_page_fit(
            PageFitInput(sections=ctx._section_specs, career_level=ctx.career_level),
            template_config=ctx.template_config,
        )
    )

    ctx.stats["final_fits_page"] = fit_result.get("fits_one_page", False)
    ctx.stats["validation_warnings"] = warnings
    ctx.theme_colors = colors

    await _progress(ctx, sb, 7, "Validation complete", 85)


# ── Phase 8: HTML Assembly ────────────────────────────────────────────────

async def phase_8_assembly(ctx: PipelineContext, sb: Client, llm):
    await _progress(ctx, sb, 8, "Assembling final HTML", 88)

    parsed = ctx._parsed
    template_html = _load_template(ctx.template_id)

    # Ask LLM to build section HTML from optimized bullets
    user_msg = prompts.PHASE_8_USER.format(
        final_bullets_json=json.dumps(ctx._optimized_bullets, indent=2),
        sections_json=json.dumps([s.model_dump() for s in ctx._section_specs], indent=2),
        contact_json=json.dumps(parsed.get("contact_info", {}), indent=2),
    )
    system_msg = prompts.PHASE_8_SYSTEM.format(
        template_css_reference="section, section-title, section-divider, entry, entry-header, entry-subhead, project-title, li-content, edge-to-edge-line",
    )
    resp = await llm.complete(system_msg, user_msg, temperature=0.1)
    data = _parse_json(resp.text)

    # Build tool inputs
    contact = parsed.get("contact_info", {})
    colors = ctx.theme_colors or {}

    theme = ThemeColors(
        brand_primary=colors.get("brand_primary", "#4285F4"),
        brand_secondary=colors.get("brand_secondary", "#EA4335"),
        brand_tertiary=colors.get("brand_tertiary", ""),
        brand_quaternary=colors.get("brand_quaternary", ""),
    )

    header = HeaderData(
        name=contact.get("name", ""),
        role=parsed.get("target_role", ""),
        contacts=[
            f"Phone: {contact.get('phone', '')}",
            f"Email: {contact.get('email', '')}",
            f"LinkedIn: {contact.get('linkedin', '')}",
            f"Portfolio: {contact.get('portfolio', '')}",
        ],
    )

    sections = []
    for s in data.get("sections", []):
        sections.append(SectionContent(
            section_html=s["section_html"],
            section_order=s["section_order"],
        ))

    assemble_result = json.loads(
        await resume_assemble_html(AssembleInput(
            template_html=template_html,
            theme_colors=theme,
            header=header,
            sections=sections,
            css_overrides=data.get("css_overrides", ""),
        ))
    )

    ctx.output_html = assemble_result.get("final_html", "")
    ctx.stats["assembly_warnings"] = assemble_result.get("warnings", [])

    await _progress(ctx, sb, 8, "Resume complete", 98)
