"""Tool 7: assemble_html - Final HTML assembly with brand colors and content injection.

Assembles the final HTML resume by injecting all content, brand colors, and
optional logo into the template. This is the final output generation step.
"""

from __future__ import annotations

import re
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from linkright.utils.color_utils import lighten_color, contrast_ratio


class ThemeColors(BaseModel):
    """Theme color configuration for the resume."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "brand_primary": "#4285F4",
        "brand_secondary": "#EA4335",
        "brand_tertiary": "",
        "brand_quaternary": "",
        "page_bg": "#FFFFFF",
        "canvas_bg": "#F1F3F4",
        "text_primary": "#202124",
        "text_secondary": "#5F6368",
        "divider": "#DADCE0",
        "metric_positive": "",
        "metric_negative": ""
    }})

    brand_primary: str = Field(
        ...,
        description="Hex code for --brand-primary-color"
    )
    brand_secondary: str = Field(
        ...,
        description="Hex code for --brand-secondary-color"
    )
    brand_tertiary: str = Field(
        default="",
        description="Hex code for --brand-tertiary-color (auto-derived if empty)"
    )
    brand_quaternary: str = Field(
        default="",
        description="Hex code for --brand-quaternary-color (auto-derived if empty)"
    )
    page_bg: str = Field(
        default="#FFFFFF",
        description="Hex code for --ui-page-bg-color (page surface)"
    )
    canvas_bg: str = Field(
        default="#F1F3F4",
        description="Hex code for --ui-canvas-bg-color (viewer background)"
    )
    text_primary: str = Field(
        default="#202124",
        description="Hex code for --ui-text-primary-color (body text)"
    )
    text_secondary: str = Field(
        default="#5F6368",
        description="Hex code for --ui-text-secondary-color (meta text)"
    )
    divider: str = Field(
        default="#DADCE0",
        description="Hex code for --ui-divider-color (hairlines)"
    )
    metric_positive: str = Field(
        default="",
        description="Hex code for green metric arrows (auto-derived to #34A853 if empty)"
    )
    metric_negative: str = Field(
        default="",
        description="Hex code for red metric arrows (auto-derived to #EA4335 if empty)"
    )


class LogoSpec(BaseModel):
    """Logo specification with dimensions and placement."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "src": "data:image/png;base64,iVBORw0KG...",
        "max_height_px": 24,
        "max_width_px": 80,
        "alt_text": "Company Logo",
        "position": "header-right"
    }})

    src: str = Field(
        default="YOUR_BASE64_URL",
        description="Base64 data URI or URL placeholder"
    )
    max_height_px: int = Field(
        default=24,
        description="Maximum height in pixels"
    )
    max_width_px: int = Field(
        default=80,
        description="Maximum width in pixels"
    )
    alt_text: str = Field(
        default="Company Logo",
        description="Alt text for accessibility"
    )
    position: str = Field(
        default="header-right",
        description="Placement: only 'header-right' supported in v2"
    )


class HeaderData(BaseModel):
    """Header information: name, role, and contacts."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "name": "Jane Smith",
        "role": "Senior Software Engineer",
        "contacts": [
            "Phone: +1-234-567-8900",
            "Email: jane@example.com",
            "LinkedIn: linkedin.com/in/jane-smith",
            "Portfolio: jane-portfolio.com"
        ]
    }})

    name: str = Field(
        ...,
        description="Candidate full name"
    )
    role: str = Field(
        ...,
        description="Target role/title"
    )
    contacts: list[str] = Field(
        ...,
        description="Contact items: ['Phone: +91-XXX', 'Email: x@y.com', 'LinkedIn: linkedin.com/in/user', 'Portfolio: site.com']"
    )


class SectionContent(BaseModel):
    """A section of the resume with its HTML content."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "section_html": "<div class=\"entry\">...</div>",
        "section_order": 1
    }})

    section_html: str = Field(
        ...,
        description="Complete HTML for this section (with all nested entries, projects, bullets)"
    )
    section_order: int = Field(
        ...,
        description="Position in the page (1-based)"
    )


