"""Synonym bank for width optimization.

Word replacements with delta widths in digit character-units.
Positive delta = expansion (use when a bullet is too short).
Negative delta = compression (use when a bullet is too long).

Deltas are computed from data/roboto_weights.py (the same table measure_width
uses), so they stay consistent with the measurer. Regenerate via the helper in
tools/build_synonym_bank notes if the font table changes.

House rules: no banned words here. The bank never suggests a replacement that the
content gate (tools/bullet_quality.py) would reject, e.g. utilize or spearhead.
Replacements stay ATS-readable, no aggressive abbreviations like "x-func".
"""

SYNONYM_BANK = {
    "expand": [
        # (original, replacement, delta_digit_units)
        ("use", "deploy", 2.73),
        ("led", "directed", 4.38),
        ("cut", "reduced", 4.07),
        ("ran", "managed", 5.08),
        ("built", "developed", 4.97),
        ("set", "established", 6.96),
        ("got", "obtained", 4.59),
        ("big", "significant", 6.07),
        ("key", "critical", 2.58),
        ("new", "innovative", 5.37),
        ("fix", "resolved", 5.07),
        ("aid", "supported", 6.08),
        ("grew", "accelerated", 5.65),
        ("made", "developed", 4.06),
        ("own", "operated", 4.07),
        ("top", "leading", 3.23),
        ("drop", "reduction", 4.17),
        ("ship", "delivered", 4.24),
        ("plan", "designed", 4.0),
        ("help", "enabled", 3.07),
        ("cut", "decreased", 5.86),
        ("won", "secured", 3.06),
        ("ran", "operated", 4.87),
        ("set up", "established", 4.31),
    ],
    "trim": [
        ("implementation", "rollout", -7.78),
        ("orchestrated", "led", -8.26),
        ("approximately", "about", -7.15),
        ("in collaboration with", "with", -13.55),
        ("was responsible for", "led", -13.63),
        ("resulting in", "yielding", -2.83),
        ("contributing to", "driving", -6.91),
        ("significant", "major", -3.88),
        ("comprehensive", "full", -10.23),
        ("subsequently", "later", -7.42),
        ("establishing", "building", -3.38),
        ("transformation", "overhaul", -5.23),
        ("infrastructure", "systems", -4.56),
        ("demonstrated", "showed", -5.4),
        ("stakeholders", "partners", -3.72),
        ("improvement", "gain", -7.65),
        ("performance", "results", -5.02),
        ("utilization", "use", -5.45),
        ("additional", "extra", -3.96),
        ("prior to", "before", -0.83),
        ("numerous", "many", -3.73),
        ("responsible for", "led", -9.87),
        ("cross-functional", "cross-team", -4.09),
        ("development", "build-out", -3.49),
    ],
}
