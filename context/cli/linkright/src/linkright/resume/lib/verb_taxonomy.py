"""verb_taxonomy.py — S2.3 + S4.2: 2D impact-category × industry verb matrix
                      + career-level vocabulary profiles.

Provides deterministic taxonomy-based verb selection for step_10 bullets.
Selection uses two axes:
  1. Impact category — classified from bullet text (9 categories from FlowCV)
  2. Industry domain — inferred from candidate's job title (same 8 as S2.2)

S4.2 adds career-level vocabulary profiles (fresher / early_career / mid /
senior / executive) with three buckets each (authority / credibility / energy).
These are injected into the step_10 LLM prompt as preference hints.

Public API:
    load_verb_taxonomy() -> dict[str, dict[str, list[str]]]
    classify_impact_category(bullet_text: str) -> str
    get_taxonomy_verb(category: str, industry: str, used_verbs: set[str]) -> str | None
    replace_with_taxonomy_verb(text: str, industry: str, used_verbs: set[str]) -> tuple[str, str | None]
    get_career_level_verb_prefs(career_level: str) -> dict[str, list[str]]
    format_career_vocab_guidance(career_level: str) -> str

S2.3 — 2026-05-11
S4.2 — 2026-05-12
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

# ── Constants ──────────────────────────────────────────────────────────────────

_CATEGORIES = (
    "Achievement",
    "Communication",
    "Initiative",
    "Research",
    "OrgPlanning",
    "Leadership",
    "Managing",
    "ProblemSolving",
    "Interpersonal",
)

_DEFAULT_CATEGORY = "Achievement"
_DEFAULT_INDUSTRY = "tech"

# S4.2 — alias map for career level normalisation.
# Handles common synonyms that the pipeline may emit.
_CAREER_LEVEL_ALIASES: dict[str, str] = {
    "entry":        "early_career",
    "entry_level":  "early_career",
    "junior":       "early_career",
    "intern":       "fresher",
    "fresher":      "fresher",
    "early_career": "early_career",
    "mid":          "mid",
    "mid_level":    "mid",
    "senior":       "senior",
    "sr":           "senior",
    "executive":    "executive",
    "exec":         "executive",
    "vp":           "executive",
    "c_level":      "executive",
    "director":     "senior",
}

_DEFAULT_CAREER_LEVEL = "mid"

# ── Priority-ordered keyword classifier ──────────────────────────────────────
# Each tuple: (keyword_set_as_frozenset_or_str, category)
# Earlier entries take priority. Match on first found keyword.
# All keywords lowercased for comparison.

_CATEGORY_RULES: list[tuple[tuple[str, ...], str]] = [
    # Leadership: led/managed team / oversaw / directed / mentored
    (("led", "managed team", "oversaw", "directed", "mentored", "coached", "built team"), "Leadership"),
    # Managing: managed / coordinated / supervised / ran / owned end-to-end
    (("managed", "coordinated", "supervised", "ran", "owned end-to-end"), "Managing"),
    # Initiative: initiated / proposed / pioneered / introduced
    (("initiated", "proposed", "pioneered", "introduced", "started", "founded", "established"), "Initiative"),
    # Communication: presented / wrote / published / authored
    (("presented", "wrote", "published", "authored", "communicated", "evangelized", "documented"), "Communication"),
    # Research: analyzed / researched / investigated / studied
    (("analyzed", "researched", "investigated", "studied", "evaluated", "assessed", "benchmarked"), "Research"),
    # OrgPlanning: planned / roadmapped / prioritized / organized
    (("planned", "roadmapped", "prioritized", "organized", "structured", "scoped", "scheduled"), "OrgPlanning"),
    # ProblemSolving: fixed / resolved / debugged / diagnosed
    (("fixed", "resolved", "debugged", "diagnosed", "improved", "optimized", "reduced"), "ProblemSolving"),
    # Interpersonal: collaborated / partnered / worked with / aligned
    (("collaborated", "partnered", "worked with", "aligned", "supported"), "Interpersonal"),
    # Achievement: shipped / delivered / launched / built / created
    (("shipped", "delivered", "launched", "built", "created", "implemented", "released", "completed", "hit", "exceeded"), "Achievement"),
]


# ── Module-level caches ────────────────────────────────────────────────────────

_TAXONOMY_CACHE: dict[str, dict[str, list[str]]] | None = None
_CAREER_PREFS_CACHE: dict[str, dict[str, list[str]]] | None = None

_YAML_PATH = Path(__file__).parent.parent / "data" / "verb_taxonomy.yaml"

# Top-level YAML key that holds the career-level section.
_CAREER_PREFS_KEY = "career_level_preferences"


# ── Internal helpers ───────────────────────────────────────────────────────────

def _load_raw_yaml() -> dict:
    """Read YAML from disk (uncached). Raises FileNotFoundError if missing."""
    with open(_YAML_PATH, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"verb_taxonomy.yaml must be a YAML mapping, got {type(data)}")
    return data


# ── Public API ─────────────────────────────────────────────────────────────────

def load_verb_taxonomy() -> dict[str, dict[str, list[str]]]:
    """Load the verb taxonomy YAML, module-cached.

    Returns a nested dict: category → industry → list[str] of past-tense verbs.
    The ``career_level_preferences`` top-level key is excluded from the returned
    dict (it has a different structure and is accessed via
    ``get_career_level_verb_prefs`` instead).

    Raises FileNotFoundError if the YAML is missing (never silently returns empty).
    """
    global _TAXONOMY_CACHE
    if _TAXONOMY_CACHE is None:
        data = _load_raw_yaml()
        _TAXONOMY_CACHE = {
            cat: {ind: list(verbs) for ind, verbs in ind_map.items()}
            for cat, ind_map in data.items()
            if cat != _CAREER_PREFS_KEY  # S4.2: skip career-level section
        }
    return _TAXONOMY_CACHE


def get_career_level_verb_prefs(career_level: str) -> dict[str, list[str]]:
    """Return verb preference buckets for the given career level.

    Parameters
    ----------
    career_level:
        Career level string as emitted by the pipeline (e.g. ``"mid"``,
        ``"senior"``, ``"entry"``, ``"fresher"``).  Aliases such as
        ``"entry"`` and ``"entry_level"`` are mapped to ``"early_career"``.
        Unknown values fall back to ``"mid"``.

    Returns
    -------
    dict with three keys:
        ``authority``   — verbs that signal scope / governance / executive presence
        ``credibility`` — verbs that signal proven impact and measurable delivery
        ``energy``      — verbs that signal hustle, execution, and hands-on building

    Each value is a list of Title Case past-tense verb strings (may be empty
    list for that level, e.g. ``authority`` for ``"fresher"``).
    """
    global _CAREER_PREFS_CACHE
    if _CAREER_PREFS_CACHE is None:
        data = _load_raw_yaml()
        raw = data.get(_CAREER_PREFS_KEY, {})
        _CAREER_PREFS_CACHE = {
            lvl: {
                "authority":   list(buckets.get("authority") or []),
                "credibility": list(buckets.get("credibility") or []),
                "energy":      list(buckets.get("energy") or []),
            }
            for lvl, buckets in raw.items()
        }

    normalised = _CAREER_LEVEL_ALIASES.get((career_level or "").strip().lower(), _DEFAULT_CAREER_LEVEL)
    return _CAREER_PREFS_CACHE.get(
        normalised,
        {"authority": [], "credibility": [], "energy": []},
    )


def format_career_vocab_guidance(career_level: str) -> str:
    """Format a verb-preference hint for injection into an LLM prompt.

    Produces a short paragraph that the LLM can use to calibrate verb tone
    for the candidate's seniority level.  Empty buckets are omitted from the
    output so the prompt stays concise.

    Parameters
    ----------
    career_level:
        Same values accepted as ``get_career_level_verb_prefs``.

    Returns
    -------
    Non-empty string, e.g.::

        Career-level verb preferences (career_level=mid):
        - Authority verbs (use freely): Led, Defined, Established, Aligned, Directed
        - Credibility verbs (use for impact): Drove, Optimized, Scaled, Improved, Reduced, Increased
        - Energy verbs (use sparingly): Shipped, Deployed, Launched
    """
    prefs = get_career_level_verb_prefs(career_level)
    normalised = _CAREER_LEVEL_ALIASES.get((career_level or "").strip().lower(), _DEFAULT_CAREER_LEVEL)

    lines = [f"Career-level verb preferences (career_level={normalised}):"]
    if prefs["authority"]:
        lines.append(f"- Authority verbs (use freely): {', '.join(prefs['authority'])}")
    if prefs["credibility"]:
        lines.append(f"- Credibility verbs (use for impact): {', '.join(prefs['credibility'])}")
    if prefs["energy"]:
        lines.append(f"- Energy verbs (use sparingly): {', '.join(prefs['energy'])}")
    if len(lines) == 1:
        # No verbs at all for this level — still return something meaningful
        lines.append("- No verb preference overrides for this level; use judgment.")

    return "\n".join(lines)


def classify_impact_category(bullet_text: str) -> str:
    """Classify a bullet's impact category from its text.

    Uses a priority-ordered keyword match with word boundaries — first match wins.
    Returns one of the 9 category strings or ``"Achievement"`` as default.

    Parameters
    ----------
    bullet_text: Raw bullet text (HTML tags stripped before matching).
    """
    if not bullet_text:
        return _DEFAULT_CATEGORY

    # Strip HTML tags for keyword matching
    clean = re.sub(r"<[^>]+>", " ", bullet_text).lower()

    for keywords, category in _CATEGORY_RULES:
        for kw in keywords:
            # Multi-word phrases use substring match (they are already specific).
            # Single words use word-boundary match to avoid false positives like
            # "led" matching "delivered" or "ran" matching "transparent".
            if " " in kw:
                if kw in clean:
                    return category
            else:
                if re.search(r"\b" + re.escape(kw) + r"\b", clean):
                    return category

    return _DEFAULT_CATEGORY


def get_taxonomy_verb(
    category: str,
    industry: str,
    used_verbs: set[str],
) -> Optional[str]:
    """Return the first unused taxonomy verb for (category, industry).

    Parameters
    ----------
    category:   Impact category (e.g. "Achievement"). Unknown categories return
                None (caller should fall back to S2.2).
    industry:   Industry slug (e.g. "tech"). Unknown slugs fall back to "tech".
    used_verbs: Set of verb strings already used in this resume (case-insensitive
                comparison). NOT mutated here — caller manages the set.

    Returns the first verb from taxonomy[category][industry] not in used_verbs.
    Falls back to "tech" if primary industry list is exhausted.
    Returns None if fully exhausted (caller should fall back to S2.2).
    """
    taxonomy = load_verb_taxonomy()

    cat_map = taxonomy.get(category)
    if cat_map is None:
        return None

    used_lower = {v.lower() for v in used_verbs}

    def _first_unused(verb_list: list[str]) -> Optional[str]:
        for verb in verb_list:
            if verb.lower() not in used_lower:
                return verb
        return None

    # Try primary industry
    ind_key = industry.lower() if industry else _DEFAULT_INDUSTRY
    primary_list = cat_map.get(ind_key, [])
    result = _first_unused(primary_list)
    if result is not None:
        return result

    # Fallback to "tech" if primary exhausted or unknown
    if ind_key != _DEFAULT_INDUSTRY:
        fallback_list = cat_map.get(_DEFAULT_INDUSTRY, [])
        result = _first_unused(fallback_list)
        if result is not None:
            return result

    return None


def replace_with_taxonomy_verb(
    text: str,
    industry: str,
    used_verbs: set[str],
) -> tuple[str, Optional[str]]:
    """Classify bullet's impact category and replace its opening verb.

    This is the S2.3 main entry point for orchestrator.step_10.

    Flow:
      1. Classify impact category from bullet text.
      2. Call get_taxonomy_verb(category, industry, used_verbs).
      3. If taxonomy verb found AND it differs from current opening verb → replace.
      4. Update used_verbs in-place with the new verb.
      5. If taxonomy returns None → return (text, None) so caller can fall back to S2.2.

    Parameters
    ----------
    text:       Raw bullet text (may contain leading HTML tags like ``<b>``).
    industry:   Industry slug for verb lookup.
    used_verbs: Mutable set of verbs already consumed — updated in-place on success.

    Returns
    -------
    (new_text, new_verb) where ``new_verb`` is the verb used (or ``None`` if
    no taxonomy replacement was made).
    """
    if not text:
        return text, None

    category = classify_impact_category(text)
    taxonomy_verb = get_taxonomy_verb(category, industry, used_verbs)

    if taxonomy_verb is None:
        return text, None

    # Extract current opening verb (strip leading HTML)
    clean_start = re.sub(r"^(<[^>]+>)+", "", text).strip()
    current_verb = re.split(r"[\s,;]", clean_start)[0].rstrip(".,;:!?")

    # If taxonomy verb is the same as current opening verb (case-insensitive):
    # mark the verb as used so subsequent bullets don't duplicate it, but return
    # None to signal "no text replacement needed" (bullet already has the right verb).
    if current_verb.lower() == taxonomy_verb.lower():
        used_verbs.add(taxonomy_verb)
        return text, None

    # Replace the opening verb (preserve any leading HTML tags)
    pattern = re.compile(
        r"^((?:<[^>]+>)*\s*)(" + re.escape(current_verb) + r")\b",
        re.IGNORECASE,
    )
    new_text, n_subs = pattern.subn(r"\g<1>" + taxonomy_verb, text, count=1)
    if n_subs == 0:
        # Fallback: simple replacement at start (no HTML prefix)
        new_text = re.sub(
            r"(?i)^" + re.escape(current_verb) + r"\b",
            taxonomy_verb,
            text,
            count=1,
        )
        if new_text == text:
            # Could not replace — return unchanged
            return text, None

    used_verbs.add(taxonomy_verb)
    return new_text, taxonomy_verb
