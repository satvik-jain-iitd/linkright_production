"""Synonym bank for width optimization.

Contains word replacements with delta widths (in digit character-units).
Positive delta = expansion, negative delta = compression.

Extracted from Section 3.4 of SPEC-v2-resume-mcp.
"""

SYNONYM_BANK = {
    "expand": [
        # (original, replacement, delta_digit_units)
        ("led", "directed", 3.5),
        ("cut", "reduced", 2.3),
        ("ran", "managed", 2.8),
        ("built", "developed", 3.1),
        ("set", "established", 5.8),
        ("got", "acquired", 3.9),
        ("for", "enabling", 3.9),
        ("via", "through", 2.1),
        ("by", "through", 3.1),
        ("use", "utilize", 2.8),
        ("big", "significant", 5.2),
        ("key", "critical", 2.9),
        ("new", "innovative", 4.8),
        ("top", "premier", 2.6),
        ("fix", "remediate", 4.1),
        ("own", "spearhead", 4.8),
        ("aid", "facilitate", 4.5),
        ("drop", "reduction", 3.2),
        ("make", "develop", 2.4),
        ("grow", "accelerate", 4.2),
    ],
    "trim": [
        ("implementation", "launch", -5.5),
        ("orchestrated", "led", -5.2),
        ("development", "dev work", -3.2),
        ("approximately", "~", -7.0),
        ("across the organization", "org-wide", -6.1),
        ("in collaboration with", "with", -9.5),
        ("was responsible for", "managed", -8.7),
        ("resulting in", "yielding", -1.8),
        ("contributing to", "driving", -3.4),
        ("significant", "key", -5.2),
        ("comprehensive", "full", -6.2),
        ("subsequently", "then", -4.8),
        ("establishing", "setting", -2.8),
        ("transformation", "shift", -6.0),
        ("infrastructure", "systems", -4.8),
        ("demonstrated", "showed", -3.6),
        ("stakeholders", "leaders", -3.2),
        ("cross-functional", "x-func", -4.5),
        ("improvement", "gain", -4.8),
        ("performance", "output", -3.2),
    ],
}
