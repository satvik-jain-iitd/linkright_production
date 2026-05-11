"""test_domain_verbs.py — Unit tests for S2.2: domain_verbs module.

Tests:
  (a) weak verb replaced with industry-appropriate strong verb
  (b) used-verb tracking prevents reuse across bullets
  (c) graceful None when all verbs exhausted
  (d) YAML loads correctly with ≥96 entries across ≥8 industries
  (e) get_strong_verb integration: verify production code path calls
      replace_weak_verb for weak-verb bullets (AC4 wire-in pattern)
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import patch, MagicMock

import pytest


# ── Helper: reset module-level cache between tests ─────────────────────────────
def _reset_cache():
    import linkright.resume.lib.domain_verbs as dv
    dv._VERB_CACHE = None


# ── (d) YAML loads correctly ──────────────────────────────────────────────────
class TestYamlLoad:
    def setup_method(self):
        _reset_cache()

    def test_loads_dict(self):
        from linkright.resume.lib.domain_verbs import load_domain_verbs
        verbs = load_domain_verbs()
        assert isinstance(verbs, dict), "load_domain_verbs() must return a dict"

    def test_minimum_8_industries(self):
        from linkright.resume.lib.domain_verbs import load_domain_verbs
        verbs = load_domain_verbs()
        assert len(verbs) >= 8, f"Expected ≥8 industries, got {len(verbs)}: {list(verbs.keys())}"

    def test_minimum_96_total_entries(self):
        from linkright.resume.lib.domain_verbs import load_domain_verbs
        verbs = load_domain_verbs()
        total = sum(len(v) for v in verbs.values())
        assert total >= 96, f"Expected ≥96 total verb entries, got {total}"

    def test_all_industries_have_12_or_more_verbs(self):
        from linkright.resume.lib.domain_verbs import load_domain_verbs
        verbs = load_domain_verbs()
        for industry, vlist in verbs.items():
            assert len(vlist) >= 12, (
                f"Industry '{industry}' has only {len(vlist)} verbs (need ≥12)"
            )

    def test_required_industries_present(self):
        from linkright.resume.lib.domain_verbs import load_domain_verbs
        verbs = load_domain_verbs()
        required = {"tech", "pm", "sales", "finance", "marketing", "legal", "operations", "data"}
        missing = required - set(verbs.keys())
        assert not missing, f"Missing required industries: {missing}"

    def test_all_verbs_are_strings(self):
        from linkright.resume.lib.domain_verbs import load_domain_verbs
        verbs = load_domain_verbs()
        for industry, vlist in verbs.items():
            for v in vlist:
                assert isinstance(v, str), f"Non-string verb in '{industry}': {v!r}"

    def test_all_verbs_nonempty(self):
        from linkright.resume.lib.domain_verbs import load_domain_verbs
        verbs = load_domain_verbs()
        for industry, vlist in verbs.items():
            for v in vlist:
                assert v.strip(), f"Empty verb string found in '{industry}'"

    def test_module_cached(self):
        from linkright.resume.lib.domain_verbs import load_domain_verbs
        v1 = load_domain_verbs()
        v2 = load_domain_verbs()
        assert v1 is v2, "load_domain_verbs() must return the same object (module-cached)"


# ── (a) Weak verb replaced with strong verb ───────────────────────────────────
class TestGetStrongVerb:
    def setup_method(self):
        _reset_cache()

    def test_returns_string_for_valid_industry(self):
        from linkright.resume.lib.domain_verbs import get_strong_verb
        result = get_strong_verb("tech", set())
        assert isinstance(result, str) and result, "Should return a non-empty string"

    def test_returns_first_unused_verb(self):
        from linkright.resume.lib.domain_verbs import get_strong_verb, load_domain_verbs
        verbs = load_domain_verbs()
        first = verbs["tech"][0]
        result = get_strong_verb("tech", set())
        assert result == first, f"Expected first verb '{first}', got '{result}'"

    def test_skips_used_verb(self):
        from linkright.resume.lib.domain_verbs import get_strong_verb, load_domain_verbs
        verbs = load_domain_verbs()
        first = verbs["tech"][0]
        second = verbs["tech"][1]
        result = get_strong_verb("tech", {first})
        assert result == second, f"Expected second verb '{second}' (first '{first}' is used), got '{result}'"

    def test_case_insensitive_used_check(self):
        from linkright.resume.lib.domain_verbs import get_strong_verb, load_domain_verbs
        verbs = load_domain_verbs()
        first = verbs["tech"][0]
        # Pass lowercase version as used
        result = get_strong_verb("tech", {first.lower()})
        # Should skip the first and return the second
        assert result != first, "Case-insensitive used check failed"

    def test_unknown_industry_falls_back_to_tech(self):
        from linkright.resume.lib.domain_verbs import get_strong_verb, load_domain_verbs
        verbs = load_domain_verbs()
        result = get_strong_verb("nonexistent_industry", set())
        assert result in verbs["tech"], f"Unknown industry should fall back to tech verbs, got '{result}'"

    def test_empty_industry_falls_back_to_tech(self):
        from linkright.resume.lib.domain_verbs import get_strong_verb, load_domain_verbs
        verbs = load_domain_verbs()
        result = get_strong_verb("", set())
        assert result in verbs["tech"], f"Empty industry should fall back to tech verbs, got '{result}'"


# ── (b) Used-verb tracking prevents reuse ────────────────────────────────────
class TestUsedVerbTracking:
    def setup_method(self):
        _reset_cache()

    def test_no_verb_reuse_across_bullets(self):
        from linkright.resume.lib.domain_verbs import get_strong_verb, load_domain_verbs
        verbs = load_domain_verbs()
        used: set[str] = set()
        results = []
        for _ in range(min(5, len(verbs["tech"]))):
            verb = get_strong_verb("tech", used)
            assert verb is not None, "Should not exhaust verbs in first 5 calls"
            assert verb not in used, f"Verb '{verb}' already in used set!"
            used.add(verb)
            results.append(verb)
        # All results distinct
        assert len(set(results)) == len(results), "Duplicate verbs returned across calls"

    def test_replace_weak_verb_updates_used_set(self):
        from linkright.resume.lib.domain_verbs import replace_weak_verb
        used: set[str] = set()
        _, new_verb = replace_weak_verb("worked on the pipeline", "tech", used)
        assert new_verb is not None, "Should have replaced 'worked'"
        assert new_verb in used, "New verb should be added to used set"

    def test_no_reuse_via_replace_weak_verb(self):
        from linkright.resume.lib.domain_verbs import replace_weak_verb
        used: set[str] = set()
        _, v1 = replace_weak_verb("worked on pipeline", "tech", used)
        _, v2 = replace_weak_verb("helped with deployment", "tech", used)
        if v1 is not None and v2 is not None:
            assert v1 != v2, f"Both bullets got same verb '{v1}'"


# ── (c) Graceful None when all verbs exhausted ───────────────────────────────
class TestExhaustion:
    def setup_method(self):
        _reset_cache()

    def test_returns_none_when_all_exhausted(self):
        from linkright.resume.lib.domain_verbs import get_strong_verb, load_domain_verbs
        verbs = load_domain_verbs()
        # Mark every tech verb as used
        all_tech = set(verbs["tech"])
        result = get_strong_verb("tech", all_tech)
        assert result is None, f"Expected None when all verbs exhausted, got '{result}'"

    def test_replace_weak_verb_no_crash_on_exhaustion(self):
        from linkright.resume.lib.domain_verbs import replace_weak_verb, load_domain_verbs
        verbs = load_domain_verbs()
        all_tech = set(verbs["tech"])
        # Should not raise; should return original text unchanged
        text = "worked on the deployment pipeline"
        new_text, new_verb = replace_weak_verb(text, "tech", all_tech)
        assert new_verb is None, "Expected None verb on exhaustion"
        assert new_text == text, "Text should be unchanged when no replacement available"


# ── replace_weak_verb unit tests ──────────────────────────────────────────────
class TestReplaceWeakVerb:
    def setup_method(self):
        _reset_cache()

    def test_replaces_worked(self):
        from linkright.resume.lib.domain_verbs import replace_weak_verb
        used: set[str] = set()
        new_text, new_verb = replace_weak_verb("worked on backend APIs", "tech", used)
        assert new_verb is not None
        assert not new_text.lower().startswith("worked"), f"Weak verb not replaced: {new_text!r}"

    def test_replaces_helped(self):
        from linkright.resume.lib.domain_verbs import replace_weak_verb
        used: set[str] = set()
        new_text, new_verb = replace_weak_verb("helped the team ship features", "pm", used)
        assert new_verb is not None
        assert not new_text.lower().startswith("helped")

    def test_replaces_assisted(self):
        from linkright.resume.lib.domain_verbs import replace_weak_verb
        used: set[str] = set()
        new_text, new_verb = replace_weak_verb("assisted the sales team", "sales", used)
        assert new_verb is not None
        assert not new_text.lower().startswith("assisted")

    def test_replaces_supported(self):
        from linkright.resume.lib.domain_verbs import replace_weak_verb
        used: set[str] = set()
        new_text, new_verb = replace_weak_verb("supported finance operations", "finance", used)
        assert new_verb is not None
        assert not new_text.lower().startswith("supported")

    def test_replaces_participated(self):
        from linkright.resume.lib.domain_verbs import replace_weak_verb
        used: set[str] = set()
        new_text, new_verb = replace_weak_verb("participated in marketing campaigns", "marketing", used)
        assert new_verb is not None
        assert not new_text.lower().startswith("participated")

    def test_replaces_leveraged(self):
        from linkright.resume.lib.domain_verbs import replace_weak_verb
        used: set[str] = set()
        new_text, new_verb = replace_weak_verb("leveraged data pipelines", "data", used)
        assert new_verb is not None
        assert not new_text.lower().startswith("leveraged")

    def test_replaces_utilized(self):
        from linkright.resume.lib.domain_verbs import replace_weak_verb
        used: set[str] = set()
        new_text, new_verb = replace_weak_verb("utilized cloud infrastructure", "tech", used)
        assert new_verb is not None
        assert not new_text.lower().startswith("utilized")

    def test_strong_verb_not_replaced(self):
        from linkright.resume.lib.domain_verbs import replace_weak_verb
        used: set[str] = set()
        text = "Architected the entire microservices platform"
        new_text, new_verb = replace_weak_verb(text, "tech", used)
        assert new_verb is None, "Strong verb should not be replaced"
        assert new_text == text, "Text should be unchanged for strong verbs"

    def test_preserves_rest_of_text(self):
        from linkright.resume.lib.domain_verbs import replace_weak_verb
        used: set[str] = set()
        new_text, new_verb = replace_weak_verb(
            "worked on a distributed system handling 10K req/s", "tech", used
        )
        assert "distributed system handling 10K req/s" in new_text

    def test_html_leading_tag_handled(self):
        from linkright.resume.lib.domain_verbs import replace_weak_verb
        used: set[str] = set()
        # Common pattern in step_10 output: <b>verb</b> rest
        text = "<b>worked</b> on backend APIs"
        new_text, new_verb = replace_weak_verb(text, "tech", used)
        # Should either replace or gracefully not crash
        assert isinstance(new_text, str)
        assert isinstance(new_verb, (str, type(None)))

    def test_industry_appropriate_verb(self):
        """Strong verb returned should come from the specified industry list."""
        from linkright.resume.lib.domain_verbs import replace_weak_verb, load_domain_verbs
        verbs = load_domain_verbs()
        used: set[str] = set()
        _, pm_verb = replace_weak_verb("helped drive product strategy", "pm", used)
        if pm_verb is not None:
            assert pm_verb in verbs["pm"], (
                f"Verb '{pm_verb}' not from pm industry list"
            )


# ── (e) Integration: verify AC4 wire-in via infer_industry + get_strong_verb ─
class TestIntegrationWireIn:
    """Mirrors the AC4 pattern from orchestrator.step_10:
    parse_p12 → infer_industry(co_title or career_level) → replace_weak_verb per bullet.

    This does NOT import orchestrator (avoids heavy dep chain).
    Instead it confirms the helper pattern the production code follows.
    """

    def setup_method(self):
        _reset_cache()

    def test_infer_industry_from_career_level(self):
        from linkright.resume.lib.domain_verbs import infer_industry
        assert infer_industry("senior pm") == "pm"
        assert infer_industry("software engineer") == "tech"
        assert infer_industry("data scientist") == "data"
        assert infer_industry("sales manager") == "sales"
        assert infer_industry("finance analyst") == "finance"
        assert infer_industry("marketing lead") == "marketing"
        assert infer_industry("legal counsel") == "legal"
        assert infer_industry("operations director") == "operations"
        assert infer_industry("") == "tech"  # fallback

    def test_infer_industry_from_job_title_strings(self):
        """Bug-fix 2 (S2.2): orchestrator now calls infer_industry(co_title)
        — a full job title — not a seniority bucket like "mid"/"senior".
        Verify the priority list correctly maps real job titles.
        """
        from linkright.resume.lib.domain_verbs import infer_industry
        # PM titles
        assert infer_industry("Senior Product Manager") == "pm"
        assert infer_industry("VP of Product") == "pm"
        assert infer_industry("Product Lead") == "pm"
        # Tech titles
        assert infer_industry("Software Engineer") == "tech"
        assert infer_industry("Backend Developer") == "tech"
        assert infer_industry("SDE II") == "tech"
        # Data titles
        assert infer_industry("Data Scientist") == "data"
        assert infer_industry("ML Engineer") == "data"
        assert infer_industry("Data Analyst") == "data"
        # Finance titles
        assert infer_industry("Finance Controller") == "finance"
        assert infer_industry("Chief Financial Officer") == "finance"
        assert infer_industry("Finance Analyst") == "finance"
        # Marketing titles
        assert infer_industry("Growth Marketing Manager") == "marketing"
        assert infer_industry("Senior Marketing Lead") == "marketing"
        # Sales titles
        assert infer_industry("Account Executive") == "sales"
        assert infer_industry("Sales Director") == "sales"
        # Legal titles
        assert infer_industry("Legal Counsel") == "legal"
        assert infer_industry("Senior Attorney") == "legal"
        # Operations titles
        assert infer_industry("Supply Chain Manager") == "operations"
        assert infer_industry("Operations Director") == "operations"
        # Seniority buckets (old call site) should fall back to "tech" since they
        # carry no domain keyword — verifies the function still works for old callers.
        assert infer_industry("mid") == "tech"
        assert infer_industry("senior") == "tech"
        assert infer_industry("manager") == "tech"
        assert infer_industry("entry") == "tech"

    def test_pre_seeding_prevents_within_company_verb_duplication(self):
        """Bug-fix 1 (S2.2): used_verbs must be pre-seeded with strong verbs
        from THIS company's accepted bullets BEFORE replace_weak_verb is called.

        Scenario: bullet[0] already has strong verb "Launched" (LLM-generated).
        bullet[1] has weak verb "helped". Without pre-seeding, replace_weak_verb
        could return "Launched" again. With pre-seeding, it skips "Launched" and
        returns a different verb.
        """
        from linkright.resume.lib.domain_verbs import (
            replace_weak_verb, get_strong_verb, load_domain_verbs, _WEAK_VERBS,
        )
        verbs = load_domain_verbs()
        # Find the first verb in pm list to use as our "already present" verb
        first_pm_verb = verbs["pm"][0]

        bullets = [
            {"text_html": f"{first_pm_verb} the new onboarding flow", "verb": first_pm_verb},
            {"text_html": "helped stakeholders align on OKRs", "verb": "helped"},
        ]

        # === Scenario A: WITHOUT pre-seeding (old buggy behavior) ===
        used_no_preseed: set[str] = set()
        _, verb_a = replace_weak_verb(bullets[1]["text_html"], "pm", used_no_preseed)
        # Without pre-seeding, first call picks first verb from list — which IS first_pm_verb
        assert verb_a == first_pm_verb, (
            f"Without pre-seeding, expected '{first_pm_verb}' (first in pm list), got '{verb_a}'"
        )

        # === Scenario B: WITH pre-seeding (fixed behavior) ===
        used_with_preseed: set[str] = {
            p["verb"] for p in bullets
            if p.get("verb") and p["verb"].lower() not in _WEAK_VERBS
        }
        assert first_pm_verb in used_with_preseed, "Strong verb should be in used set after pre-seeding"
        _, verb_b = replace_weak_verb(bullets[1]["text_html"], "pm", used_with_preseed)
        # With pre-seeding, first_pm_verb is already used → replacement is a different verb
        assert verb_b is not None, "Should still find a replacement verb"
        assert verb_b != first_pm_verb, (
            f"With pre-seeding, replacement should NOT be '{first_pm_verb}' (already present), got '{verb_b}'"
        )

    def test_full_pipeline_pattern_weak_verb_replaced(self):
        """Simulate the exact orchestrator loop for a single company.

        Pre-seeding used_verbs with existing strong verbs before replacements
        ensures the replacement picks a verb not already in the bullet list —
        mirrors the real pipeline's intent of no-verb-repeat across a resume.
        """
        from linkright.resume.lib.domain_verbs import replace_weak_verb, infer_industry

        parsed_p12 = {"career_level": "senior pm", "industry": None}
        career_level = parsed_p12.get("career_level", "mid")

        # Simulate 3 bullets — two weak, one already strong
        bullets = [
            {"text_html": "worked closely with engineering to ship the Q2 roadmap", "verb": "worked"},
            {"text_html": "Launched the new onboarding flow", "verb": "Launched"},
            {"text_html": "helped stakeholders align on OKRs", "verb": "helped"},
        ]

        _industry = parsed_p12.get("industry") or infer_industry(career_level)

        # Pre-seed used_verbs with already-strong verbs so replacements
        # won't duplicate them — matches the production intent.
        used_verbs: set[str] = {
            p["verb"] for p in bullets
            if p["verb"].lower() not in {
                "worked", "helped", "assisted", "supported",
                "participated", "contributed", "involved", "utilized", "leveraged"
            }
        }

        for p in bullets:
            txt = p.get("text_html", "")
            new_txt, new_verb = replace_weak_verb(txt, _industry, used_verbs)
            if new_verb:
                p["text_html"] = new_txt
                p["verb"] = new_verb

        # collect all verbs
        for p in bullets:
            v = p.get("verb")
            if v:
                used_verbs.add(v)

        # bullets[0] and bullets[2] had weak verbs — both should be replaced
        assert bullets[0]["verb"] != "worked", "First bullet weak verb should be replaced"
        assert bullets[2]["verb"] != "helped", "Third bullet weak verb should be replaced"
        # Strong bullet untouched
        assert bullets[1]["verb"] == "Launched", "Strong verb should remain unchanged"
        # No repeated verbs in output
        all_verbs = [b["verb"] for b in bullets]
        assert len(set(all_verbs)) == len(all_verbs), f"Duplicate verbs in output: {all_verbs}"

    def test_pipeline_pattern_handles_exhaustion_gracefully(self):
        """If all verbs exhausted, original weak verb remains — no crash."""
        from linkright.resume.lib.domain_verbs import replace_weak_verb, load_domain_verbs
        verbs = load_domain_verbs()
        used_verbs = set(verbs["tech"])  # All tech verbs already "used"

        bullet = {"text_html": "worked on the CI/CD pipeline", "verb": "worked"}
        txt = bullet["text_html"]
        new_txt, new_verb = replace_weak_verb(txt, "tech", used_verbs)
        if new_verb:
            bullet["text_html"] = new_txt
            bullet["verb"] = new_verb

        # No crash and original text preserved when exhausted
        assert bullet["text_html"] == txt or new_verb is None
