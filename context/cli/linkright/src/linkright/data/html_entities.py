"""HTML entity map for resolving named and numeric HTML entities.

Extracted from Section 3.5 of SPEC-v2-resume-mcp.
Also handles numeric entities: &#NNN; and &#xHHHH;
"""

HTML_ENTITIES = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&apos;": "'",
    "&ndash;": "\u2013",  # en-dash
    "&mdash;": "\u2014",  # em-dash
    "&nbsp;": " ",
    "&bull;": "\u2022",  # bullet
    "&rarr;": "\u2192",  # right arrow
    "&uarr;": "\u2191",  # up arrow
    "&darr;": "\u2193",  # down arrow
    "&times;": "\u00d7",  # multiplication sign
    "&plusmn;": "\u00b1",  # plus-minus sign
    "&deg;": "\u00b0",  # degree sign
    "&hellip;": "\u2026",  # ellipsis
    "&lsquo;": "\u2018",  # left single quote
    "&rsquo;": "\u2019",  # right single quote
    "&ldquo;": "\u201c",  # left double quote
    "&rdquo;": "\u201d",  # right double quote
}
