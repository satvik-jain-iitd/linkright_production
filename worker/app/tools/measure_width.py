"""Tool 2: measure_width - Core text width measurement engine.

Calculates weighted character-unit width of text, accounting for bold segments,
font weights, and letter-spacing. Compares against line budgets and returns fill status.
"""

import json
import re
from pydantic import BaseModel, Field, ConfigDict

from ..data.roboto_weights import ROBOTO_REGULAR_WEIGHTS, ROBOTO_BOLD_WEIGHTS, REGULAR_DEFAULT, BOLD_DEFAULT
from ..utils.html_parser import parse_bold_segments, resolve_entities


class MeasureWidthInput(BaseModel):
    """Input for resume_measure_width tool."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "text_html": "Senior <b>Software Engineer</b>",
        "line_type": "entry_header"
    }})

    text_html: str = Field(
        ...,
        description=(
            "The text to measure. May contain <b>, <strong>, or <b style='...;'> tags "
            "for bold segments, and HTML entities like &ndash;, &mdash;, &amp;. "
            "Only visible rendered text is measured — all HTML tags are stripped."
        )
    )
    line_type: str = Field(
        ...,
        description=(
            "Which line type budget to compare against. "
            "One of: bullet, edge_to_edge, entry_header, entry_subhead, "
            "project_title, section_title, name, role, summary_line, contact_item"
        )
    )


class MeasureWidthOutput(BaseModel):
    """Output from resume_measure_width tool."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "weighted_total": 42.5,
        "raw_budget": 94.0,
        "fill_percentage": 45.2,
        "status": "PASS"
    }})

    weighted_total: float = Field(
        ...,
        description="Total width in character-units (after letter-spacing correction)"
    )
    target_95: float = Field(
        ...,
        description="Target fill target (95% of raw_budget) in character-units"
    )
    raw_budget: float = Field(
        ...,
        description="Maximum budget for this line_type in character-units"
    )
    fill_percentage: float = Field(
        ...,
        description="(weighted_total / raw_budget) * 100, percentage fill"
    )
    status: str = Field(
        ...,
        description="'PASS' (90-100% fill) | 'TOO_SHORT' (<90%) | 'OVERFLOW' (>100%)"
    )
    rendered_text: str = Field(
        ...,
        description="Visible text after HTML tag removal and entity resolution"
    )
    rendered_char_count: int = Field(
        ...,
        description="Total characters in rendered text"
    )
    bold_char_count: int = Field(
        ...,
        description="Characters inside <b> or <strong> tags"
    )
    surplus_or_deficit: float = Field(
        ...,
        description="positive = over target_95, negative = under target_95, in character-units"
    )