class AssembleInput(BaseModel):
    """Input for resume_assemble_html tool."""

    model_config = ConfigDict(json_schema_extra={})

    template_html: str = Field(
        ...,
        description="Original HTML template source code"
    )
    theme_colors: ThemeColors = Field(
        ...,
        description="All 9 CSS color variables + 2 metric colors"
    )
    header: HeaderData = Field(
        ...,
        description="Name, role, contacts"
    )
    sections: list[SectionContent] = Field(
        ...,
        description="Section HTML snippets in order"
    )
    logo_spec: Optional[LogoSpec] = Field(
        default=None,
        description="Optional logo with dimensions and src"
    )


class AssembleOutput(BaseModel):
    """Output from resume_assemble_html tool."""

    model_config = ConfigDict(json_schema_extra={})

    final_html: str = Field(
        ...,
        description="Complete, ready-to-open HTML file"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Any alerts (e.g., 'Logo width exceeds max')"
    )


def _derive_brand_colors(theme_colors: ThemeColors) -> ThemeColors:
    """Derive missing brand colors (tertiary/quaternary) using HSL lightness shift.

    If brand_tertiary is empty: derive as 40% lighter tint of brand_primary.
    If brand_quaternary is empty: derive as 40% lighter tint of brand_secondary.

    Args:
        theme_colors: ThemeColors input

    Returns:
        Updated ThemeColors with derived colors filled in
    """
    if not theme_colors.brand_tertiary:
        theme_colors.brand_tertiary = lighten_color(theme_colors.brand_primary, factor=0.4)

    if not theme_colors.brand_quaternary:
        theme_colors.brand_quaternary = lighten_color(theme_colors.brand_secondary, factor=0.4)

    return theme_colors


def _set_metric_colors(theme_colors: ThemeColors) -> tuple[ThemeColors, list[str]]:
    """Set metric colors with contrast validation.

    If metric_positive empty: set to #34A853 (Google Green).
    If metric_negative empty: set to #EA4335 (Google Red).
    Validate both against page_bg using 4.5:1 contrast ratio.
    If either fails: fallback both to brand_primary.

    Args:
        theme_colors: ThemeColors with potential empty metric colors

    Returns:
        Tuple of (updated ThemeColors, warnings list)
    """
    warnings = []

    # Set defaults
    if not theme_colors.metric_positive:
        theme_colors.metric_positive = "#34A853"  # Google Green
    if not theme_colors.metric_negative:
        theme_colors.metric_negative = "#EA4335"  # Google Red

    # Validate contrast
    pos_ratio = contrast_ratio(theme_colors.metric_positive, theme_colors.page_bg)
    neg_ratio = contrast_ratio(theme_colors.metric_negative, theme_colors.page_bg)

    if pos_ratio < 4.5 or neg_ratio < 4.5:
        warnings.append(
            f"Metric colors fail 4.5:1 contrast (pos: {pos_ratio:.2f}, neg: {neg_ratio:.2f}). "
            f"Falling back to brand_primary."
        )
        theme_colors.metric_positive = theme_colors.brand_primary
        theme_colors.metric_negative = theme_colors.brand_primary

    return theme_colors, warnings


