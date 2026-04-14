"""Agent 2: Bullet Writer — Generates XYZ-format bullets with pixel-precise width fitting."""
from __future__ import annotations

import json
import logging
import os

from anthropic import Anthropic

logger = logging.getLogger(__name__)

from linkright.schemas.jd_analysis import JDAnalysis
from linkright.schemas.pipeline_state import WrittenBullet
from linkright.tools.measure_width import measure_width, MeasureWidthInput
from linkright.tools.suggest_synonyms import suggest_synonyms, SynonymInput
from linkright.tools.track_verbs import track_verbs, TrackVerbsInput, TrackVerbsState
from linkright.tools.score_bullets import ScoredBullet


SYSTEM_PROMPT = """You are a resume bullet point writer. You write in XYZ format:
"Accomplished [X] as measured by [Y] by doing [Z]"

Rules:
1. ALWAYS use XYZ format: action/result (X), quantified metric (Y), method/how (Z)
2. Start with a strong, unique action verb (no repeats across bullets)
3. Include specific numbers: percentages, dollar amounts, team sizes, counts
4. Keep bullets concise — they must fit a specific character width
5. Use <b> tags around key metrics and company/product names for bold
6. Do NOT use generic filler words — every word must earn its place
7. Write in past tense for previous roles, present tense for current role

Examples of XYZ format:
- "Reduced customer onboarding time by <b>40%</b> by redesigning the 3-step setup wizard, serving <b>50K+ monthly users</b>"
- "Drove <b>$2.3M annual savings</b> by leading migration of 50 microservices to AWS, coordinating across <b>4 engineering teams</b>"
- "Increased bid volume by <b>2x</b> by shipping AI-powered measurement tool processing <b>1000+ properties/month</b>"

Return ONLY the bullet text (with <b> tags), no explanations or markdown."""


REVISE_PROMPT = """The bullet you wrote is {status}. Current fill: {fill}% (target: 90-100%).
{suggestions}

Rewrite the bullet to be {direction}. Keep XYZ format and the same meaning.
Return ONLY the revised bullet text (with <b> tags)."""


