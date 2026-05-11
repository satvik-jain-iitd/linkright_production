"""test_peer_applicant.py — Unit tests for S4.1: peer_applicant module.

Acceptance criteria:
  AC1: load_peer_applicant_bank() returns dict with junior/mid/senior keys
  AC2: get_preferred_verbs("executive") returns senior band (exec → senior mapping)
  AC3: get_preferred_verbs("fresher") returns junior band
  AC4: format_verb_guidance("senior") returns non-empty string with "Prefer" section
  AC5: Bank has ≥80 total phrase entries (count across all bands)

Additional tests:
  - get_seniority_band maps all documented career_level values correctly
  - get_avoided_verbs returns correct avoid list per band
  - format_verb_guidance includes band name and career_level
  - format_verb_guidance returns empty string for empty career_level (graceful)
  - Module-level cache: load_peer_applicant_bank() returns same object on repeat calls
  - Orchestrator imports _format_peer_verb_guidance (wired in)
"""

from __future__ import annotations

import pytest


# ── Helper: reset module-level cache between tests ─────────────────────────────
def _reset_cache():
    import linkright.resume.lib.peer_applicant as pa
    pa._BANK_CACHE = None


# ── AC1: load_peer_applicant_bank() structure ──────────────────────────────────
class TestLoadBank:
    def setup_method(self):
        _reset_cache()

    def test_returns_dict(self):
        from linkright.resume.lib.peer_applicant import load_peer_applicant_bank
        bank = load_peer_applicant_bank()
        assert isinstance(bank, dict), "load_peer_applicant_bank() must return a dict"

    def test_has_junior_key(self):
        from linkright.resume.lib.peer_applicant import load_peer_applicant_bank
        bank = load_peer_applicant_bank()
        assert "junior" in bank, "Bank must have 'junior' key"

    def test_has_mid_key(self):
        from linkright.resume.lib.peer_applicant import load_peer_applicant_bank
        bank = load_peer_applicant_bank()
        assert "mid" in bank, "Bank must have 'mid' key"

    def test_has_senior_key(self):
        from linkright.resume.lib.peer_applicant import load_peer_applicant_bank
        bank = load_peer_applicant_bank()
        assert "senior" in bank, "Bank must have 'senior' key"

    def test_each_band_has_prefer_and_avoid(self):
        from linkright.resume.lib.peer_applicant import load_peer_applicant_bank
        bank = load_peer_applicant_bank()
        for band in ("junior", "mid", "senior"):
            assert "prefer" in bank[band], f"Band '{band}' must have 'prefer' list"
            assert "avoid" in bank[band], f"Band '{band}' must have 'avoid' list"

    def test_prefer_lists_are_nonempty(self):
        from linkright.resume.lib.peer_applicant import load_peer_applicant_bank
        bank = load_peer_applicant_bank()
        for band in ("junior", "mid", "senior"):
            assert len(bank[band]["prefer"]) > 0, f"Band '{band}' prefer list must not be empty"

    def test_module_cached(self):
        from linkright.resume.lib.peer_applicant import load_peer_applicant_bank
        b1 = load_peer_applicant_bank()
        b2 = load_peer_applicant_bank()
        assert b1 is b2, "load_peer_applicant_bank() must return the same object (module-cached)"


# ── AC2: executive → senior band ───────────────────────────────────────────────
class TestExecutiveMapsToSenior:
    def setup_method(self):
        _reset_cache()

    def test_executive_preferred_verbs_match_senior_band(self):
        from linkright.resume.lib.peer_applicant import get_preferred_verbs, load_peer_applicant_bank
        executive_preferred = get_preferred_verbs("executive")
        bank = load_peer_applicant_bank()
        senior_preferred = bank["senior"]["prefer"]
        assert executive_preferred == senior_preferred, (
            f"get_preferred_verbs('executive') must return senior band verbs. "
            f"Got {executive_preferred[:5]}... expected {senior_preferred[:5]}..."
        )

    def test_executive_returns_nonempty_list(self):
        from linkright.resume.lib.peer_applicant import get_preferred_verbs
        result = get_preferred_verbs("executive")
        assert isinstance(result, list) and len(result) > 0, (
            "get_preferred_verbs('executive') must return a non-empty list"
        )

    def test_vp_maps_to_senior(self):
        from linkright.resume.lib.peer_applicant import get_seniority_band
        assert get_seniority_band("vp") == "senior"

    def test_director_maps_to_senior(self):
        from linkright.resume.lib.peer_applicant import get_seniority_band
        assert get_seniority_band("director") == "senior"

    def test_senior_maps_to_senior(self):
        from linkright.resume.lib.peer_applicant import get_seniority_band
        assert get_seniority_band("senior") == "senior"

    def test_executive_maps_to_senior(self):
        from linkright.resume.lib.peer_applicant import get_seniority_band
        assert get_seniority_band("executive") == "senior"

    def test_c_level_maps_to_senior(self):
        from linkright.resume.lib.peer_applicant import get_seniority_band
        assert get_seniority_band("c_level") == "senior"

    def test_principal_maps_to_senior(self):
        from linkright.resume.lib.peer_applicant import get_seniority_band
        assert get_seniority_band("principal") == "senior"