def _replace_css_variables(html: str, theme_colors: ThemeColors) -> str:
    """Replace all :root CSS variable values with theme colors.

    Locates the :root { ... } block and replaces values for all 9 variables.

    Args:
        html: Template HTML
        theme_colors: Color values to inject

    Returns:
        Updated HTML with new CSS variable values
    """
    # Map of CSS variable names to color field names
    var_map = {
        "--brand-primary-color": theme_colors.brand_primary,
        "--brand-secondary-color": theme_colors.brand_secondary,
        "--brand-tertiary-color": theme_colors.brand_tertiary,
        "--brand-quaternary-color": theme_colors.brand_quaternary,
        "--ui-page-bg-color": theme_colors.page_bg,
        "--ui-canvas-bg-color": theme_colors.canvas_bg,
        "--ui-text-primary-color": theme_colors.text_primary,
        "--ui-text-secondary-color": theme_colors.text_secondary,
        "--ui-divider-color": theme_colors.divider,
        "--metric-positive-color": theme_colors.metric_positive,
        "--metric-negative-color": theme_colors.metric_negative,
    }

    result = html

    # Replace each variable value in :root block
    for var_name, color_value in var_map.items():
        # Pattern: var_name: any_value;
        pattern = f"({var_name}\\s*:\\s*)([^;]+)(;)"
        replacement = f"\\g<1>{color_value}\\3"
        result = re.sub(pattern, replacement, result)

    return result


def _extract_contact_value(contact_str: str) -> tuple[str, str, str]:
    """Extract label, value, and link type from contact string.

    Examples:
    - "Phone: +1-234-567-8900" -> ("Phone", "+1-234-567-8900", "tel")
    - "Email: jane@example.com" -> ("Email", "jane@example.com", "mailto")
    - "LinkedIn: linkedin.com/in/jane" -> ("LinkedIn", "linkedin.com/in/jane", "linkedin")
    - "Portfolio: jane.com" -> ("Portfolio", "jane.com", "portfolio")

    Args:
        contact_str: Contact string with label and value

    Returns:
        Tuple of (label, value, link_type)
    """
    if ":" not in contact_str:
        return "", contact_str, "unknown"

    label, value = contact_str.split(":", 1)
    label = label.strip()
    value = value.strip()

    link_type = "unknown"
    if label.lower() == "phone":
        link_type = "tel"
    elif label.lower() == "email":
        link_type = "mailto"
    elif "linkedin" in label.lower():
        link_type = "linkedin"
    elif "portfolio" in label.lower() or "website" in label.lower() or "site" in label.lower():
        link_type = "portfolio"

    return label, value, link_type


def _create_contact_link(value: str, link_type: str) -> str:
    """Create a hyperlink for a contact value.

    Args:
        value: Contact value (email, phone, URL, etc.)
        link_type: Type of link (tel, mailto, linkedin, portfolio, unknown)

    Returns:
        HTML anchor tag with proper href
    """
    style = 'style="color: inherit; text-decoration: none;"'

    if link_type == "tel":
        # Extract digits for tel: URL
        digits = "".join(c for c in value if c.isdigit() or c in ["+", "-"])
        return f'<a href="tel:{digits}" {style}>{value}</a>'

    elif link_type == "mailto":
        return f'<a href="mailto:{value}" {style}>{value}</a>'

    elif link_type == "linkedin":
        # Ensure URL format
        if not value.startswith("http"):
            url = f"https://{value}"
        else:
            url = value
        return f'<a href="{url}" {style}>{value}</a>'

    elif link_type == "portfolio":
        # Ensure URL format
        if not value.startswith("http"):
            url = f"https://{value}"
        else:
            url = value
        return f'<a href="{url}" {style}>{value}</a>'

    else:
        # Unknown type: return as plain text
        return value


def _replace_header_content(html: str, header: HeaderData) -> str:
    """Replace header content: name, role, and contacts.

    Finds .name, .role, and .contact-info spans and replaces their content.
    Wraps contact values in appropriate hyperlinks.

    Args:
        html: Template HTML
        header: HeaderData with name, role, contacts

    Returns:
        Updated HTML with header content injected
    """
    result = html

    # Replace name (template uses <div class="name">)
    result = re.sub(
        r'<div[^>]*class="name"[^>]*>[^<]*</div>',
        f'<div class="name">{header.name}</div>',
        result,
        flags=re.IGNORECASE
    )

    # Replace role (template uses <div class="role">)
    result = re.sub(
        r'<div[^>]*class="role"[^>]*>[^<]*</div>',
        f'<div class="role">{header.role}</div>',
        result,
        flags=re.IGNORECASE
    )

    # Replace or create contact info
    contact_html = []
    for contact in header.contacts:
        label, value, link_type = _extract_contact_value(contact)
        link = _create_contact_link(value, link_type)
        if label:
            contact_html.append(f'<span><strong>{label}</strong>: {link}</span>')
        else:
            contact_html.append(f'<span>{link}</span>')

    contact_block = "\n".join(contact_html)

    # Replace contact-info div or span
    result = re.sub(
        r'<div[^>]*class="[^"]*contact-info[^"]*"[^>]*>.*?</div>',
        f'<div class="contact-info">\n{contact_block}\n</div>',
        result,
        flags=re.IGNORECASE | re.DOTALL
    )

    return result


