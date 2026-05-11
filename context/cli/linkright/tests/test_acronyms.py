"""Tests for S2.1 — Acronym Expansion Bank.

AC6: Covers:
  (a) known acronym resolves from bank without LLM
  (b) unknown acronym falls back gracefully (returns empty / doesn't crash)
  (c) bank loaded correctly with ≥250 entries
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


# ── AC6-a: known acronym resolves from bank without LLM ──────────────────────

class TestKnownAcronymResolution:
    @pytest.mark.parametrize("acronym,expected_substr", [
        ("API", "Application Programming Interface"),
        ("ML", "Machine Learning"),
        ("AML", "Anti-Money Laundering"),
        ("GDPR", "General Data Protection Regulation"),
        ("KYC", "Know Your Customer"),
        ("SEO", "Search Engine Optimization"),
        ("NPS", "Net Promoter Score"),
        ("ETL", "Extract Transform Load"),
        ("LLM", "Large Language Model"),
        ("RAG", "Retrieval-Augmented Generation"),
        ("K8s", "Kubernetes"),
        ("CI", "Continuous Integration"),
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
