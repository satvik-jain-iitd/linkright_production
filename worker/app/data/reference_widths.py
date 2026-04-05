"""Pre-computed Roboto Regular widths for common resume words.

Used in batched Phase 5 prompt so the LLM has a menu of known-width
replacement words. Values are in character-units (digit = 1.000 CU).
Generated from ROBOTO_REGULAR_WEIGHTS in roboto_weights.py.
"""

REFERENCE_WIDTHS: dict[str, float] = {
    # Prepositions & connectors (1-4 CU)
    "in": 1.52, "of": 1.66, "at": 1.73, "or": 1.73, "to": 1.8,
    "by": 2.07, "for": 2.32, "via": 2.45, "per": 2.73,
    "the": 2.8, "and": 3.14, "into": 3.31, "with": 3.63,
    "than": 3.87, "from": 3.92,
    # Short words (2-5 CU)
    "fix": 2.03, "led": 2.52, "aid": 2.52, "set": 2.59,
    "ran": 2.73, "cut": 2.73, "got": 2.87, "use": 2.93,
    "own": 3.53, "plan": 3.59, "goal": 3.59, "core": 3.66,
    "built": 3.76, "data": 3.8, "tools": 4.17, "team": 4.33,
    # Medium words (4-6 CU)
    "profit": 4.56, "client": 4.62, "effort": 4.63, "drove": 4.8,
    "global": 5.1, "senior": 5.1, "within": 5.14, "target": 5.18,
    "digital": 5.2, "scaled": 5.31, "metric": 5.36, "across": 5.38,
    "clients": 5.48, "design": 5.52, "launch": 5.59, "results": 5.62,
    "annual": 5.66, "gained": 5.66, "output": 5.74, "driving": 5.76,
    "impact": 5.77, "weekly": 5.83, "project": 5.9, "growth": 5.98,
    "market": 5.98, "budget": 6.01, "system": 6.05, "models": 6.05,
    # Longer words (6-8 CU)
    "leading": 6.1, "custom": 6.26, "process": 6.45, "support": 6.53,
    "pipeline": 6.55, "yielding": 6.55, "product": 6.6, "utilizing": 6.65,
    "through": 6.74, "projects": 6.76, "revenue": 6.8, "partners": 7.04,
    "complex": 7.12, "platform": 7.16, "enabling": 7.17,
    "initiative": 7.31, "reducing": 7.32, "analytics": 7.48,
    "company": 7.74,
    # Long words (8+ CU)
    "efficiency": 8.0, "achieving": 8.03, "delivering": 8.21,
    "managing": 8.33, "improving": 8.43, "enterprise": 8.49,
    "increasing": 8.55, "leveraging": 8.76, "optimizing": 8.88,
    "framework": 8.96, "operations": 8.97, "generating": 9.11,
    "supporting": 9.12, "developing": 9.24, "automating": 9.78,
    "establishing": 10.07, "streamlining": 10.39,
    "organization": 10.56, "engagement": 10.61,
    "stakeholders": 10.76, "collaboration": 11.0,
    "orchestrating": 11.29, "spearheading": 11.32,
    "infrastructure": 11.46, "demonstrating": 12.37,
    "transformation": 12.54, "comprehensive": 12.77,
    "implementation": 13.27, "cross-functional": 13.39,
}


def format_reference_table() -> str:
    """Format REFERENCE_WIDTHS into a compact string for LLM prompts."""
    items = sorted(REFERENCE_WIDTHS.items(), key=lambda x: x[1])
    parts = [f"{w}={v}" for w, v in items]
    # ~6 per line for readability
    lines = []
    for i in range(0, len(parts), 6):
        lines.append("  ".join(parts[i:i+6]))
    return "\n".join(lines)