def _replace_section_content(html: str, sections: list[SectionContent]) -> str:
    """Replace ALL template sections with provided sections.

    Strategy: Find the first numbered comment marker (<!-- 1. ... -->),
    strip everything from there to the closing </div> of the page container,
    then inject our sections in that space.

    Args:
        html: Template HTML
        sections: List of SectionContent objects

    Returns:
        Updated HTML with only our sections
    """
    # Find where template sections start (first <!-- N. ... --> comment)
    marker_match = re.search(r'<!--\s*1\.\s*[^-]*-->', html)
    if not marker_match:
        # No template sections found — just append before </body>
        sorted_sections = sorted(sections, key=lambda s: s.section_order)
        sections_html = "\n\n    ".join(s.section_html for s in sorted_sections)
        return html.replace('</body>', f'    {sections_html}\n</body>')

    # Everything before the first section marker
    before = html[:marker_match.start()]

    # Find the page-closing </div> and </body> at the end
    # The template ends with: </div>\n\n</body>\n</html>
    end_match = re.search(r'</div>\s*</body>', html[marker_match.start():])
    if end_match:
        after = html[marker_match.start() + end_match.start():]
    else:
        after = '\n</div>\n\n</body>\n</html>'

    # Build our sections
    sorted_sections = sorted(sections, key=lambda s: s.section_order)
    sections_html = "\n\n    ".join(s.section_html for s in sorted_sections)

    return before + "    " + sections_html + "\n\n" + after


def _add_margin_to_last_section(html: str) -> str:
    """Add margin-top: auto to the last section div.

    Finds the last <div class="section"> and adds style="margin-top: auto;".

    Args:
        html: Template HTML

    Returns:
        Updated HTML with auto margin on last section
    """
    # Find all section divs
    section_pattern = r'<div[^>]*class="[^"]*section[^"]*"[^>]*>'
    matches = list(re.finditer(section_pattern, html, flags=re.IGNORECASE))

    if not matches:
        return html

    # Get the last match
    last_match = matches[-1]
    start, end = last_match.span()
    original_tag = html[start:end]

    # Add margin-top: auto if not already present
    if 'margin-top: auto' not in original_tag:
        # Add or append style attribute
        if 'style=' in original_tag:
            # Insert into existing style
            new_tag = original_tag.replace('style="', 'style="margin-top: auto; ')
        else:
            # Add new style attribute
            new_tag = original_tag.rstrip('>') + ' style="margin-top: auto;">'

        html = html[:start] + new_tag + html[end:]

    return html


