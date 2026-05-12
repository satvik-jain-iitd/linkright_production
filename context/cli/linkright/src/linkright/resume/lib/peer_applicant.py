"""peer_applicant.py — S4.1: peer-vs-applicant language bank.

Calibrates verb tone in step_10 bullets based on candidate seniority level.
Three bands:
  junior  → strong-contributor tone (entry + early_career candidates)
  mid     → driver/owner tone (mid-level individual contributors leading work)
  senior  → peer-to-panel tone (senior + executive, sounds like an equal to hiring panel)

Public API:
    load_peer_applicant_bank() -> dict
    get_seniority_band(career_level: str) -> str
    get_preferred_verbs(career_level: str) -> list[str]
    get_avoided_verbs(career_level: str) -> list[str]
    format_verb_guidance(career_level: str) -> str

S4.1 — 2026-05-12
"""

from __future__ import annotations

from pathlib import Path

import yaml

# ── Constants ──────────────────────────────────────────────────────────────────

_YAML_PATH = Path(__file__).parent.parent / "data" / "peer_applicant_bank.yaml"

# Maps career_level strings → seniority band
# Covers all career_level values used in the pipeline (step_12 / parsed_p12).
_BAND_MAP: dict[str, str] = {
    # junior band
    "fresher": "junior",
    "entry": "junior",
    "early_career": "junior",
    "junior": "junior",
    "intern": "junior",
    # mid band
    "mid": "mid",
    "mid_level": "mid",
    "individual_contributor": "mid",
    "ic": "mid",
    # senior band
    "senior": "senior",
    "staff": "senior",
    "principal": "senior",
    "lead": "senior",
    "director": "senior",
    "vp": "senior",
    "executive": "senior",
    "c_level": "senior",
    "c-level": "senior",
    "partner": "senior",
    "managing_director": "senior",
}

_DEFAULT_BAND = "mid"

# ── Module-level cache ─────────────────────────────────────────────────────────

_BANK_CACHE: dict | None = None


# ── Public API ─────────────────────────────────────────────────────────────────

def load_peer_applicant_bank() -> dict:
    """Load the peer_applicant_bank YAML, module-cached.

    Returns a dict with keys: ``junior``, ``mid``, ``senior``.
    Each value is a dict with keys ``prefer`` and ``avoid`` (list[str]).
    Raises FileNotFoundError if YAML is missing — never silently returns empty.
    """
    global _BANK_CACHE
    if _BANK_CACHE is None:
        with open(_YAML_PATH, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        if not isinstance(raw, dict) or "bands" not in raw:
            raise ValueError(
                f"peer_applicant_bank.yaml must have a top-level 'bands' key, got: {list(raw.keys()) if isinstance(raw, dict) else type(raw)}"
            )
        _BANK_CACHE = {
            band: {
                "prefer": list(content.get("prefer", [])),
                "avoid": list(content.get("avoid", [])),
            }
            for band, content in raw["bands"].items()
        }
    return _BANK_CACHE


def get_seniority_band(career_level: str) -> str:
    """Map a career_level string to one of: 'junior', 'mid', 'senior'.

    Normalises to lowercase + underscore before lookup. Unknown values default
    to 'mid' (safe middle ground — neither too junior nor too executive).

    Parameters
    ----------
    career_level:
        The ``career_level`` field from ``parsed_p12`` (e.g. "senior", "executive",
        "mid", "fresher"). Case-insensitive. Hyphens normalised to underscores.

    Returns
    -------
    One of ``"junior"``, ``"mid"``, or ``"senior"``.
    """
    if not career_level:
        return _DEFAULT_BAND
    normalised = career_level.strip().lower().replace("-", "_").replace(" ", "_")
    return _BAND_MAP.get(normalised, _DEFAULT_BAND)


def get_preferred_verbs(career_level: str) -> list[str]:
    """Return the preferred-verb list for this career_level's seniority band.

    Parameters
    ----------
    career_level: Raw career_level string (e.g. "senior", "executive", "fresher").

    Returns
    -------
    List of verb/phrase strings to favour in bullet writing. Empty list if bank
    missing data for the resolved band.
    """
    bank = load_peer_applicant_bank()
    band = get_seniority_band(career_level)
    return bank.get(band, {}).get("prefer", [])


def get_avoided_verbs(career_level: str) -> list[str]:
    """Return the avoided-verb list for this career_level's seniority band.

    Parameters
    ----------
    career_level: Raw career_level string.

    Returns
    -------
    List of verb/phrase strings to avoid in bullet writing.
    """
    bank = load_peer_applicant_bank()
    band = get_seniority_band(career_level)
    return bank.get(band, {}).get("avoid", [])


def format_verb_guidance(career_level: str) -> str:
    """Format seniority-based verb guidance for injection into the step_10 LLM prompt.

    Produces a structured paragraph describing preferred and avoided verbs for
    this candidate's seniority level. Designed to be placed AFTER any existing
    taxonomy verb guidance in the PHASE_4A_VERBOSE_SYSTEM prompt.

    FABRICATION RULE: The guidance instructs the LLM to use these verbs
    *where natural and supported by evidence*. It does NOT authorise inventing
    peer relationships or attributing unearned scope.

    Parameters
    ----------
    career_level: The ``career_level`` from ``parsed_p12`` (e.g. "senior", "mid").

    Returns
    -------
    A non-empty string ready for prompt injection. Returns empty string only if
    both prefer and avoid lists are empty (should not happen with a valid YAML).
    """
    band = get_seniority_band(career_level)
    preferred = get_preferred_verbs(career_level)
    avoided = get_avoided_verbs(career_level)

    if not preferred and not avoided:
        return ""

    tone_desc = {
        "junior": "strong-contributor (entry/early-career): sound like someone who drives and ships things",
        "mid": "driver/owner (mid-level IC): sound like someone who owns and leads work",
        "senior": "peer-to-panel (senior/executive): sound like an equal to the hiring panel",
    }.get(band, "mid-level professional")

    lines = [
        f"# Seniority tone guidance (career_level={career_level}, band={band})",
        f"This candidate's tone target: {tone_desc}.",
        "Use these verbs where the evidence naturally supports it — do NOT invent context.",
    ]
    if preferred:
        lines.append(f"Prefer: {', '.join(preferred[:15])}")
    if avoided:
        lines.append(f"Avoid: {', '.join(avoided)}")

    return "\n".join(lines)
