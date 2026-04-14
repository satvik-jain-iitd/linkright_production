"""Cover Letter Pipeline — AI-generated cover letters from career data + JD.

Single Gemini Flash call with quality gate. Reuses JD analysis from linked
resume_job if available. Adapts career-ops "I'm choosing you" tone —
confident, selective, concrete without arrogance.
"""

from __future__ import annotations

import json
import logging
import re
import time

from ..llm.gemini import GeminiProvider
from ..llm.rate_limiter import gemini_limiter
from ..tools.hybrid_retrieval import hybrid_retrieve, NuggetResult
from .. import config as worker_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Quality gate — reject generic AI slop
# ---------------------------------------------------------------------------

BANNED_PHRASES = [
    "passionate about",
    "proven track record",
    "leveraged",
    "dynamic environment",
    "fast-paced",
    "team player",
    "results-driven",
    "self-starter",
    "think outside the box",
    "synergy",
    "go-getter",
    "detail-oriented professional",
]


def _quality_check(text: str) -> tuple[bool, list[str]]:
    """Check cover letter for generic AI patterns.

    Returns (passed, list_of_issues).
    """
    issues = []
    text_lower = text.lower()

    for phrase in BANNED_PHRASES:
        if phrase in text_lower:
            issues.append(f"Contains generic phrase: '{phrase}'")

    # Must contain at least one real metric/number
    has_metrics = bool(re.search(r'\d+[%$KMx]|\d+\+?\s*(years?|months?|users?|clients?|team)', text))
    if not has_metrics:
        issues.append("No specific metrics or numbers found")

    # Length check: 200-400 words
    word_count = len(text.split())
    if word_count < 150:
        issues.append(f"Too short ({word_count} words, need 200+)")
    elif word_count > 500:
        issues.append(f"Too long ({word_count} words, max 400)")

    passed = len(issues) == 0
    return passed, issues


# ---------------------------------------------------------------------------
# Cover letter system prompt
# ---------------------------------------------------------------------------

COVER_LETTER_SYSTEM = """You are an expert career writer crafting a cover letter.

## Tone (from career-ops philosophy)
Write with an "I'm choosing you" voice — confident, selective, concrete without arrogance.
The candidate is evaluating the company as much as the company evaluates them.
Lead with proof, not claims. Reference specific metrics from the candidate's achievements.

## Rules
- 250-350 words
- NEVER use: "passionate about", "proven track record", "leveraged", "dynamic environment",
  "fast-paced", "team player", "results-driven", "self-starter"
- Use the candidate's ACTUAL metrics and achievements — don't invent or generalize
- Mirror the company's language from the JD
- Reference specific company initiatives, products, or values from the JD

## Structure
1. Opening hook: Reference a specific company initiative or JD requirement that connects to the candidate's experience
2. Body paragraph 1: Map 2-3 strongest career achievements directly to top JD requirements, with metrics
3. Body paragraph 2: Address a secondary requirement with a unique angle or transferable skill
4. Closing: Confident call to action — "I'd welcome the opportunity to discuss how my experience with [specific thing] aligns with [specific company goal]"

## Output
Return ONLY the cover letter body text (no subject line, no salutation, no sign-off).
Plain text with paragraph breaks. No HTML, no markdown formatting."""


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------