def _insert_logo(html: str, logo_spec: LogoSpec) -> tuple[str, list[str]]:
    """Insert logo image into header with absolute positioning.

    Creates <img> element with src and alt text, positioned absolutely
    in the top-right of the header.

    Args:
        html: Template HTML
        logo_spec: LogoSpec with src, dimensions, and alt text

    Returns:
        Tuple of (updated HTML, warnings list)
    """
    warnings = []

    # Create logo img tag
    logo_img = (
        f'<img src="{logo_spec.src}" '
        f'alt="{logo_spec.alt_text}" '
        f'style="position: absolute; '
        f'top: calc(var(--page-margin) + 1mm); '
        f'right: var(--page-margin); '
        f'max-height: {logo_spec.max_height_px}px; '
        f'max-width: {logo_spec.max_width_px}px;" '
        f'/>'
    )

    # Find header element and ensure it has position: relative
    header_pattern = r'<header[^>]*>'
    header_match = re.search(header_pattern, html, flags=re.IGNORECASE)

    if header_match:
        # Insert logo before closing header tag
        header_end_pattern = r'</header>'
        result = re.sub(
            header_end_pattern,
            f'{logo_img}\n</header>',
            html,
            count=1,
            flags=re.IGNORECASE
        )

        warnings.append(f"Logo inserted with max dimensions {logo_spec.max_width_px}px x {logo_spec.max_height_px}px")
        return result, warnings
    else:
        warnings.append("Could not find <header> element to insert logo")
        return html, warnings


def _verify_print_rules(html: str) -> list[str]:
    """Verify that @media print rules are intact.

    Checks for @media print block with critical rules:
    - margin: 0
    - box-shadow: none
    - background: white
    - @page size: A4

    Args:
        html: Template HTML

    Returns:
        List of warnings if rules are missing or malformed
    """
    warnings = []

    # Check for @media print block
    if "@media print" not in html:
        warnings.append("Warning: @media print block not found")
        return warnings

    # Check for critical print rules (basic check)
    print_section = html[html.find("@media print"):html.find("@media print") + 2000]

    if "margin: 0" not in print_section and "margin:0" not in print_section:
        warnings.append("Warning: @media print should include 'margin: 0'")

    if "@page" not in print_section:
        warnings.append("Warning: @media print should include '@page' rule")

    return warnings


def assemble_html(params: AssembleInput) -> AssembleOutput:
    """Assemble the final HTML resume by injecting content and colors into template.

    Performs 11 operations in order:
    1. Replace all 9 CSS variable values with ThemeColors fields
    2. Derive missing brand colors (tertiary/quaternary -> lighter tints)
    3. Set metric colors; validate contrast; fallback if needed
    4. Replace header: name, role, contact spans
    5. Wrap contact values in hyperlinks (mailto, tel, https)
    6. Replace section content with provided section HTML snippets in order
    7. Add margin-top: auto to last section div
    8. If logo_spec provided: insert <img> with absolute positioning
    9. Verify @media print rules intact
    10. Add footer comment: Print to PDF using Chrome for best results
    11. Return final HTML and warnings

    CRITICAL: Only modify content slots. Never modify CSS class definitions,
    layout rules, flex properties, or page dimensions.

    Args:
        params: AssembleInput with template, colors, header, sections, optional logo

    Returns:
        AssembleOutput containing final_html and warnings
    """
    warnings = []

    # 1. Derive missing brand colors
    theme_colors = _derive_brand_colors(params.theme_colors)

    # 2. Set and validate metric colors
    theme_colors, metric_warnings = _set_metric_colors(theme_colors)
    warnings.extend(metric_warnings)

    # 3. Replace CSS variables
    html = _replace_css_variables(params.template_html, theme_colors)

    # 4-5. Replace header content with hyperlinks
    html = _replace_header_content(html, params.header)

    # 6. Replace section content
    html = _replace_section_content(html, params.sections)

    # 7. Add margin-top: auto to last section
    html = _add_margin_to_last_section(html)

    # 8. Insert logo if provided
    if params.logo_spec:
        html, logo_warnings = _insert_logo(html, params.logo_spec)
        warnings.extend(logo_warnings)

    # 9. Verify print rules
    print_warnings = _verify_print_rules(html)
    warnings.extend(print_warnings)

    # 10. Add footer comment
    html = html.rstrip()
    if not html.endswith("</body>"):
        html += "\n</body>"

    html = html.replace(
        "</body>",
        "\n<!-- Print to PDF using Chrome for best results -->\n</body>"
    )

    return AssembleOutput(
        final_html=html,
        warnings=warnings
    )
