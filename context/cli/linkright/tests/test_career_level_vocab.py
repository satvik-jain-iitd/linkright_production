"""test_career_level_vocab.py — S4.2 acceptance tests for career-level vocabulary profiles.

AC1: get_career_level_verb_prefs("executive") returns dict with non-empty authority list
AC2: get_career_level_verb_prefs("fresher") returns dict with empty/minimal authority list
AC3: format_career_vocab_guidance("mid") returns non-empty string mentioning credibility verbs
AC4: get_career_level_verb_prefs("entry") maps to early_career (alias, doesn't crash)
"""
from __future__ import annotations

import pytest

from linkright.resume.lib.verb_taxonomy import (
    get_career_level_verb_prefs,
    format_career_vocab_guidance,
)


# ── AC1 ─────────────────────────────────────────────────────────────────────────

def test_executive_has_nonempty_authority():
    """AC1: executive level must have authority verbs."""
    prefs = get_career_level_verb_prefs("executive")
    assert isinstance(prefs, dict), "return value must be a dict"
    assert "authority" in prefs, "must have 'authority' key"
    assert "credibility" in prefs, "must have 'credibility' key"
    assert "energy" in prefs, "must have 'energy' key"
    assert len(prefs["authority"]) > 0, (
        "executive authority list must be non-empty; "
        f"got {prefs['authority']}"
    )
    # Spot-check a canonical executive authority verb
    authority_lower = [v.lower() for v in prefs["authority"]]
    assert "oversaw" in authority_lower or "governed" in authority_lower, (
        "expected at least one of 'Oversaw' / 'Governed' for executive authority"
    )


# ── AC2 ─────────────────────────────────────────────────────────────────────────

def test_fresher_has_empty_authority():
    """AC2: fresher level must have empty authority list."""
    prefs = get_career_level_verb_prefs("fresher")
    assert isinstance(prefs, dict), "return value must be a dict"
    assert prefs["authority"] == [], (
        f"fresher authority list must be empty; got {prefs['authority']}"
    )
    # Fresher should still have energy verbs
    assert len(prefs["energy"]) > 0, "fresher should have energy verbs"


# ── AC3 ─────────────────────────────────────────────────────────────────────────

def test_mid_guidance_mentions_credibility():
    """AC3: format_career_vocab_guidance('mid') must be non-empty and mention credibility."""
    guidance = format_career_vocab_guidance("mid")
    assert isinstance(guidance, str), "guidance must be a str"
    assert len(guidance.strip()) > 0, "guidance must be non-empty"
    # Must contain the word "credibility" (case-insensitive)
    assert "credibility" in guidance.lower(), (
        f"guidance for 'mid' must mention credibility verbs; got:\n{guidance}"
    )
    # Must also include a verb from the mid credibility list
    assert any(v in guidance for v in ("Drove", "Optimized", "Scaled", "Improved")), (
        f"guidance for 'mid' must include at least one mid credibility verb; got:\n{guidance}"
    )


# ── AC4 ─────────────────────────────────────────────────────────────────────────

def test_entry_alias_maps_to_early_career():
    """AC4: 'entry' is an alias for early_career — must not crash and must return prefs."""
    prefs = get_career_level_verb_prefs("entry")
    assert isinstance(prefs, dict), "return value must be a dict"
    # 'entry' → early_career, which has empty authority
    assert prefs["authority"] == [], (
        f"entry (→early_career) authority list must be empty; got {prefs['authority']}"
    )
    # early_career should have credibility verbs (e.g. Drove, Owned)
    assert len(prefs["credibility"]) > 0, "entry (→early_career) should have credibility verbs"
    # Also test 'entry_level' alias
    prefs2 = get_career_level_verb_prefs("entry_level")
    assert prefs2 == prefs, "'entry_level' alias must resolve same as 'entry'"


# ── Bonus: structure contract ────────────────────────────────────────────────────

@pytest.mark.parametrize("level", ["fresher", "early_career", "mid", "senior", "executive"])
def test_all_levels_return_three_bucket_dict(level):
    """All canonical career levels must return a dict with all three bucket keys."""
    prefs = get_career_level_verb_prefs(level)
    assert set(prefs.keys()) == {"authority", "credibility", "energy"}, (
        f"level '{level}' prefs must have exactly 3 keys; got {set(prefs.keys())}"
    )
    for bucket, value in prefs.items():
        assert isinstance(value, list), (
            f"level '{level}' bucket '{bucket}' must be a list; got {type(value)}"
        )


def test_unknown_level_falls_back_gracefully():
    """Unknown career level must not crash and must return a valid dict."""
    prefs = get_career_level_verb_prefs("wizard_level")
    assert isinstance(prefs, dict)
    assert set(prefs.keys()) == {"authority", "credibility", "energy"}


def test_format_guidance_executive_no_energy():
    """Executive has empty energy list — guidance must not mention energy verbs."""
    guidance = format_career_vocab_guidance("executive")
    # Executive has no energy verbs, so the energy line should be absent
    assert "energy verbs" not in guidance.lower() or "[]" in guidance or "Energy verbs" not in guidance, (
        "executive guidance should not include an energy verbs line (list is empty)"
    )
    # But authority line must be present
    assert "authority" in guidance.lower(), (
        f"executive guidance must mention authority verbs; got:\n{guidance}"
    )


def test_format_guidance_returns_career_level_in_header():
    """Guidance string must include the canonical career level name."""
    guidance = format_career_vocab_guidance("senior")
    assert "senior" in guidance, (
        f"guidance header must include 'senior'; got:\n{guidance}"
    )
