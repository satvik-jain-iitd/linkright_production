"""Tool 4: validate_page_fit - Vertical page fit validation and space allocation.

Checks if all planned content sections fit vertically on one A4 page.
Returns recommended section allocations based on career level.
"""

import json
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

try:
    # Try absolute import (when used as MCP tool)
    from data.career_profiles import CAREER_PROFILES
except ImportError:
    # Fall back to relative import (when imported from package)
    from ..data.career_profiles import CAREER_PROFILES


class SectionSpec(BaseModel):
    """Specification for a single resume section."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "section_type": "experience",
        "entry_count": 3,
        "project_count_per_entry": [2, 2, 1],
        "bullets_per_project": 3,
        "edge_to_edge_lines": 0,
        "has_entry_subhead": True
    }})

    section_type: str = Field(
        ...,
        description=(
            "One of: header, summary, experience, education, skills, awards, "
            "voluntary, projects, achievements, interests, certifications, custom"
        )
    )
    entry_count: int = Field(
        default=1,
        description="Number of company/institution/project entries"
    )
    project_count_per_entry: list[int] = Field(
        default_factory=lambda: [1],
        description="List: number of projects/subsections under each entry"
    )
    bullets_per_project: int = Field(
        default=2,
        description="Bullets per project group"
    )
    edge_to_edge_lines: int = Field(
        default=0,
        description="Non-bullet lines (e.g., skills, education summary)"
    )
    has_entry_subhead: bool = Field(
        default=True,
        description="Whether entries have subheadings"
    )
    summary_lines: int = Field(
        default=0,
        description="Number of lines in professional summary (for summary section type)"
    )


class PageFitInput(BaseModel):
    """Input for resume_validate_page_fit tool."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "sections": [
            {"section_type": "header"},
            {"section_type": "experience", "entry_count": 3}
        ],
        "career_level": "mid"
    }})

    sections: list[SectionSpec] = Field(
        ...,
        description="List of all planned sections in order"
    )
    career_level: Optional[str] = Field(
        default=None,
        description="Optional: 'fresher', 'entry', 'mid', 'senior', or 'executive'"
    )


class SectionHeightBreakdown(BaseModel):
    """Breakdown of height for a single section."""

    section_type: str = Field(..., description="Section type identifier")
    title_height_mm: float = Field(..., description="Section title height")
    content_height_mm: float = Field(..., description="Content/entries height")
    spacing_height_mm: float = Field(..., description="Spacing after section")
    total_mm: float = Field(..., description="Total height for this section")