async def generate_cover_letter(
    user_id: str,
    company: str,
    role: str,
    jd_text: str,
    supabase_client,
    jd_analysis: dict | None = None,
    recipient_name: str | None = None,
) -> str:
    """Generate a cover letter body from career data + JD.

    Returns the cover letter body as plain text (paragraphs separated by newlines).
    Applies quality gate — retries with stronger instructions if generic.
    """
    started = time.time()

    # 1. Hybrid retrieve top 8 nuggets
    nuggets, _method = await hybrid_retrieve(
        sb=supabase_client,
        user_id=user_id,
        query=jd_text,
        limit=8,
    )
    logger.info(f"CoverLetter: retrieved {len(nuggets)} nuggets via {_method}")

    # 2. Format nuggets
    nugget_lines = []
    for i, n in enumerate(nuggets, 1):
        nugget_lines.append(
            f"{i}. [{n.importance}] {n.answer}"
            f"\n   Company: {n.company} | Role: {n.role}"
        )
    nuggets_text = "\n".join(nugget_lines) if nugget_lines else "(No career data available)"

    # 3. Build user prompt
    jd_context = ""
    if jd_analysis:
        jd_context = f"\n## JD Analysis (from resume generation)\n{json.dumps(jd_analysis, indent=2)[:2000]}\n"

    user_prompt = f"""Write a cover letter for the following role:

## Company: {company}
## Role: {role}
{f"## Addressed to: {recipient_name}" if recipient_name else ""}
{jd_context}
## Job Description
{jd_text[:4000]}

## Candidate's Relevant Career Achievements
{nuggets_text}

Write the cover letter body now. Remember: specific metrics, "I'm choosing you" tone, 250-350 words."""

    # 4. Gemini Flash call with rate limiting
    gemini = GeminiProvider(
        api_key=worker_config.GEMINI_API_KEY,
        model_id=worker_config.GEMINI_MODEL_ID,
    )

    async with gemini_limiter(user_id):
        response = await gemini.complete(
            system=COVER_LETTER_SYSTEM,
            user=user_prompt,
            temperature=0.4,  # slightly creative but consistent
        )

    body = response.text.strip()
    logger.info(
        f"CoverLetter: Gemini call done ({response.input_tokens} in, {response.output_tokens} out)"
    )

    # 5. Quality gate
    passed, issues = _quality_check(body)
    if not passed:
        logger.warning(f"CoverLetter: quality gate failed — {issues}. Retrying...")

        retry_prompt = (
            user_prompt
            + "\n\nCRITICAL REVISION NEEDED:\n"
            + "\n".join(f"- {issue}" for issue in issues)
            + "\n\nFix these issues. Use SPECIFIC metrics from the candidate's achievements. "
            "Replace any generic phrases with concrete, evidence-backed statements."
        )

        async with gemini_limiter(user_id):
            response = await gemini.complete(
                system=COVER_LETTER_SYSTEM,
                user=retry_prompt,
                temperature=0.3,
            )

        body = response.text.strip()
        passed2, issues2 = _quality_check(body)
        if not passed2:
            logger.warning(f"CoverLetter: quality gate still failed after retry — {issues2}. Shipping anyway.")

    elapsed = time.time() - started
    word_count = len(body.split())
    logger.info(f"CoverLetter: complete — {word_count} words, {elapsed:.1f}s total")

    return body


def format_cover_letter_html(
    body: str,
    company: str,
    role: str,
    candidate_name: str,
    recipient_name: str | None = None,
) -> str:
    """Wrap cover letter body in a simple, professional HTML template."""

    # Convert plain text paragraphs to HTML
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    body_html = "\n".join(f"    <p>{p}</p>" for p in paragraphs)

    recipient_line = f"Dear {recipient_name}," if recipient_name else "Dear Hiring Manager,"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Cover Letter — {candidate_name} for {role} at {company}</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Roboto', sans-serif; background: #F1F3F4; display: flex; justify-content: center; padding: 30px 0; }}
        .page {{
            width: 210mm; min-height: 297mm; background: #fff; padding: 20mm;
            box-shadow: 0 1px 3px rgba(60,64,67,0.3), 0 4px 8px 3px rgba(60,64,67,0.15);
        }}
        @media print {{
            body {{ background: none; padding: 0; }}
            .page {{ margin: 0; box-shadow: none; }}
            @page {{ size: A4; margin: 0; }}
        }}
        .header {{ margin-bottom: 8mm; }}
        .name {{ font-size: 16pt; font-weight: 700; color: #202124; }}
        .meta {{ font-size: 9pt; color: #5F6368; margin-top: 2mm; }}
        .salutation {{ font-size: 10pt; margin-bottom: 5mm; color: #202124; }}
        .body p {{ font-size: 10pt; line-height: 1.5; color: #202124; margin-bottom: 4mm; }}
        .sign-off {{ font-size: 10pt; color: #202124; margin-top: 6mm; }}
        .sign-off .name-sign {{ font-weight: 700; margin-top: 2mm; }}
    </style>
</head>
<body>
<div class="page">
    <div class="header">
        <div class="name">{candidate_name}</div>
        <div class="meta">Application for {role} at {company}</div>
    </div>
    <div class="salutation">{recipient_line}</div>
    <div class="body">
{body_html}
    </div>
    <div class="sign-off">
        <p>Sincerely,</p>
        <p class="name-sign">{candidate_name}</p>
    </div>
</div>
</body>
</html>"""
