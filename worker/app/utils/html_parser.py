"""HTML parsing utilities for text width measurement.

Handles extraction of text segments with bold flags and HTML entity resolution.
"""

import re
from typing import Optional

from ..data.html_entities import HTML_ENTITIES


def parse_bold_segments(text_html: str) -> list[tuple[str, bool]]:
    """Parse HTML to extract text segments with bold flags.

    Matches <b>, <b style="...">, and <strong> tags.
    Returns list of (text, is_bold) tuples.

    Args:
        text_html: HTML string containing optional bold tags and entities.

    Returns:
        List of (text_segment, is_bold_flag) tuples.
        All HTML tags are stripped; only visible text is included.
    """
    segments = []
    pattern = re.compile(r'<(b|strong)(?:\s[^>]*)?>(.+?)</\1>', re.DOTALL | re.IGNORECASE)

    last_end = 0
    for match in pattern.finditer(text_html):
        # Add non-bold text before this match
        if match.start() > last_end:
            text_before = text_html[last_end : match.start()]
            if text_before:
                segments.append((text_before, False))

        # Add bold text from this match
        bold_text = match.group(2)
        if bold_text:
            segments.append((bold_text, True))

        last_end = match.end()

    # Add remaining non-bold text after last match
    if last_end < len(text_html):
        text_after = text_html[last_end:]
        if text_after:
            segments.append((text_after, False))

    # If no matches found, return entire string as non-bold
    if not segments:
        return [(text_html, False)] if text_html else []

    return segments


def resolve_entities(text: str) -> str:
    """Resolve HTML entities to their Unicode characters.

    Handles:
    - Named entities: &ndash;, &mdash;, &amp;, &nbsp;, etc.
    - Numeric entities: &#8211; (decimal), &#x2013; (hex)

    Args:
        text: String containing HTML entities.

    Returns:
        String with all entities resolved to Unicode characters.
    """
    # Replace named entities
    for entity, char in HTML_ENTITIES.items():
        text = text.replace(entity, char)

    # Replace decimal numeric entities &#NNN;
    def replace_decimal_entity(match):
        code = int(match.group(1))
        try:
            return chr(code)
        except (ValueError, OverflowError):
            return match.group(0)  # Return original if invalid

    text = re.sub(r'&#(\d+);', replace_decimal_entity, text)

    # Replace hex numeric entities &#xHHHH;
    def replace_hex_entity(match):
        code = int(match.group(1), 16)
        try:
            return chr(code)
        except (ValueError, OverflowError):
            return match.group(0)  # Return original if invalid

    text = re.sub(r'&#x([0-9a-fA-F]+);', replace_hex_entity, text)

    return text