async def resume_measure_width(
    params: MeasureWidthInput,
    template_config: dict = None
) -> str:
    """Calculate the exact weighted width of a text string in character-units.

    ALGORITHM:
    1. Parse HTML to separate text into segments: [{text, is_bold}, ...]
       - <b>, <b style="...">, <strong> tags -> is_bold=True
       - Everything outside those tags -> is_bold=False
       - HTML tags themselves are NOT measured (only rendered text)
    2. Resolve HTML entities to rendered characters:
       - &ndash; -> - (U+2013), &amp; -> &, &mdash; -> -- (U+2014)
       - Numeric entities: &#8211; -> -, &#x2013; -> -
    3. For each character in the resolved text:
       - If is_bold: weight = ROBOTO_BOLD_WEIGHTS.get(char, BOLD_DEFAULT)
       - Else: weight = ROBOTO_REGULAR_WEIGHTS.get(char, REGULAR_DEFAULT)
    4. Sum all weights into weighted_total
    5. Apply letter-spacing correction:
       - actual_width_px = (weighted_total * digit_width_px) + (rendered_char_count - 1) * letter_spacing_px
       - adjusted_weighted_total = actual_width_px / digit_width_px
    6. Compare adjusted_weighted_total to budget for the given line_type:
       - fill < 90%: status = "TOO_SHORT"
       - 90% <= fill <= 100%: status = "PASS"
       - fill > 100%: status = "OVERFLOW"
    7. Compute surplus_or_deficit as adjusted_weighted_total - target_95

    Args:
        params: MeasureWidthInput with text_html and line_type
        template_config: Template configuration dict (should be injected from ctx.template_config)

    Returns:
        JSON string with MeasureWidthOutput
    """
    if template_config is None:
        # Fallback: use empty dict which will cause KeyError below
        template_config = {}

    try:
        # Get the budget for this line type
        budgets = template_config.get("budgets", {})
        if params.line_type not in budgets:
            raise ValueError(f"Unknown line_type: {params.line_type}")

        budget_dict = budgets[params.line_type]
        # Handle both dict and Pydantic model formats
        if hasattr(budget_dict, 'model_dump'):
            budget_dict = budget_dict.model_dump()

        raw_budget = budget_dict.get("raw_budget", 0.0)
        target_95 = budget_dict.get("target_95", 0.0)
        range_min_90 = budget_dict.get("range_min_90", 0.0)
        range_max_100 = budget_dict.get("range_max_100", 0.0)
        font_size_pt = budget_dict.get("font_size_pt", 9.5)
        letter_spacing_px = budget_dict.get("letter_spacing_px", 0.0)

        # Step 1: Parse HTML segments
        segments = parse_bold_segments(params.text_html)

        # Step 2 & 3: Resolve entities and sum weights
        weighted_total = 0.0
        rendered_text = ""
        bold_char_count = 0

        for segment_text, is_bold in segments:
            # Resolve HTML entities
            resolved_text = resolve_entities(segment_text)
            rendered_text += resolved_text

            # Look up weights and accumulate
            for char in resolved_text:
                if is_bold:
                    weight = ROBOTO_BOLD_WEIGHTS.get(char, BOLD_DEFAULT)
                    bold_char_count += 1
                else:
                    weight = ROBOTO_REGULAR_WEIGHTS.get(char, REGULAR_DEFAULT)
                weighted_total += weight

        rendered_char_count = len(rendered_text)

        # Step 4: Apply letter-spacing correction
        # digit_width_px = (1086/2048) * (font_size_pt/72) * 96
        digit_width_px = (1086 / 2048) * (font_size_pt / 72) * 96

        # actual_width_px = (weighted_total * digit_width_px) + (rendered_char_count - 1) * letter_spacing_px
        if rendered_char_count > 0:
            actual_width_px = (weighted_total * digit_width_px) + max(0, rendered_char_count - 1) * letter_spacing_px
            adjusted_weighted_total = actual_width_px / digit_width_px if digit_width_px > 0 else weighted_total
        else:
            adjusted_weighted_total = 0.0

        # Step 5: Compute fill percentage
        fill_percentage = (adjusted_weighted_total / raw_budget * 100) if raw_budget > 0 else 0.0

        # Step 6: Determine status
        if adjusted_weighted_total < range_min_90:
            status = "TOO_SHORT"
        elif adjusted_weighted_total <= range_max_100:
            status = "PASS"
        else:
            status = "OVERFLOW"

        # Step 7: Compute surplus/deficit
        surplus_or_deficit = adjusted_weighted_total - target_95

        output = MeasureWidthOutput(
            weighted_total=round(adjusted_weighted_total, 2),
            target_95=round(target_95, 2),
            raw_budget=round(raw_budget, 2),
            fill_percentage=round(fill_percentage, 1),
            status=status,
            rendered_text=rendered_text,
            rendered_char_count=rendered_char_count,
            bold_char_count=bold_char_count,
            surplus_or_deficit=round(surplus_or_deficit, 2)
        )

        return json.dumps(output.model_dump(), indent=2)

    except Exception as e:
        # Return error response
        error_output = {
            "error": f"measure_width failed: {str(e)}",
            "weighted_total": 0.0,
            "target_95": 0.0,
            "raw_budget": 0.0,
            "fill_percentage": 0.0,
            "status": "ERROR",
            "rendered_text": "",
            "rendered_char_count": 0,
            "bold_char_count": 0,
            "surplus_or_deficit": 0.0
        }
        return json.dumps(error_output, indent=2)