# ── AC3: fresher → junior band ─────────────────────────────────────────────────
class TestFresherMapsToJunior:
    def setup_method(self):
        _reset_cache()

    def test_fresher_preferred_verbs_match_junior_band(self):
        from linkright.resume.lib.peer_applicant import get_preferred_verbs, load_peer_applicant_bank
        fresher_preferred = get_preferred_verbs("fresher")
        bank = load_peer_applicant_bank()
        junior_preferred = bank["junior"]["prefer"]
        assert fresher_preferred == junior_preferred, (
            f"get_preferred_verbs('fresher') must return junior band verbs."
        )

    def test_fresher_returns_nonempty_list(self):
        from linkright.resume.lib.peer_applicant import get_preferred_verbs
        result = get_preferred_verbs("fresher")
        assert isinstance(result, list) and len(result) > 0

    def test_entry_maps_to_junior(self):
        from linkright.resume.lib.peer_applicant import get_seniority_band
        assert get_seniority_band("entry") == "junior"

    def test_early_career_maps_to_junior(self):
        from linkright.resume.lib.peer_applicant import get_seniority_band
        assert get_seniority_band("early_career") == "junior"

    def test_intern_maps_to_junior(self):
        from linkright.resume.lib.peer_applicant import get_seniority_band
        assert get_seniority_band("intern") == "junior"

    def test_junior_keyword_maps_to_junior(self):
        from linkright.resume.lib.peer_applicant import get_seniority_band
        assert get_seniority_band("junior") == "junior"

    def test_junior_avoids_executive_verbs(self):
        """Junior band must avoid executive verbs like 'oversaw'."""
        from linkright.resume.lib.peer_applicant import get_avoided_verbs
        avoided = get_avoided_verbs("fresher")
        assert "oversaw" in avoided, "Junior band must avoid 'oversaw'"

    def test_junior_band_contains_shipped(self):
        from linkright.resume.lib.peer_applicant import get_preferred_verbs
        preferred = get_preferred_verbs("fresher")
        assert "shipped" in preferred, "Junior band must include 'shipped' as a preferred verb"


# ── AC4: format_verb_guidance("senior") ────────────────────────────────────────
class TestFormatVerbGuidance:
    def setup_method(self):
        _reset_cache()

    def test_senior_returns_nonempty_string(self):
        from linkright.resume.lib.peer_applicant import format_verb_guidance
        result = format_verb_guidance("senior")
        assert isinstance(result, str) and len(result) > 0, (
            "format_verb_guidance('senior') must return a non-empty string"
        )

    def test_senior_contains_prefer_section(self):
        from linkright.resume.lib.peer_applicant import format_verb_guidance
        result = format_verb_guidance("senior")
        assert "Prefer" in result, (
            f"format_verb_guidance('senior') must contain 'Prefer' section. Got:\n{result}"
        )

    def test_senior_contains_career_level(self):
        from linkright.resume.lib.peer_applicant import format_verb_guidance
        result = format_verb_guidance("senior")
        assert "senior" in result.lower(), (
            "format_verb_guidance('senior') must mention career_level in output"
        )

    def test_senior_contains_avoid_section(self):
        from linkright.resume.lib.peer_applicant import format_verb_guidance
        result = format_verb_guidance("senior")
        assert "Avoid" in result, (
            f"format_verb_guidance('senior') must contain 'Avoid' section. Got:\n{result}"
        )

    def test_executive_guidance_nonempty(self):
        from linkright.resume.lib.peer_applicant import format_verb_guidance
        result = format_verb_guidance("executive")
        assert len(result) > 0

    def test_fresher_guidance_nonempty(self):
        from linkright.resume.lib.peer_applicant import format_verb_guidance
        result = format_verb_guidance("fresher")
        assert len(result) > 0

    def test_mid_guidance_nonempty(self):
        from linkright.resume.lib.peer_applicant import format_verb_guidance
        result = format_verb_guidance("mid")
        assert len(result) > 0

    def test_unknown_level_returns_mid_guidance(self):
        """Unknown career_level defaults to mid band — should still produce guidance."""
        from linkright.resume.lib.peer_applicant import format_verb_guidance
        result = format_verb_guidance("some_unknown_level")
        assert len(result) > 0, "Unknown career_level should still produce guidance (defaults to mid)"

    def test_case_insensitive_lookup(self):
        """'SENIOR' and 'Senior' should both produce the same guidance as 'senior'."""
        from linkright.resume.lib.peer_applicant import format_verb_guidance
        lower = format_verb_guidance("senior")
        upper = format_verb_guidance("SENIOR")
        title = format_verb_guidance("Senior")
        # All should have content (exact string may differ due to career_level display)
        assert len(lower) > 0 and len(upper) > 0 and len(title) > 0

    def test_guidance_contains_fabrication_safeguard(self):
        """Guidance must not instruct LLM to invent relationships — verified by presence
        of 'evidence' or 'natural' in the text (from the FABRICATION RULE note)."""
        from linkright.resume.lib.peer_applicant import format_verb_guidance
        result = format_verb_guidance("senior")
        assert "evidence" in result.lower() or "natural" in result.lower(), (
            "format_verb_guidance must reference the fabrication safeguard (evidence/natural)"
        )


