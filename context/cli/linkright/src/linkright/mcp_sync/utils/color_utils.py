"""Color utilities for contrast validation and color manipulation.

Implements W3C contrast ratio formula and color adjustment functions.
"""

import re
from typing import Tuple


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple.

    Args:
        hex_color: Color in hex format (#RRGGBB or RRGGBB).

    Returns:
        Tuple of (red, green, blue) integers in range 0-255.

    Raises:
        ValueError: If the hex color is invalid.
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")

    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        raise ValueError(f"Invalid hex color: {hex_color}")


def relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance per W3C formula.

    Used for contrast ratio calculations.
    L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    where R, G, B are normalized to 0-1 and linearized.

    Args:
        r, g, b: RGB values (0-255).

    Returns:
        Relative luminance (0.0-1.0).
    """
    def linearize(c):
        c = c / 255.0
        if c <= 0.03928:
            return c / 12.92
        else:
            return ((c + 0.055) / 1.055) ** 2.4

    r_linear = linearize(r)
    g_linear = linearize(g)
    b_linear = linearize(b)

    return 0.2126 * r_linear + 0.7152 * g_linear + 0.0722 * b_linear


def contrast_ratio(color1: str, color2: str) -> float:
    """Calculate contrast ratio between two colors per W3C formula.

    Contrast = (L_lighter + 0.05) / (L_darker + 0.05)

    Args:
        color1: First color in hex format (#RRGGBB).
        color2: Second color in hex format (#RRGGBB).

    Returns:
        Contrast ratio (1.0-21.0).

    Raises:
        ValueError: If hex colors are invalid.
    """
    r1, g1, b1 = hex_to_rgb(color1)
    r2, g2, b2 = hex_to_rgb(color2)

    l1 = relative_luminance(r1, g1, b1)
    l2 = relative_luminance(r2, g2, b2)

    l_lighter = max(l1, l2)
    l_darker = min(l1, l2)

    return (l_lighter + 0.05) / (l_darker + 0.05)


def lighten_color(hex_color: str, factor: float = 0.2) -> str:
    """Lighten a color by blending toward white.

    Args:
        hex_color: Color in hex format (#RRGGBB).
        factor: Blend factor (0.0-1.0). 0.0 = original color, 1.0 = white.

    Returns:
        Lightened color as hex string (#RRGGBB).
    """
    r, g, b = hex_to_rgb(hex_color)

    # Blend toward white (255, 255, 255)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)

    return f"#{r:02x}{g:02x}{b:02x}"


def darken_color(hex_color: str, factor: float = 0.2) -> str:
    """Darken a color by blending toward black.

    Args:
        hex_color: Color in hex format (#RRGGBB).
        factor: Blend factor (0.0-1.0). 0.0 = original color, 1.0 = black.

    Returns:
        Darkened color as hex string (#RRGGBB).
    """
    r, g, b = hex_to_rgb(hex_color)

    # Blend toward black (0, 0, 0)
    r = int(r * (1 - factor))
    g = int(g * (1 - factor))
    b = int(b * (1 - factor))

    return f"#{r:02x}{g:02x}{b:02x}"


def suggest_accessible_color(foreground: str, background: str, target_ratio: float = 4.5) -> str:
    """Suggest a foreground color that meets target contrast ratio against background.

    Iteratively adjusts the foreground color (lightening or darkening) until
    the contrast ratio meets or exceeds the target.

    Args:
        foreground: Starting foreground color (#RRGGBB).
        background: Background color (#RRGGBB).
        target_ratio: Target contrast ratio (default 4.5 for WCAG AA).

    Returns:
        Adjusted foreground color as hex string (#RRGGBB).
    """
    current_ratio = contrast_ratio(foreground, background)

    if current_ratio >= target_ratio:
        return foreground

    # Determine if we need to lighten or darken
    bg_luminance = relative_luminance(*hex_to_rgb(background))
    # If background is light, darken foreground; if dark, lighten foreground
    if bg_luminance > 0.5:
        # Light background: darken foreground
        factor_step = 0.05
        for i in range(1, 21):
            adjusted = darken_color(foreground, factor_step * i)
            if contrast_ratio(adjusted, background) >= target_ratio:
                return adjusted
        return darken_color(foreground, 1.0)
    else:
        # Dark background: lighten foreground
        factor_step = 0.05
        for i in range(1, 21):
            adjusted = lighten_color(foreground, factor_step * i)
            if contrast_ratio(adjusted, background) >= target_ratio:
                return adjusted
        return lighten_color(foreground, 1.0)