def write_bullets(
    jd_analysis: JDAnalysis,
    scored_bullets: list[ScoredBullet],
    template_config: dict,
    max_bullets: int = 8,
) -> list[WrittenBullet]:
    """Generate XYZ-format bullets with width-check loop.

    For each scored bullet:
    1. Claude writes an XYZ bullet
    2. measure_width checks fill (target: 90-100%)
    3. If not PASS → suggest_synonyms → Claude revises → re-measure
    4. track_verbs registers the leading verb
    5. Max 3 revision attempts per bullet

    Args:
        jd_analysis: Parsed JD with keywords and strategy.
        scored_bullets: Ranked bullets from score_bullets tool.
        template_config: Template config dict with budgets.
        max_bullets: Maximum bullets to write.

    Returns:
        List of WrittenBullet objects, width-fitted.
    """
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    verb_state = TrackVerbsState()
    written = []

    # Take top N scored bullets
    to_write = scored_bullets[:max_bullets]

    # Get list of JD keywords for context
    kw_list = ", ".join(kw.keyword for kw in jd_analysis.keywords[:20])
    used_verbs = verb_state.list_all()

    for scored in to_write:
        # Build prompt with context
        avoid_verbs = ", ".join(used_verbs) if used_verbs else "none yet"
        user_msg = (
            f"Write a resume bullet in XYZ format for this achievement:\n\n"
            f"Raw: {scored.raw_text}\n\n"
            f"Target role: {jd_analysis.role_title} at {jd_analysis.company_name}\n"
            f"Strategy: {jd_analysis.strategy}\n"
            f"Key JD keywords to include if relevant: {kw_list}\n"
            f"Verbs already used (DO NOT reuse): {avoid_verbs}\n\n"
            f"Write ONE bullet. XYZ format. Include <b> tags around metrics."
        )

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )

        bullet_html = response.content[0].text.strip()
        # Clean up any quotes or markdown
        bullet_html = bullet_html.strip('"').strip("'").strip("`")
        if bullet_html.startswith("- "):
            bullet_html = bullet_html[2:]

        # Width-check loop (max 3 attempts)
        for attempt in range(3):
            width_result = measure_width(
                MeasureWidthInput(text_html=bullet_html, line_type="bullet"),
                template_config=template_config,
            )

            if width_result.status == "PASS":
                break

            # Get synonym suggestions
            direction = "expand" if width_result.status == "TOO_SHORT" else "trim"
            syn_result = suggest_synonyms(SynonymInput(
                text=width_result.rendered_text,
                current_width=width_result.weighted_total,
                target_width=width_result.target_95,
                direction=direction,
            ))

            # Build revision suggestions
            suggestions = ""
            if syn_result.suggestions:
                top_3 = syn_result.suggestions[:3]
                suggestions = "Synonym suggestions:\n" + "\n".join(
                    f"  - Replace '{s.original_word}' with '{s.replacement_word}' (delta: {s.width_delta:+.1f})"
                    for s in top_3
                )

            # Ask Claude to revise
            revise_msg = REVISE_PROMPT.format(
                status=width_result.status,
                fill=width_result.fill_percentage,
                suggestions=suggestions,
                direction="longer (add detail/context)" if direction == "expand" else "shorter (tighten language)",
            )

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": bullet_html},
                    {"role": "user", "content": revise_msg},
                ],
            )

            bullet_html = response.content[0].text.strip().strip('"').strip("'").strip("`")
            if bullet_html.startswith("- "):
                bullet_html = bullet_html[2:]

        # Final width measurement
        final_width = measure_width(
            MeasureWidthInput(text_html=bullet_html, line_type="bullet"),
            template_config=template_config,
        )

        # ── Width fallback: handle bullets that failed the 3-attempt loop ──
        if final_width.status != "PASS":
            fill = final_width.fill_percentage
            if 85 <= fill <= 105:
                # Relaxed range — accept with warning
                logger.warning(
                    "Bullet accepted at relaxed range (%.1f%% fill, target 90-100%%): %s",
                    fill, final_width.rendered_text[:80],
                )
                # Override status so downstream doesn't flag it
                # final_width.status remains as-is for transparency in reporting
            elif fill > 105:
                # Too long — hard truncate to fit target width
                logger.error(
                    "Bullet OVER 105%% fill (%.1f%%) — truncating to fit: %s",
                    fill, final_width.rendered_text[:80],
                )
                # Iteratively remove trailing words until within 105%
                words = bullet_html.split()
                while len(words) > 3:
                    words.pop(-1)
                    candidate = " ".join(words)
                    # Ensure we don't break mid-tag
                    if "<b>" in candidate and "</b>" not in candidate:
                        candidate += "</b>"
                    check = measure_width(
                        MeasureWidthInput(text_html=candidate, line_type="bullet"),
                        template_config=template_config,
                    )
                    if check.fill_percentage <= 100:
                        bullet_html = candidate
                        final_width = check
                        break
            else:
                # Too short (<85%) — log error, keep as-is (no good automated fix)
                logger.error(
                    "Bullet UNDER 85%% fill (%.1f%%) — no automated fix available: %s",
                    fill, final_width.rendered_text[:80],
                )

        # Extract and register the leading verb
        first_word = final_width.rendered_text.split()[0].lower() if final_width.rendered_text else "unknown"
        track_verbs(TrackVerbsInput(action="register", verbs=[first_word]), state=verb_state)
        used_verbs = verb_state.list_all()

        written.append(WrittenBullet(
            signal_id=scored.project_id,
            achievement_index=0,
            section_type="experience",
            html_text=bullet_html,
            plain_text=final_width.rendered_text,
            width_total=final_width.weighted_total,
            fill_percentage=final_width.fill_percentage,
            width_status=final_width.status,
            action_verb=first_word,
        ))

    return written
