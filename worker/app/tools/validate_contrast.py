"""Tool 3: validate_contrast - WCAG 2.0 AA color contrast validation.

Checks contrast ratio between foreground and background colors.
Uses W3C relative luminance formula and suggests accessible color fixes if needed.
"""

import json
from pydantic import BaseModel, Field, ConfigDict

from ..utils.color_utils import contrast_ratio, suggest_accessible_color


class ContrastInput(BaseModel):
    """Input for resume_validate_contrast tool."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "foreground_hex": "#4285F4",
        "background_hex": "#FFFFFF"
    }})

    foreground_hex: str = Field(
        ...,
        description="Text color hex code (e.g., '#4285F4')"
    )
    background_hex: str = Field(
        ...,
        description="Background color hex code (e.g., '#FFFFFF')"
    )


class ContrastOutput(BaseModel):
    """Output from resume_validate_contrast tool."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "contrast_ratio": 4.71,
        "passes_wcag_aa_normal_text": True,
        "passes_wcag_aa_large_text": True,
        "recommendation": "OK"
    }})

    contrast_ratio: float = Field(
        ...,
        description="Computed WCAG contrast ratio (e.g., 4.71)"
    )
    passes_wcag_aa_normal_text: bool = Field(
        ...,
        description="True if ratio >= 4.5 (for text < 18pt or < 14pt bold)"
    )
    passes_wcag_aa_large_text: bool = Field(
        ...,
        description="True if ratio >= 3.0 (for text >= 18pt or >= 14pt bold)"
    )
    recommendation: str = Field(
        ...,
        description="'OK' if passes, else suggested color as hex code"
    )


async def resume_validate_contrast(params: ContrastInput) -> str:
    """Check WCAG 2.0 AA contrast ratio between two colors.

    Uses the W3C relative luminance formula:
        L = 0.2126 * R_lin + 0.7152 * G_lin + 0.0722 * B_lin
        where R_lin = (R/255)^2.4 (simplified gamma)

    Contrast ratio = (L_lighter + 0.05) / (L_darker + 0.05)

    WCAG AA requirements:
    - Normal text (< 18pt or < 14pt bold): ratio >= 4.5
    - Large text (>= 18pt or >= 14pt bold): ratio >= 3.0

    Since resume body text is 9.5pt, it counts as normal text -> needs 4.5:1.
    This tool should be called for EVERY color that will be used as text on the
    page background: brand primary (section titles, bold metrics), brand secondary,
    metric-positive color, metric-negative color. All must pass 4.5:1 against
    --ui-page-bg-color for normal text at 9.5pt.

    If the ratio fails, the tool suggests a darker/lighter variant of the
    foreground color that achieves 4.5:1.

    Args:
        params: ContrastInput with foreground_hex and background_hex

    Returns:
        JSON string with ContrastOutput
    """
    try:
        # Compute contrast ratio
        ratio = contrast_ratio(params.foreground_hex, params.background_hex)

        # Check WCAG AA levels
        passes_normal = ratio >= 4.5
        passes_large = ratio >= 3.0

        # Generate recommendation
        if passes_normal:
            recommendation = "OK"
        else:
            # Suggest an accessible color
            suggested = suggest_accessible_color(
                params.foreground_hex,
                params.background_hex,
                target_ratio=4.5
            )
            recommendation = suggested

        output = ContrastOutput(
            contrast_ratio=round(ratio, 2),
            passes_wcag_aa_normal_text=passes_normal,
            passes_wcag_aa_large_text=passes_large,
            recommendation=recommendation
        )

        return json.dumps(output.model_dump(), indent=2)

    except Exception as e:
        error_output = {
            "error": f"validate_contrast failed: {str(e)}",
            "contrast_ratio": 0.0,
            "passes_wcag_aa_normal_text": False,
            "passes_wcag_aa_large_text": False,
            "recommendation": "ERROR"
        }
        return json.dumps(error_output, indent=2)
