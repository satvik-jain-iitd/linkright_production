"""CSS parsing utilities for template configuration extraction.

Handles extraction of CSS custom properties (variables) and dimension parsing.
"""

import re
from typing import Optional


def extract_css_variables(html: str) -> dict[str, str]:
    """Extract CSS custom properties from :root {} block.

    Searches for a <style> tag and extracts all custom properties (--var-name)
    from the :root block.

    Args:
        html: HTML string containing a <style> tag.

    Returns:
        Dictionary mapping {variable_name: value}.
        Example: {"--brand-primary-color": "#0066cc", "--page-width": "210"}
    """
    # Find the style tag
    style_match = re.search(r'<style[^>]*>(.*?)</style>', html, re.DOTALL | re.IGNORECASE)
    if not style_match:
        return {}

    style_content = style_match.group(1)

    # Find the :root block
    root_match = re.search(r':root\s*\{([^}]*)\}', style_content, re.DOTALL)
    if not root_match:
        return {}

    root_block = root_match.group(1)

    # Extract all --var-name: value; pairs
    variables = {}
    pattern = r'--([a-zA-Z0-9\-]+)\s*:\s*([^;]+);'
    for match in re.finditer(pattern, root_block):
        var_name = f"--{match.group(1)}"
        var_value = match.group(2).strip()
        variables[var_name] = var_value

    return variables


def parse_dimension(value: str) -> float:
    """Convert CSS dimension strings to pixels (px).

    Handles conversion from mm, pt, px, and em units.
    - mm: multiply by 3.7795 (at 96 dpi)
    - pt: multiply by 96/72 (points to pixels)
    - px: return as-is
    - em: multiply by 16 (assuming 16px base)

    Args:
        value: CSS dimension string (e.g., "210mm", "12pt", "100px", "2em").

    Returns:
        Floating-point value in pixels.

    Raises:
        ValueError: If the value cannot be parsed.
    """
    value = value.strip()

    # Try to extract number and unit
    match = re.match(r'^([\d.]+)\s*(mm|pt|px|em)?$', value)
    if not match:
        raise ValueError(f"Cannot parse dimension: {value}")

    num = float(match.group(1))
    unit = match.group(2) or 'px'

    if unit == 'mm':
        return num * 3.7795
    elif unit == 'pt':
        return num * (96 / 72)
    elif unit == 'px':
        return num
    elif unit == 'em':
        return num * 16
    else:
        raise ValueError(f"Unknown unit: {unit}")
