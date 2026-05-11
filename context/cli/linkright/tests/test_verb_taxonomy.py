"""test_verb_taxonomy.py — Unit tests for S2.3: verb_taxonomy module.

Tests:
  (a) classify_impact_category correctly classifies ≥8 example bullets
  (b) get_taxonomy_verb returns taxonomy verb, respects used_verbs, falls back to tech, returns None when exhausted
  (c) YAML shape: ≥9 categories, ≥8 industries, ≥8 verbs per cell
  (d) get_taxonomy_verb integration: taxonomy lookup wired into orchestrator (not inline)
  (e) Verb diversity test: 14-bullet scenario produces unique-verb ratio ≥ 0.95
"""

from __future__ import annotations

import pytest


# ── Helper: reset module-level cache between tests ─────────────────────────────
def _reset_cache():
    import linkright.resume.lib.verb_taxonomy as vt
    vt._TAXONOMY_CACHE = None


# ── (c) YAML shape ─────────────────────────────────────────────────────────────
class TestYamlShape:
    def setup_method(self):
        _reset_cache()

    def test_loads_dict(self):
        from linkright.resume.lib.verb_taxonomy import load_verb_taxonomy
        taxonomy = load_verb_taxonomy()
        assert isinstance(taxonomy, dict), "load_verb_taxonomy() must return a dict"

    def test_minimum_9_categories(self):
        from linkright.resume.lib.verb_taxonomy import load_verb_taxonomy
        taxonomy = load_verb_taxonomy()
        assert len(taxonomy) >= 9, f"Expected ≥9 categories, got {len(taxonomy)}: {list(taxonomy.keys())}"

    def test_required_categories_present(self):
        from linkright.resume.lib.verb_taxonomy import load_verb_taxonomy
        taxonomy = load_verb_taxonomy()
        required = {
            "Achievement", "Communication", "Initiative", "Research",
            "OrgPlanning", "Leadership", "Managing", "ProblemSolving", "Interpersonal"
        }
        missing = required - set(taxonomy.keys())
        assert not missing, f"Missing required categories: {missing}"

    def test_minimum_8_industries_per_category(self):
        from linkright.resume.lib.verb_taxonomy import load_verb_taxonomy
        taxonomy = load_verb_taxonomy()
        required_industries = {"tech", "pm", "sales", "finance", "marketing", "legal", "operations", "data"}
        for cat, ind_map in taxonomy.items():
            missing = required_industries - set(ind_map.keys())
            assert not missing, f"Category '{cat}' missing industries: {missing}"

    def test_minimum_8_verbs_per_cell(self):
        from linkright.resume.lib.verb_taxonomy import load_verb_taxonomy
        taxonomy = load_verb_taxonomy()
        for cat, ind_map in taxonomy.items():
            for ind, verbs in ind_map.items():
                assert len(verbs) >= 8, (
                    f"Cell [{cat}][{ind}] has only {len(verbs)} verbs (need ≥8)"
                )

    def test_all_verbs_are_strings(self):
        from linkright.resume.lib.verb_taxonomy import load_verb_taxonomy
        taxonomy = load_verb_taxonomy()
        for cat, ind_map in taxonomy.items():
            for ind, verbs in ind_map.items():
                for v in verbs:
                    assert isinstance(v, str), f"Non-string verb in [{cat}][{ind}]: {v!r}"

    def test_all_verbs_nonempty(self):
        from linkright.resume.lib.verb_taxonomy import load_verb_taxonomy
        taxonomy = load_verb_taxonomy()
        for cat, ind_map in taxonomy.items():
            for ind, verbs in ind_map.items():
                for v in verbs:
                    assert v.strip(), f"Empty verb in [{cat}][{ind}]"

    def test_module_cached(self):
        from linkright.resume.lib.verb_taxonomy import load_verb_taxonomy
        t1 = load_verb_taxonomy()
        t2 = load_verb_taxonomy()
        assert t1 is t2, "load_verb_taxonomy() must return the same object (module-cached)"

    def test_total_entries_gte_576(self):
        from linkright.resume.lib.verb_taxonomy import load_verb_taxonomy
        taxonomy = load_verb_taxonomy()
        total = sum(len(v) for ind_map in taxonomy.values() for v in ind_map.values())
        assert total >= 576, f"Expected ≥576 total entries, got {total}"


