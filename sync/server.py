"""Resume Optimization MCP Server — FastMCP implementation.

Main entry point for the sync resume MCP server. Uses module-level state
that persists for the lifetime of the Python process, avoiding dependency
on request_context.lifespan_state which requires an active MCP session.

Tools:
- sync_parse_template: Extract CSS variables and compute line budgets
- sync_measure_width: Calculate weighted character-unit width of text
- sync_validate_contrast: Check WCAG 2.0 AA color contrast
- sync_validate_page_fit: Verify vertical page fit and space allocation
- sync_suggest_synonyms: Find synonym replacements for width optimization
- sync_track_verbs: Maintain action verb registry to prevent repetition
- sync_assemble_html: Final HTML assembly with brand colors and content
- sync_score_bullets: Score bullets against job description keywords (BRS)
"""

import json

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

# Import all tool implementations
from tools.parse_template import (
    resume_parse_template,
    ParseTemplateInput,
    ParseTemplateOutput,
)
from tools.measure_width import (
    resume_measure_width,
    MeasureWidthInput,
)
from tools.validate_contrast import (
    resume_validate_contrast,
    ContrastInput,
)
from tools.validate_page_fit import (
    resume_validate_page_fit,
    PageFitInput,
)
from tools.suggest_synonyms import (
    resume_suggest_synonyms,
    SynonymInput,
)
from tools.track_verbs import (
    resume_track_verbs,
    TrackVerbsInput,
    TrackVerbsState,
)
from tools.assemble_html import (
    resume_assemble_html,
    AssembleInput,
)
from tools.score_bullets import (
    resume_score_bullets,
    ScoreBulletsInput,
)


# ---------------------------------------------------------------------------
# MODULE-LEVEL STATE — persists for the lifetime of the process.
# No dependency on request_context or lifespan. Works with any transport
# (stdio, streamable HTTP) and with stateless tool bridges (api_tool).
# ---------------------------------------------------------------------------
SERVER_STATE: dict = {
    "template_config": None,      # Set by sync_parse_template
    "used_verbs": set(),          # Managed by sync_track_verbs
    "sections": [],               # Accumulated HTML sections
    "line_log": [],               # Audit log: every line measured
    "career_level": None,         # Set by LLM (fresher|entry|mid|senior|executive)
    "strategy": None,             # Set by LLM
    "bullet_scores": [],          # Populated by sync_score_bullets
    "jd_keywords": [],            # Populated by LLM during Phase F
    "theme_colors": None,         # All 11 CSS vars
}

# Verb tracker state wrapper
_verb_state = TrackVerbsState(used_verbs=set())


# Create FastMCP server instance — no lifespan needed
mcp = FastMCP("sync")


# ---------------------------------------------------------------------------
# TOOL REGISTRATIONS
# ---------------------------------------------------------------------------