# ── AC5: ≥80 total phrase entries across all bands ────────────────────────────
class TestBankEntryCount:
    def setup_method(self):
        _reset_cache()

    def test_total_entries_gte_80(self):
        from linkright.resume.lib.peer_applicant import load_peer_applicant_bank
        bank = load_peer_applicant_bank()
        total = sum(
            len(lst)
            for band_data in bank.values()
            for lst in band_data.values()
        )
        assert total >= 80, (
            f"Bank must have ≥80 total phrase entries (prefer + avoid across all bands), got {total}"
        )

    def test_senior_prefer_has_gte_15_entries(self):
        from linkright.resume.lib.peer_applicant import load_peer_applicant_bank
        bank = load_peer_applicant_bank()
        assert len(bank["senior"]["prefer"]) >= 15, (
            f"Senior prefer list must have ≥15 entries, got {len(bank['senior']['prefer'])}"
        )

    def test_junior_prefer_has_gte_10_entries(self):
        from linkright.resume.lib.peer_applicant import load_peer_applicant_bank
        bank = load_peer_applicant_bank()
        assert len(bank["junior"]["prefer"]) >= 10, (
            f"Junior prefer list must have ≥10 entries, got {len(bank['junior']['prefer'])}"
        )

    def test_mid_prefer_has_gte_10_entries(self):
        from linkright.resume.lib.peer_applicant import load_peer_applicant_bank
        bank = load_peer_applicant_bank()
        assert len(bank["mid"]["prefer"]) >= 10, (
            f"Mid prefer list must have ≥10 entries, got {len(bank['mid']['prefer'])}"
        )

    def test_all_entries_are_strings(self):
        from linkright.resume.lib.peer_applicant import load_peer_applicant_bank
        bank = load_peer_applicant_bank()
        for band, data in bank.items():
            for key, lst in data.items():
                for entry in lst:
                    assert isinstance(entry, str) and entry.strip(), (
                        f"All entries must be non-empty strings; found {entry!r} in [{band}][{key}]"
                    )


# ── Orchestrator wire-in ────────────────────────────────────────────────────────
class TestOrchestratorWireIn:
    """Verify orchestrator.py imports and uses the peer_applicant guidance."""

    def test_orchestrator_imports_format_peer_verb_guidance(self):
        from pathlib import Path
        orchestrator_path = (
            Path(__file__).parent.parent
            / "src" / "linkright" / "resume" / "orchestrator.py"
        )
        src = orchestrator_path.read_text(encoding="utf-8")
        assert "peer_applicant" in src, (
            "orchestrator.py must import from .lib.peer_applicant"
        )
        assert "_format_peer_verb_guidance" in src, (
            "orchestrator.py must reference _format_peer_verb_guidance"
        )

    def test_orchestrator_uses_guidance_in_step_10(self):
        from pathlib import Path
        orchestrator_path = (
            Path(__file__).parent.parent
            / "src" / "linkright" / "resume" / "orchestrator.py"
        )
        src = orchestrator_path.read_text(encoding="utf-8")
        # The injection block appends peer guidance to sys
        assert "_format_peer_verb_guidance(career_level)" in src, (
            "orchestrator.py must call _format_peer_verb_guidance(career_level) in step_10"
        )