class PageFitOutput(BaseModel):
    """Output from resume_validate_page_fit tool."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "total_height_mm": 250.0,
        "usable_height_mm": 271.6,
        "fits_one_page": True,
        "remaining_mm": 21.6,
        "breakdown": []
    }})

    total_height_mm: float = Field(
        ...,
        description="Total computed height of all sections"
    )
    usable_height_mm: float = Field(
        ...,
        description="Available height on page (271.6mm for A4)"
    )
    fits_one_page: bool = Field(
        ...,
        description="True if total_height_mm ≤ usable_height_mm"
    )
    remaining_mm: float = Field(
        ...,
        description="Positive = space left, negative = overflow amount"
    )
    breakdown: list[dict] = Field(
        ...,
        description="Per-section height details"
    )
    recommended_allocation: Optional[dict[str, float]] = Field(
        default=None,
        description="If career_level provided, section percentages from career profile"
    )
    recommendation: str = Field(
        ...,
        description="Human-readable assessment: 'fits', 'tight', 'overflow', or 'underfill'"
    )
    underfill_suggestion: Optional[str] = Field(
        default=None,
        description="If underfill detected, suggests how many bullets/lines could fill the gap"
    )


async def resume_validate_page_fit(
    params: PageFitInput,
    template_config: dict = None
) -> str:
    """Check if all planned sections fit within one page vertically.

    Uses pre-computed element heights from template config.
    Computes total height using the full formula, accounting for:
    - header_block (21.34mm)
    - each section's title, entries, projects, bullets
    - summary special handling via summary_lines

    If career_level provided, output includes recommended section allocations
    (section_type → percentage of usable space).

    Called TWICE:
    1. Before building sections (proactive) — catch impossible layouts early
    2. After quality check (reactive) — final confirmation

    Args:
        params: PageFitInput with sections list and optional career_level
        template_config: Template configuration dict (should be injected from server state)

    Returns:
        JSON string with PageFitOutput
    """
    if template_config is None:
        template_config = {}

    try:
        # Extract vertical heights from template config
        v_heights = template_config.get("vertical_heights_mm", {})
        usable_height_mm = template_config.get("usable_height_mm", 271.6)

        # Default heights if not found
        if not v_heights:
            v_heights = {
                "identity_horizon": 1.06,
                "header_block": 21.34,
                "section_title": 7.68,
                "section_spacing": 4.0,
                "entry_header": 4.44,
                "entry_subhead": 5.24,
                "entry_spacing": 2.5,
                "project_title": 5.52,
                "bullet_line": 4.52,
                "edge_to_edge_line": 4.02,
                "summary_line": 4.02,
            }

        # Start with header block
        total_height_mm = v_heights.get("header_block", 21.34)
        breakdown = []

        # Process each section
        for section in params.sections:
            section_height = 0.0

            if section.section_type == "header":
                # Header already counted, skip
                continue

            # Add section title
            section_title_height = v_heights.get("section_title", 7.68)
            section_height += section_title_height

            # Add content based on section type
            if section.section_type == "summary":
                # Summary section: summary_lines × summary_line_height
                content_height = section.summary_lines * v_heights.get("summary_line", 4.02)
                section_height += content_height

            elif section.section_type in ["skills", "interests", "awards"]:
                # Edge-to-edge lines
                content_height = section.edge_to_edge_lines * v_heights.get("edge_to_edge_line", 4.02)
                section_height += content_height

            else:
                # Experience, education, projects, custom: with entries
                content_height = 0.0

                # Ensure project_count_per_entry has enough entries
                project_counts = section.project_count_per_entry
                if len(project_counts) < section.entry_count:
                    project_counts = project_counts + [1] * (section.entry_count - len(project_counts))

                for entry_idx in range(section.entry_count):
                    # Entry header
                    content_height += v_heights.get("entry_header", 4.44)

                    # Entry subhead (optional)
                    if section.has_entry_subhead:
                        content_height += v_heights.get("entry_subhead", 5.24)

                    # Projects under this entry
                    num_projects = project_counts[entry_idx] if entry_idx < len(project_counts) else 1
                    for _ in range(num_projects):
                        # Project title
                        content_height += v_heights.get("project_title", 5.52)

                        # Bullets under this project
                        content_height += section.bullets_per_project * v_heights.get("bullet_line", 4.52)

                    # Entry spacing
                    if entry_idx < section.entry_count - 1:
                        content_height += v_heights.get("entry_spacing", 2.5)

                section_height += content_height

            # Add section spacing
            section_spacing = v_heights.get("section_spacing", 4.0)
            section_height += section_spacing

            # Add to total
            total_height_mm += section_height

            # Record breakdown
            breakdown.append({
                "section_type": section.section_type,
                "height_mm": round(section_height, 2)
            })

        # Compute remaining space
        remaining_mm = usable_height_mm - total_height_mm

        # Determine fit status (4-tier: overflow, tight, fits, underfill)
        underfill_suggestion = None
        if remaining_mm < 0:
            recommendation = "overflow"
        elif remaining_mm <= 5:
            recommendation = "tight"
        elif remaining_mm <= 20:
            recommendation = "fits"
        else:
            recommendation = "underfill"
            extra_bullets = int(remaining_mm / v_heights.get("bullet_line", 4.52))
            extra_lines = int(remaining_mm / v_heights.get("edge_to_edge_line", 4.02))
            underfill_suggestion = (
                f"Page has {remaining_mm:.1f}mm unused space. "
                f"Could fit ~{extra_bullets} more bullets or ~{extra_lines} edge-to-edge lines. "
                f"Consider adding: more experience bullets, scholastic achievements, voluntary work, or skills."
            )

        # Get career-level allocation if provided
        recommended_allocation = None
        if params.career_level and params.career_level in CAREER_PROFILES:
            profile = CAREER_PROFILES[params.career_level]
            recommended_allocation = profile.get("space_allocation", {})

        output = PageFitOutput(
            total_height_mm=round(total_height_mm, 2),
            usable_height_mm=round(usable_height_mm, 2),
            fits_one_page=remaining_mm >= 0,
            remaining_mm=round(remaining_mm, 2),
            breakdown=breakdown,
            recommended_allocation=recommended_allocation,
            recommendation=recommendation,
            underfill_suggestion=underfill_suggestion
        )

        return json.dumps(output.model_dump(), indent=2)

    except Exception as e:
        error_output = {
            "error": f"validate_page_fit failed: {str(e)}",
            "total_height_mm": 0.0,
            "usable_height_mm": 271.6,
            "fits_one_page": False,
            "remaining_mm": 0.0,
            "breakdown": [],
            "recommended_allocation": None,
            "recommendation": "ERROR"
        }
        return json.dumps(error_output, indent=2)
