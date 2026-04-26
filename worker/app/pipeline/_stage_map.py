"""Map fine-grained user-preference stages to coarse job_discoveries.company_stage.

user_preferences.preferred_stages: seed | series_a | series_b | series_c | series_d_plus | public | bootstrapped
job_discoveries.company_stage:     startup | growth | enterprise

Without this map, no job ever matches a user's stage preference (different enums).
"""
from __future__ import annotations

PREF_TO_COARSE: dict[str, list[str]] = {
    "seed":           ["startup"],
    "series_a":       ["startup"],
    "series_b":       ["growth"],
    "series_c":       ["growth"],
    "series_d_plus":  ["growth", "enterprise"],
    "public":         ["enterprise"],
    "bootstrapped":   ["startup", "growth"],
}


def coarse_stages_for_user(preferred_stages: list[str] | None) -> set[str]:
    """Translate user's fine-grained stage prefs to coarse stages.
    Empty input or unknown values → empty set (caller should treat as 'no preference')."""
    out: set[str] = set()
    for s in preferred_stages or []:
        if not s:
            continue
        out.update(PREF_TO_COARSE.get(s.strip().lower(), []))
    return out