@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
async def sync_parse_template(params: ParseTemplateInput) -> str:
    """Parse HTML template and extract CSS variables for line budget computation.

    Extracts CSS custom properties (--page-width, --page-margin, --font-size-body,
    etc.) from the template HTML and computes line budgets for all line types.
    Stores the resulting TemplateConfig in server state for use by subsequent tools.

    MUST be called once before any other tool.

    Args:
        params: ParseTemplateInput with template_html

    Returns:
        JSON string with ParseTemplateOutput containing template_id, status, and budgets_computed
    """
    result = await resume_parse_template(params, server_state=SERVER_STATE)
    return result


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def sync_measure_width(params: MeasureWidthInput) -> str:
    """Calculate weighted character-unit width of text against line budget.

    Measures the exact width of HTML text (accounting for bold segments,
    font weights, and letter-spacing) and compares against line budgets
    to determine fill status (PASS, TOO_SHORT, or OVERFLOW).

    Args:
        params: MeasureWidthInput with text_html and line_type

    Returns:
        JSON string with MeasureWidthOutput containing weighted_total, status, and fill_percentage
    """
    template_config = SERVER_STATE.get("template_config")
    result = await resume_measure_width(params, template_config=template_config)

    # Log the measurement
    try:
        output = json.loads(result)
        SERVER_STATE["line_log"].append({
            "text": output.get("rendered_text", ""),
            "line_type": params.line_type,
            "status": output.get("status", ""),
            "fill_percentage": output.get("fill_percentage", 0),
        })
    except (json.JSONDecodeError, KeyError):
        pass

    return result


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def sync_validate_contrast(params: ContrastInput) -> str:
    """Check WCAG 2.0 AA contrast ratio between two colors.

    Validates that foreground and background colors meet accessibility
    standards for normal text (4.5:1) and large text (3.0:1).
    Suggests accessible color fixes if contrast fails.

    Args:
        params: ContrastInput with foreground_hex and background_hex

    Returns:
        JSON string with ContrastOutput containing contrast_ratio, pass status, and recommendation
    """
    return await resume_validate_contrast(params)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def sync_validate_page_fit(params: PageFitInput) -> str:
    """Check if all planned sections fit vertically on one page.

    Computes total height of all sections using pre-computed element heights
    from template config. Returns fit status and recommended section allocations
    based on career level.

    Args:
        params: PageFitInput with sections list and optional career_level

    Returns:
        JSON string with PageFitOutput containing total_height_mm, fits_one_page, and recommendation
    """
    template_config = SERVER_STATE.get("template_config")
    return await resume_validate_page_fit(params, template_config=template_config)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def sync_suggest_synonyms(params: SynonymInput) -> str:
    """Find word substitutions that adjust text width closer to target.

    Scans text for words in the synonym bank and calculates width impact
    of each substitution. Returns suggestions sorted by proximity to target width.
    The LLM chooses which suggestion to apply (language quality decision).

    Args:
        params: SynonymInput with text, current_width, target_width, direction

    Returns:
        JSON string with SynonymOutput containing suggestions and gap_to_close
    """
    return await resume_suggest_synonyms(params)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    ),
)
async def sync_track_verbs(params: TrackVerbsInput) -> str:
    """Manage a global registry of action verbs used across the entire resume.

    Maintains state across all tool calls within a session to ensure zero
    verb repetition. Supports four actions: check, register, list, reset.

    Args:
        params: TrackVerbsInput with action and optional verbs list

    Returns:
        JSON string with TrackVerbsOutput containing results, conflicts, and totals
    """
    global _verb_state

    # Sync module-level verb state with SERVER_STATE
    _verb_state.used_verbs = SERVER_STATE["used_verbs"]

    result = await resume_track_verbs(params, state=_verb_state)

    # Write back to SERVER_STATE
    SERVER_STATE["used_verbs"] = _verb_state.used_verbs

    return result


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def sync_assemble_html(params: AssembleInput) -> str:
    """Assemble final HTML resume by injecting content and colors into template.

    Performs comprehensive HTML assembly: replaces CSS variables with theme colors,
    injects header data (name, role, contacts), inserts section content, adds logo
    if provided, and verifies print rules. Returns production-ready single-file HTML.

    CRITICAL: Only modifies content slots. Never modifies CSS class definitions,
    layout rules, flex properties, or page dimensions.

    Args:
        params: AssembleInput with template, colors, header, sections, optional logo

    Returns:
        JSON string with AssembleOutput containing final_html and warnings
    """
    result = await resume_assemble_html(params)

    # Store theme colors in state
    if hasattr(params, "theme_colors"):
        SERVER_STATE["theme_colors"] = params.theme_colors

    return result


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def sync_score_bullets(params: ScoreBulletsInput) -> str:
    """Score candidate bullets against job description keywords (BRS engine).

    Computes Bullet Relevance Score (BRS) for every candidate bullet using
    five weighted components: keyword overlap (35%), metric magnitude (25%),
    recency (20%), leadership indicators (10%), and uniqueness (10%).

    Returns tiered and sorted bullets for LLM to decide which to include.

    Args:
        params: ScoreBulletsInput with bullets, JD keywords, career_level, budget

    Returns:
        JSON string with ScoreBulletsOutput containing scored_bullets, tiers, and recommendations
    """
    result = await resume_score_bullets(params)

    # Store bullet scores in state
    try:
        output = json.loads(result)
        SERVER_STATE["bullet_scores"] = output.get("scored_bullets", [])
    except (json.JSONDecodeError, KeyError):
        pass

    return result


if __name__ == "__main__":
    mcp.run()