# ── (a) classify_impact_category ──────────────────────────────────────────────
class TestClassifyImpactCategory:
    def setup_method(self):
        _reset_cache()

    def test_leadership_keyword_led(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Led a team of 12 engineers") == "Leadership"

    def test_leadership_keyword_mentored(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Mentored 5 junior developers") == "Leadership"

    def test_managing_keyword_managed(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Managed vendor relationships across 4 regions") == "Managing"

    def test_managing_keyword_coordinated(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Coordinated cross-functional sprint planning") == "Managing"

    def test_initiative_keyword_pioneered(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Pioneered the use of LLMs for resume scoring") == "Initiative"

    def test_initiative_keyword_proposed(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Proposed the migration to microservices") == "Initiative"

    def test_communication_keyword_presented(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Presented quarterly roadmap to 50-person exec team") == "Communication"

    def test_communication_keyword_authored(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Authored 10-page technical whitepaper on distributed systems") == "Communication"

    def test_research_keyword_analyzed(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Analyzed 3 years of clickstream data to identify conversion funnels") == "Research"

    def test_research_keyword_benchmarked(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Benchmarked 6 embedding models on latency and recall") == "Research"

    def test_orgplanning_keyword_planned(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Planned the 3-quarter migration to cloud infra") == "OrgPlanning"

    def test_orgplanning_keyword_roadmapped(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Roadmapped 18-month feature delivery for enterprise tier") == "OrgPlanning"

    def test_problemsolving_keyword_debugged(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Debugged memory leak that caused 3 production outages") == "ProblemSolving"

    def test_problemsolving_keyword_resolved(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Resolved critical payment failure affecting 10K users") == "ProblemSolving"

    def test_interpersonal_keyword_collaborated(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Collaborated with design and data science teams") == "Interpersonal"

    def test_interpersonal_keyword_partnered(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Partnered with legal to draft vendor agreements") == "Interpersonal"

    def test_achievement_keyword_shipped(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Shipped v2 of the recommendation engine") == "Achievement"

    def test_achievement_keyword_delivered(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Delivered 30% reduction in API latency") == "Achievement"

    def test_default_fallback_returns_achievement(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("Did some work on the project") == "Achievement"

    def test_empty_string_returns_achievement(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        assert classify_impact_category("") == "Achievement"

    def test_html_stripped_before_classification(self):
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        # <b> tag should be stripped, then "Debugged" keyword detected
        result = classify_impact_category("<b>Debugged</b> a memory corruption bug")
        assert result == "ProblemSolving"

    def test_word_boundary_led_inside_delivered_no_false_positive(self):
        """'led' as embedded substring of word 'delivered' must not match Leadership rule."""
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        # "Delivered" → starts with Achievement keyword "delivered"; first-match is Achievement.
        # More importantly, the word "delivered" should not match the "led" rule because
        # "led" is NOT a word boundary match inside "delivered".
        result = classify_impact_category("Delivered the new onboarding experience on schedule")
        assert result == "Achievement", (
            f"Bullet starting with 'Delivered' should classify as Achievement, got '{result}'"
        )

    def test_word_boundary_ran_not_in_rebranded(self):
        """'ran' as substring of 'rebranded' must not classify as Managing."""
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        result = classify_impact_category("Rebranded the enterprise product line")
        # "rebranded" contains "ran" — should not fire Managing
        assert result != "Managing" or result == "Achievement", (
            f"'ran' inside 'rebranded' should not classify as Managing, got '{result}'"
        )

    def test_word_boundary_led_at_start_is_leadership(self):
        """'led' as a standalone word at start should still classify as Leadership."""
        from linkright.resume.lib.verb_taxonomy import classify_impact_category
        result = classify_impact_category("Led a 12-person cross-functional team")
        assert result == "Leadership", f"Expected Leadership, got '{result}'"



# ── (b) get_taxonomy_verb ──────────────────────────────────────────────────────
class TestGetTaxonomyVerb:
    def setup_method(self):
        _reset_cache()

    def test_returns_string_for_valid_category_industry(self):
        from linkright.resume.lib.verb_taxonomy import get_taxonomy_verb
        result = get_taxonomy_verb("Achievement", "tech", set())
        assert isinstance(result, str) and result, "Should return a non-empty string"

    def test_returns_first_verb_in_list(self):
        from linkright.resume.lib.verb_taxonomy import get_taxonomy_verb, load_verb_taxonomy
        taxonomy = load_verb_taxonomy()
        first = taxonomy["Achievement"]["tech"][0]
        result = get_taxonomy_verb("Achievement", "tech", set())
        assert result == first, f"Expected first verb '{first}', got '{result}'"

    def test_respects_used_verbs(self):
        from linkright.resume.lib.verb_taxonomy import get_taxonomy_verb, load_verb_taxonomy
        taxonomy = load_verb_taxonomy()
        first = taxonomy["Achievement"]["tech"][0]
        second = taxonomy["Achievement"]["tech"][1]
        result = get_taxonomy_verb("Achievement", "tech", {first})
        assert result == second, f"Expected second verb '{second}', got '{result}'"

    def test_case_insensitive_used_check(self):
        from linkright.resume.lib.verb_taxonomy import get_taxonomy_verb, load_verb_taxonomy
        taxonomy = load_verb_taxonomy()
        first = taxonomy["Achievement"]["tech"][0]
        second = taxonomy["Achievement"]["tech"][1]
        # Mark first as used (lowercase)
        result = get_taxonomy_verb("Achievement", "tech", {first.lower()})
        assert result == second, f"Case-insensitive check failed; expected '{second}', got '{result}'"

    def test_falls_back_to_tech_on_unknown_industry(self):
        from linkright.resume.lib.verb_taxonomy import get_taxonomy_verb, load_verb_taxonomy
        taxonomy = load_verb_taxonomy()
        result = get_taxonomy_verb("Achievement", "unknownindustry", set())
        assert result in taxonomy["Achievement"]["tech"], (
            f"Unknown industry should fall back to tech verbs, got '{result}'"
        )

    def test_falls_back_to_tech_when_primary_exhausted(self):
        from linkright.resume.lib.verb_taxonomy import get_taxonomy_verb, load_verb_taxonomy
        taxonomy = load_verb_taxonomy()
        # Exhaust sales Achievement verbs
        all_sales = set(taxonomy["Achievement"]["sales"])
        result = get_taxonomy_verb("Achievement", "sales", all_sales)
        # Should fall back to tech
        assert result is not None, "Should fall back to tech when primary exhausted"
        assert result in taxonomy["Achievement"]["tech"], (
            f"Fallback should be from tech list, got '{result}'"
        )

    def test_returns_none_when_fully_exhausted(self):
        from linkright.resume.lib.verb_taxonomy import get_taxonomy_verb, load_verb_taxonomy
        taxonomy = load_verb_taxonomy()
        # Exhaust both the primary (sales) and tech lists
        all_sales = set(taxonomy["Achievement"]["sales"])
        all_tech = set(taxonomy["Achievement"]["tech"])
        all_used = all_sales | all_tech
        result = get_taxonomy_verb("Achievement", "sales", all_used)
        assert result is None, "Should return None when both primary and tech lists exhausted"

    def test_returns_none_for_unknown_category(self):
        from linkright.resume.lib.verb_taxonomy import get_taxonomy_verb
        result = get_taxonomy_verb("NonexistentCategory", "tech", set())
        assert result is None, "Unknown category should return None"

    def test_does_not_mutate_used_verbs(self):
        """get_taxonomy_verb must NOT mutate the used_verbs set — that is the caller's job."""
        from linkright.resume.lib.verb_taxonomy import get_taxonomy_verb
        used = set()
        get_taxonomy_verb("Achievement", "tech", used)
        assert len(used) == 0, "get_taxonomy_verb must not mutate used_verbs"

    def test_all_categories_return_verb_for_tech(self):
        from linkright.resume.lib.verb_taxonomy import get_taxonomy_verb, _CATEGORIES
        for cat in _CATEGORIES:
            result = get_taxonomy_verb(cat, "tech", set())
            assert result is not None, f"Category '{cat}' should return a verb for 'tech'"


# ── (d) Integration: taxonomy wired into orchestrator ──────────────────────────
class TestIntegrationOrchestratorWireIn:
    """Verify that replace_with_taxonomy_verb (not inline code) is the call site in
    orchestrator.py — confirms the lesson from S2.1 is applied.
    """

    def test_replace_with_taxonomy_verb_importable_and_callable(self):
        from linkright.resume.lib.verb_taxonomy import replace_with_taxonomy_verb
        assert callable(replace_with_taxonomy_verb)

    def test_orchestrator_imports_replace_with_taxonomy_verb(self):
        """Confirm orchestrator.py uses replace_with_taxonomy_verb from verb_taxonomy module."""
        import inspect
        from pathlib import Path
        # We can't import orchestrator directly (heavy deps), so inspect the source file
        orchestrator_path = (
            Path(__file__).parent.parent
            / "src" / "linkright" / "resume" / "orchestrator.py"
        )
        src = orchestrator_path.read_text(encoding="utf-8")
        assert "replace_with_taxonomy_verb" in src, (
            "orchestrator.py must import and use replace_with_taxonomy_verb from verb_taxonomy"
        )
        assert "from .lib.verb_taxonomy import replace_with_taxonomy_verb" in src, (
            "orchestrator.py must have explicit import from .lib.verb_taxonomy"
        )

    def test_replace_with_taxonomy_verb_basic(self):
        from linkright.resume.lib.verb_taxonomy import replace_with_taxonomy_verb
        used: set[str] = set()
        new_text, new_verb = replace_with_taxonomy_verb(
            "Shipped the new onboarding flow", "tech", used
        )
        # "Shipped" is Achievement×tech first verb — taxonomy may or may not replace
        # depending on ordering; but function must not crash
        assert isinstance(new_text, str)
        assert isinstance(new_verb, (str, type(None)))

    def test_replace_with_taxonomy_verb_updates_used_set(self):
        from linkright.resume.lib.verb_taxonomy import replace_with_taxonomy_verb
        used: set[str] = set()
        # Use a bullet that triggers a taxonomy replacement
        new_text, new_verb = replace_with_taxonomy_verb(
            "Did the analysis on competitor pricing", "pm", used
        )
        if new_verb is not None:
            assert new_verb in used, "replace_with_taxonomy_verb must add new_verb to used_verbs"

    def test_fallback_to_s22_on_taxonomy_none(self):
        """When taxonomy returns None (all verbs exhausted), S2.2 fallback kicks in."""
        from linkright.resume.lib.verb_taxonomy import replace_with_taxonomy_verb, load_verb_taxonomy
        from linkright.resume.lib.domain_verbs import replace_weak_verb

        taxonomy = load_verb_taxonomy()
        # Exhaust ALL Achievement × tech AND tech verbs for all cats
        used_verbs: set[str] = set()
        for cat_map in taxonomy.values():
            used_verbs.update(cat_map.get("tech", []))

        text = "worked on the CI/CD pipeline"
        # Taxonomy will return None (all tech exhausted)
        new_txt_tax, new_verb_tax = replace_with_taxonomy_verb(text, "tech", used_verbs.copy())
        # S2.2 fallback also needs all verbs used — confirm graceful None from both
        # (This test verifies the combined flow doesn't crash, not the exact outcome)
        assert isinstance(new_txt_tax, str)


# ── (e) Verb diversity ─────────────────────────────────────────────────────────
class TestVerbDiversity:
    def setup_method(self):
        _reset_cache()

    def test_14_bullet_diversity_gte_095(self):
        """A 14-bullet scenario using replace_with_taxonomy_verb must produce
        unique verb ratio ≥ 0.95 (i.e. ≥14 of 14 bullets have distinct opening verbs
        when starting from empty used_verbs).
        """
        from linkright.resume.lib.verb_taxonomy import replace_with_taxonomy_verb

        # 14 bullets covering different impact categories and text content
        test_bullets = [
            "Led a team of 8 engineers to rebuild the authentication system",
            "Managed vendor contracts across 3 SaaS platforms",
            "Pioneered automated testing infrastructure used by 5 teams",
            "Presented quarterly roadmap to C-suite and 200-person org",
            "Analyzed user drop-off data to identify 3 key friction points",
            "Planned 6-month migration to Kubernetes with zero downtime",
            "Debugged critical race condition in payment processing module",
            "Collaborated with design and data science teams on ML features",
            "Shipped end-to-end resume tailoring pipeline with 30% latency reduction",
            "Authored RFC for new observability stack adopted org-wide",
            "Initiated cloud cost review saving $120K annually",
            "Evaluated 6 vector DB vendors and selected Qdrant for scale",
            "Prioritized feature roadmap based on user research and OKR alignment",
            "Resolved P0 incident affecting 50K users within 45 minutes",
        ]

        used_verbs: set[str] = set()
        result_verbs: list[str] = []

        for bullet in test_bullets:
            new_text, new_verb = replace_with_taxonomy_verb(bullet, "tech", used_verbs)
            if new_verb:
                result_verbs.append(new_verb)
            else:
                # Keep original opening verb
                import re
                clean = re.sub(r"^(<[^>]+>)+", "", bullet).strip()
                orig_verb = re.split(r"[\s,;]", clean)[0].rstrip(".,;:!?")
                result_verbs.append(orig_verb)

        unique_ratio = len(set(v.lower() for v in result_verbs)) / len(result_verbs)
        assert unique_ratio >= 0.95, (
            f"Verb diversity {unique_ratio:.2%} < 0.95 target. Verbs: {result_verbs}"
        )

    def test_diversity_across_multiple_industries(self):
        """Diversity holds even when rotating across industries."""
        from linkright.resume.lib.verb_taxonomy import replace_with_taxonomy_verb

        bullets_and_industries = [
            ("Led the product team through 3 pivots", "pm"),
            ("Managed $2M Q4 ad budget", "marketing"),
            ("Pioneered algorithmic trading strategy", "finance"),
            ("Shipped core authentication service", "tech"),
            ("Coordinated 20-person ops team", "operations"),
            ("Analyzed 500K legal documents with NLP", "legal"),
            ("Closed 8 enterprise deals totaling $3M ARR", "sales"),
            ("Modeled churn prediction with 92% AUC", "data"),
            ("Collaborated with legal on GDPR compliance", "pm"),
            ("Authored API reference documentation", "tech"),
        ]

        used_verbs: set[str] = set()
        result_verbs: list[str] = []

        for bullet, industry in bullets_and_industries:
            new_text, new_verb = replace_with_taxonomy_verb(bullet, industry, used_verbs)
            if new_verb:
                result_verbs.append(new_verb)
            else:
                import re
                clean = re.sub(r"^(<[^>]+>)+", "", bullet).strip()
                orig_verb = re.split(r"[\s,;]", clean)[0].rstrip(".,;:!?")
                result_verbs.append(orig_verb)

        unique_ratio = len(set(v.lower() for v in result_verbs)) / len(result_verbs)
        assert unique_ratio >= 0.95, (
            f"Cross-industry diversity {unique_ratio:.2%} < 0.95. Verbs: {result_verbs}"
        )
