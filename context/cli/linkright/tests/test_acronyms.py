"""Tests for S2.1 — Acronym Expansion Bank.

AC6: Covers:
  (a) known acronym resolves from bank without LLM
  (b) unknown acronym falls back gracefully (returns empty / doesn't crash)
  (c) bank loaded correctly with ≥250 entries
  (d) [AC4] bank-merge wire-in logic: non-no_expand entries are added,
      no_expand entries are excluded (exercises orchestrator.py:4664-4680)
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fresh_bank():
    """Return a bank dict, bypassing module-level cache for test isolation."""
    from linkright.resume.lib.acronyms import load_acronym_bank
    return load_acronym_bank(_force_reload=True)


# ── AC6-c: bank has ≥250 entries across 12 domains ───────────────────────────

class TestBankSize:
    def test_minimum_250_entries(self):
        bank = _fresh_bank()
        assert len(bank) >= 250, (
            f"Expected ≥250 entries in acronym bank, got {len(bank)}"
        )

    def test_all_12_domains_present(self):
        # Load YAML directly to check domain coverage
        import yaml
        data_file = (
            Path(__file__).parent.parent
            / "src" / "linkright" / "resume" / "data" / "acronyms.yaml"
        )
        raw = yaml.safe_load(data_file.read_text(encoding="utf-8"))
        domains_found = {v["domain"] for v in raw.values() if isinstance(v, dict)}
        required_domains = {
            "tech", "cloud", "devops", "data", "AI",
            "security", "business", "product", "healthcare",
            "marketing", "HR", "finance",
        }
        missing = required_domains - domains_found
        assert not missing, f"Missing domains in acronym bank: {missing}"

    def test_each_domain_has_at_least_5_entries(self):
        import yaml
        data_file = (
            Path(__file__).parent.parent
            / "src" / "linkright" / "resume" / "data" / "acronyms.yaml"
        )
        raw = yaml.safe_load(data_file.read_text(encoding="utf-8"))
        domain_counts: dict[str, int] = {}
        for v in raw.values():
            if isinstance(v, dict):
                d = v.get("domain", "unknown")
                domain_counts[d] = domain_counts.get(d, 0) + 1
        for domain in ["tech", "cloud", "devops", "data", "AI", "security",
                       "business", "product", "healthcare", "marketing", "HR", "finance"]:
            count = domain_counts.get(domain, 0)
            assert count >= 5, f"Domain '{domain}' has only {count} entries (need ≥5)"

    def test_no_dead_entries_in_bank(self):
        """No bank entry should be in _UNIVERSAL_NO_EXPAND_UPPER (they are silently
        suppressed at wire-in time, making those entries useless).  AC1 guard."""
        import yaml
        from linkright.resume.data.no_expand import _UNIVERSAL_NO_EXPAND_UPPER
        data_file = (
            Path(__file__).parent.parent
            / "src" / "linkright" / "resume" / "data" / "acronyms.yaml"
        )
        raw = yaml.safe_load(data_file.read_text(encoding="utf-8"))
        dead = [k for k in raw if k.upper() in _UNIVERSAL_NO_EXPAND_UPPER]
        assert not dead, (
            f"acronyms.yaml contains {len(dead)} entries blocked by _UNIVERSAL_NO_EXPAND_UPPER "
            f"(they are silently dropped at step_14 wire-in): {dead}"
        )


# ── AC6-a: known acronym resolves from bank without LLM ──────────────────────
# NOTE: All acronyms here must NOT be in _UNIVERSAL_NO_EXPAND_UPPER — otherwise
# they are suppressed at step_14 wire-in and this test would be misleading.
# Verified 2026-05-11 against no_expand.py. Blocked acronyms removed:
#   API, ML, LLM, RAG (all in _UNIVERSAL_NO_EXPAND_UPPER → never used by step_14)
# Replaced with: ETL, CAGR, FHIR, DORA — domain acronyms that ARE used at runtime.

class TestKnownAcronymResolution:
    @pytest.mark.parametrize("acronym,expected_substr", [
        ("ETL", "Extract Transform Load"),
        ("AML", "Anti-Money Laundering"),
        ("K8s", "Kubernetes"),
        ("KYC", "Know Your Customer"),
        ("CAGR", "Compound Annual Growth Rate"),
        ("FHIR", "Fast Healthcare Interoperability Resources"),
        ("HRIS", "Human Resources Information System"),
        ("DORA", "DevOps Research and Assessment"),
        ("ABM", "Account-Based Marketing"),
        ("PACS", "Picture Archiving and Communication System"),
        ("GDPR", "General Data Protection Regulation"),
        ("SEO", "Search Engine Optimization"),
        ("NPS", "Net Promoter Score"),
        ("ARR", "Annual Recurring Revenue"),
        ("EHR", "Electronic Health Record"),
        ("ATS", "Applicant Tracking System"),
        ("ROI", "Return on Investment"),
        ("EBITDA", "Earnings Before Interest"),
    ])
    def test_known_acronym_in_bank(self, acronym, expected_substr):
        bank = _fresh_bank()
        assert acronym in bank, f"Expected '{acronym}' in bank but not found"
        expansion = bank[acronym]
        assert expected_substr.lower() in expansion.lower(), (
            f"'{acronym}' expansion '{expansion}' does not contain expected '{expected_substr}'"
        )

    def test_bank_entries_are_strings(self):
        """All values in the bank must be non-empty strings."""
        bank = _fresh_bank()
        for acronym, expansion in bank.items():
            assert isinstance(expansion, str), (
                f"Entry '{acronym}' has non-string expansion: {type(expansion)}"
            )
            assert expansion.strip(), (
                f"Entry '{acronym}' has empty expansion"
            )


# ── AC6-b: unknown acronym falls back gracefully ─────────────────────────────

class TestUnknownAcronymFallback:
    def test_unknown_acronym_not_in_bank(self):
        """An obscure/custom acronym should simply be absent from the bank — no crash."""
        bank = _fresh_bank()
        assert "XYZQ_CUSTOM_99" not in bank

    def test_missing_data_file_returns_empty_dict(self, tmp_path, monkeypatch):
        """If the YAML file is missing, load_acronym_bank must return {} not raise."""
        import linkright.resume.lib.acronyms as _mod
        # Point the module's _DATA_FILE to a non-existent path
        monkeypatch.setattr(_mod, "_DATA_FILE", tmp_path / "nonexistent.yaml")
        result = _mod.load_acronym_bank(_force_reload=True)
        assert result == {}, "Expected empty dict when data file is missing"
        # Restore for other tests
        _mod._CACHE = None

    def test_corrupt_yaml_returns_empty_dict(self, tmp_path, monkeypatch):
        """If the YAML is corrupt, load_acronym_bank must return {} not raise."""
        import linkright.resume.lib.acronyms as _mod
        bad_file = tmp_path / "acronyms.yaml"
        bad_file.write_text("{{not valid yaml:::\n  - broken [", encoding="utf-8")
        monkeypatch.setattr(_mod, "_DATA_FILE", bad_file)
        result = _mod.load_acronym_bank(_force_reload=True)
        assert result == {}, "Expected empty dict when YAML is corrupt"
        _mod._CACHE = None

    def test_load_is_cached(self):
        """Second call without _force_reload returns same object (O(1) cache hit)."""
        from linkright.resume.lib.acronyms import load_acronym_bank
        first = load_acronym_bank()
        second = load_acronym_bank()
        assert first is second, "Expected module-level cache to return same dict object"

    def test_bank_size_helper(self):
        """bank_size() returns the same count as len(load_acronym_bank())."""
        from linkright.resume.lib.acronyms import bank_size, load_acronym_bank
        assert bank_size() == len(load_acronym_bank())


# ── AC4: bank-merge wire-in logic (orchestrator.py:4664-4680) ────────────────
# Exercises _merge_bank_into_expansions() — the extracted helper from the
# inline bank-load block.  Previously zero test coverage.

class TestBankMergeLogic:
    """Integration tests for the bank-merge helper that mirrors the
    orchestrator.py wire-in block at lines 4664-4680.

    Verifies:
    - A bank entry whose key is NOT in _UNIVERSAL_NO_EXPAND_UPPER is merged
      into _LEARNED_EXPANSIONS when not already present.
    - A bank entry whose key IS in _UNIVERSAL_NO_EXPAND_UPPER is excluded
      (matches the `if _bac.upper() not in _UNIVERSAL_NO_EXPAND_UPPER` guard).
    - An entry already present in learned is not overwritten.
    """

    def test_non_no_expand_entry_is_merged(self):
        """ETL is in bank, not in no_expand → must appear in result."""
        from linkright.resume.lib.acronyms import _merge_bank_into_expansions
        from linkright.resume.data.no_expand import _UNIVERSAL_NO_EXPAND_UPPER

        bank = {"ETL": "Extract Transform Load", "AML": "Anti-Money Laundering"}
        learned: dict = {}
        result = _merge_bank_into_expansions(bank, learned, _UNIVERSAL_NO_EXPAND_UPPER)

        assert "ETL" in result, "ETL should be merged (not in no_expand)"
        assert result["ETL"] == "Extract Transform Load"
        assert "AML" in result, "AML should be merged (not in no_expand)"

    def test_no_expand_entry_is_excluded(self):
        """API is in _UNIVERSAL_NO_EXPAND_UPPER → must NOT appear in result."""
        from linkright.resume.lib.acronyms import _merge_bank_into_expansions
        from linkright.resume.data.no_expand import _UNIVERSAL_NO_EXPAND_UPPER

        # API is confirmed in _UNIVERSAL_NO_EXPAND_UPPER
        assert "API" in _UNIVERSAL_NO_EXPAND_UPPER, "Test precondition: API must be in no_expand set"

        bank = {"API": "Application Programming Interface", "ETL": "Extract Transform Load"}
        learned: dict = {}
        result = _merge_bank_into_expansions(bank, learned, _UNIVERSAL_NO_EXPAND_UPPER)

        assert "API" not in result, "API must be excluded (in _UNIVERSAL_NO_EXPAND_UPPER)"
        assert "ETL" in result, "ETL should still be merged"

    def test_existing_learned_entry_not_overwritten(self):
        """Per-run learned expansions have priority over bank."""
        from linkright.resume.lib.acronyms import _merge_bank_into_expansions
        from linkright.resume.data.no_expand import _UNIVERSAL_NO_EXPAND_UPPER

        bank = {"ETL": "Extract Transform Load"}
        learned = {"ETL": "Custom ETL Definition from corpus"}  # already learned
        result = _merge_bank_into_expansions(bank, learned, _UNIVERSAL_NO_EXPAND_UPPER)

        assert result["ETL"] == "Custom ETL Definition from corpus", (
            "Per-run learned entry must not be overwritten by bank"
        )

    def test_merge_returns_modified_learned_dict(self):
        """Helper must return the same dict object (mutates in place) or a new
        dict containing the merged entries — caller must see the additions."""
        from linkright.resume.lib.acronyms import _merge_bank_into_expansions
        from linkright.resume.data.no_expand import _UNIVERSAL_NO_EXPAND_UPPER

        bank = {"CAGR": "Compound Annual Growth Rate"}
        learned: dict = {}
        result = _merge_bank_into_expansions(bank, learned, _UNIVERSAL_NO_EXPAND_UPPER)

        assert "CAGR" in result

    def test_live_bank_loaded_and_merged(self):
        """End-to-end: load real bank, merge with empty learned — result must
        contain at least 250 entries and exclude all no_expand keys."""
        from linkright.resume.lib.acronyms import load_acronym_bank, _merge_bank_into_expansions
        from linkright.resume.data.no_expand import _UNIVERSAL_NO_EXPAND_UPPER

        bank = load_acronym_bank(_force_reload=True)
        learned: dict = {}
        result = _merge_bank_into_expansions(bank, learned, _UNIVERSAL_NO_EXPAND_UPPER)

        assert len(result) >= 250, f"Expected ≥250 merged entries, got {len(result)}"

        # No no_expand entry should have leaked through
        leaked = [k for k in result if k.upper() in _UNIVERSAL_NO_EXPAND_UPPER]
        assert not leaked, f"no_expand entries leaked into merged result: {leaked}"
