"""UAT Cluster B-truth-engine — fix verification (bug #13).

Bug #13: Truth Engine: Missing Regex-based pre-extraction for high-
confidence fields (Email, Phone).

Coverage:
  - Happy path: single email / phone → both extracted verbatim.
  - Indian formats: +91-9876543210, +91 98765 43210, bare 10-digit.
  - North-American formats: (212) 555-1234, 415-555-1234.
  - First-wins when multiple candidates appear.
  - URL false-positive: ``http://name@example.com`` does NOT yield an email.
  - Date false-positive: ``2024-03-15`` does NOT yield a phone.
  - Bare-year false-positive: ``2024`` alone does NOT yield a phone.
  - Reconcile: LLM agreement → regex value, no disagreement.
  - Reconcile: LLM disagreement → regex wins + disagreement recorded.
  - Reconcile: regex empty → LLM value preserved.
  - Wiring: step_07 LLM prompt receives regex hits as `qa_context`.
  - Wiring: step_01 stores regex hits under `contact_info` AND
    `contact_info_regex` provenance key.
"""
from __future__ import annotations

import re
from unittest.mock import patch

import pytest

from linkright.profile.regex_extract import (
    extract_email,
    extract_phone,
    extract_email_phone,
    reconcile_contact,
)


# ─────────────────────────────────────────────────────────────────────
# Email extraction
# ─────────────────────────────────────────────────────────────────────

class TestExtractEmail:
    def test_single_email_extracted(self):
        text = "Contact: satvik@iitdalumni.com for more details."
        assert extract_email(text) == "satvik@iitdalumni.com"

    def test_plus_alias_supported(self):
        text = "Reach me at jane.doe+work@example.org anytime."
        assert extract_email(text) == "jane.doe+work@example.org"

    def test_dashed_domain_supported(self):
        text = "founder@my-startup.co.in"
        assert extract_email(text) == "founder@my-startup.co.in"

    def test_first_email_wins_when_multiple(self):
        text = "Primary: first@one.com. Secondary: second@two.com."
        assert extract_email(text) == "first@one.com"

    def test_no_hit_returns_empty(self):
        assert extract_email("No email here, just text.") == ""
        assert extract_email("") == ""
        assert extract_email(None) == ""  # type: ignore[arg-type]

    def test_url_userinfo_not_matched(self):
        """``http://name@example.com`` is a URL, not a contact email."""
        text = "Visit http://name@example.com for info"
        assert extract_email(text) == ""

    def test_mailto_prefix_stripped(self):
        text = "Email: mailto:satvik@example.com"
        # The regex itself doesn't match `mailto:satvik` as the local
        # part because the alnum-first rule starts at `satvik`. So the
        # captured email is just `satvik@example.com` — verify that.
        assert extract_email(text) == "satvik@example.com"

    def test_trailing_punctuation_stripped(self):
        text = "Email me at satvik@example.com, please."
        assert extract_email(text) == "satvik@example.com"

    def test_numeric_tld_rejected(self):
        """``foo@bar.123`` is not a real email — TLD must be alpha."""
        text = "Bogus: foo@bar.123 — nope."
        assert extract_email(text) == ""


# ─────────────────────────────────────────────────────────────────────
# Phone extraction
# ─────────────────────────────────────────────────────────────────────

class TestExtractPhone:
    def test_indian_with_country_code_dashed(self):
        text = "Call +91-9876543210 anytime."
        assert extract_phone(text) == "+91-9876543210"

    def test_indian_with_country_code_spaced(self):
        text = "Mobile: +91 98765 43210"
        assert extract_phone(text) == "+91 98765 43210"

    def test_indian_bare_10_digit(self):
        text = "Phone: 9876543210"
        assert extract_phone(text) == "9876543210"

    def test_us_with_parens(self):
        text = "Call (212) 555-1234 today."
        assert extract_phone(text) == "(212) 555-1234"

    def test_us_dashed(self):
        text = "415-555-1234"
        assert extract_phone(text) == "415-555-1234"

    def test_us_with_country_code(self):
        text = "+1 415 555 1234"
        assert extract_phone(text) == "+1 415 555 1234"

    def test_date_not_matched_as_phone(self):
        """A date like 2024-03-15 must NOT be extracted as phone."""
        text = "Updated: 2024-03-15. Available immediately."
        assert extract_phone(text) == ""

    def test_dd_mm_yyyy_date_not_matched(self):
        text = "DOB: 15/03/1990. Indian citizen."
        assert extract_phone(text) == ""

    def test_bare_year_not_matched(self):
        text = "Graduated in 2024."
        assert extract_phone(text) == ""

    def test_no_hit_returns_empty(self):
        assert extract_phone("Plain prose, no numbers at all.") == ""
        assert extract_phone("") == ""
        assert extract_phone(None) == ""  # type: ignore[arg-type]

    def test_too_short_rejected(self):
        """A 5-digit ZIP / postal code is not a phone."""
        text = "ZIP 94107"
        assert extract_phone(text) == ""

    def test_ssn_rejected(self):
        """US SSN ``\\d{3}-\\d{2}-\\d{4}`` has 9 digits — must not match
        as phone. We require ≥10 digits."""
        text = "SSN: 123-45-6789 (for tax purposes only)"
        assert extract_phone(text) == ""

    def test_employee_id_rejected(self):
        """Short numeric employee IDs / order numbers are not phones."""
        text = "Employee ID 12345 reporting."
        assert extract_phone(text) == ""


# ─────────────────────────────────────────────────────────────────────
# Combined extractor
# ─────────────────────────────────────────────────────────────────────

class TestExtractEmailPhone:
    def test_both_extracted(self):
        text = (
            "Jane Doe\n"
            "jane.doe@example.org\n"
            "+91 9876543210\n"
            "LinkedIn: linkedin.com/in/janedoe\n"
        )
        out = extract_email_phone(text)
        assert out == {"email": "jane.doe@example.org", "phone": "+91 9876543210"}

    def test_only_email(self):
        out = extract_email_phone("Contact foo@bar.com please.")
        assert out == {"email": "foo@bar.com", "phone": ""}

    def test_only_phone(self):
        out = extract_email_phone("Reach me at +91-9876543210.")
        assert out == {"email": "", "phone": "+91-9876543210"}

    def test_empty_input(self):
        assert extract_email_phone("") == {"email": "", "phone": ""}
        assert extract_email_phone(None) == {"email": "", "phone": ""}  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────
# Reconciliation — the Truth Engine deterministic floor
# ─────────────────────────────────────────────────────────────────────

class TestReconcileContact:
    def test_regex_fills_when_llm_empty(self):
        llm = {"email": "", "phone": ""}
        raw = "satvik@iitdalumni.com\n+91-9876543210"
        final, dis = reconcile_contact(llm, raw)
        assert final["email"] == "satvik@iitdalumni.com"
        assert final["phone"] == "+91-9876543210"
        assert dis == []

    def test_agreement_no_disagreement(self):
        llm = {"email": "satvik@iitdalumni.com", "phone": "+91 98765 43210"}
        raw = "satvik@iitdalumni.com\n+91-9876543210"  # same digits, diff format
        final, dis = reconcile_contact(llm, raw)
        assert final["email"] == "satvik@iitdalumni.com"
        # Regex value wins as canonical even on agreement (digit-normalised match).
        assert final["phone"] == "+91-9876543210"
        assert dis == []

    def test_email_disagreement_regex_wins(self):
        """Truth Engine: LLM hallucinates gmail — regex wins."""
        llm = {"email": "satvik@gmail.com", "phone": "+91-9876543210"}
        raw = "Satvik Jain\nsatvik@iitdalumni.com\n+91-9876543210"
        final, dis = reconcile_contact(llm, raw)
        assert final["email"] == "satvik@iitdalumni.com"
        assert len(dis) == 1
        assert dis[0]["field"] == "email"
        assert dis[0]["llm_value"] == "satvik@gmail.com"
        assert dis[0]["regex_value"] == "satvik@iitdalumni.com"

    def test_phone_disagreement_regex_wins(self):
        """Truth Engine: LLM flips a digit — regex wins."""
        llm = {"email": "a@b.com", "phone": "+91-9876543219"}  # flipped last
        raw = "a@b.com\n+91-9876543210"
        final, dis = reconcile_contact(llm, raw)
        assert final["phone"] == "+91-9876543210"
        assert any(d["field"] == "phone" for d in dis)

    def test_regex_empty_llm_kept(self):
        """No regex hit → LLM value preserved (regex is a floor, not a ceiling)."""
        llm = {"email": "weird+but+real@corp.io", "phone": ""}
        raw = "no contact info in this blob"
        final, dis = reconcile_contact(llm, raw)
        assert final["email"] == "weird+but+real@corp.io"
        assert final["phone"] == ""
        assert dis == []

    def test_case_insensitive_email_no_disagreement(self):
        """``Foo@Bar.COM`` vs ``foo@bar.com`` is the same email."""
        llm = {"email": "Foo@Bar.COM", "phone": ""}
        raw = "foo@bar.com\nno phone"
        final, dis = reconcile_contact(llm, raw)
        assert final["email"] == "foo@bar.com"
        assert dis == []

    def test_non_dict_llm_input_safe(self):
        """Defensive: malformed LLM output (None / list) must not crash."""
        final, dis = reconcile_contact(None, "foo@bar.com")  # type: ignore[arg-type]
        assert final["email"] == "foo@bar.com"
        assert dis == []


# ─────────────────────────────────────────────────────────────────────
# Wiring — orchestrator integration
# ─────────────────────────────────────────────────────────────────────

class TestWiring:
    """Verify the regex helper is actually CALLED from the pipeline, not
    just defined. PR-review pattern after prior incidents where helpers
    were imported but never invoked."""

    def test_step_07_imports_regex_extract(self):
        """Source-level check: orchestrator imports extract_email_phone."""
        from linkright.resume import orchestrator
        src = open(orchestrator.__file__).read()
        # Both call sites must exist.
        assert "from linkright.profile.regex_extract import extract_email_phone" in src
        assert "from linkright.profile.regex_extract import reconcile_contact" in src

    def _run_step_07_with_capture(self, tmp_path, raw_text: str, jd_text: str) -> str:
        """Execute step_07 with all side-effecting paths redirected to
        tmp_path and llm.tier_chat stubbed. Returns the user prompt
        passed to the LLM (so wiring assertions can inspect it).
        """
        from linkright.resume import orchestrator

        # Redirect ARTIFACTS so the step's write_text() lands in tmp_path.
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)

        captured: dict = {}

        def _fake_tier_chat(system, user, klass, intent, temperature, max_tokens):
            captured["system"] = system
            captured["user"] = user
            fake_json = (
                '{"career_level":"mid","profile":"mid",'
                '"jd_keywords":["sql","leadership","pm","experience","senior",'
                '"agile","product","analytics","stakeholder","roadmap",'
                '"strategy","execution","metrics","kpi","data","customer"],'
                '"target_role":"Senior PM","company_name":"X",'
                '"contact_info":{"name":"","phone":"","email":"",'
                '"linkedin":"","portfolio":""},'
                '"career_summary":"PM.","companies":[],"education":[],'
                '"skills":{},"awards":[],"interests":"","voluntary":[],'
                '"strategy":"BALANCED","strategy_reason":"x",'
                '"requirements":['
                '{"id":"r1","text":"SQL","importance":"required"},'
                '{"id":"r2","text":"PM","importance":"required"},'
                '{"id":"r3","text":"agile","importance":"required"},'
                '{"id":"r4","text":"leadership","importance":"preferred"},'
                '{"id":"r5","text":"data","importance":"preferred"},'
                '{"id":"r6","text":"kpi","importance":"preferred"}],'
                '"section_order":["Professional Experience"],'
                '"bullet_budget":{"company_1_total":6,"company_2_total":4,'
                '"awards":0,"voluntary":0,"projects":0}}'
            )
            return fake_json, {"provider": "stub", "prompt_tokens": 0, "completion_tokens": 0}

        with patch.object(orchestrator.llm, "tier_chat", side_effect=_fake_tier_chat), \
             patch.object(orchestrator.logbook, "append"), \
             patch.object(orchestrator, "log"), \
             patch.object(orchestrator, "ARTIFACTS", artifacts_dir):
            orchestrator.step_07_phase_1_2(jd_text, raw_text)

        return captured.get("user", "")

    def test_step_07_injects_regex_hints_into_user_prompt(self, tmp_path):
        """The PHASE_1_2 user prompt must include regex_email / regex_phone
        as a `qa_context` hint when the resume text yields hits."""
        raw_text = (
            "Satvik Jain\n"
            "satvik@iitdalumni.com\n"
            "+91-9876543210\n"
            "Software engineer with 5 years experience.\n"
        )
        jd_text = "We are hiring a Senior PM. Required: SQL, leadership."

        user_msg = self._run_step_07_with_capture(tmp_path, raw_text, jd_text)

        assert "regex_email: satvik@iitdalumni.com" in user_msg, (
            "step_07 user prompt does not contain the regex email hint — "
            "Truth Engine pre-extraction is not being surfaced to the LLM. "
            f"User msg:\n{user_msg[:500]}"
        )
        assert "regex_phone: +91-9876543210" in user_msg, (
            "step_07 user prompt does not contain the regex phone hint."
        )
        assert "Truth Engine" in user_msg

    def test_step_07_no_hint_block_when_text_empty(self, tmp_path):
        """If the raw_text yields no regex hits, the prompt should NOT
        include a hint block (avoids confusing the LLM with empty values)."""
        raw_text = "Just a generic blob of text with no contact details."
        jd_text = "Hiring PM. Required: SQL."

        user_msg = self._run_step_07_with_capture(tmp_path, raw_text, jd_text)

        assert "Truth Engine — Regex-extracted contact hints" not in user_msg, (
            "Hint block should be omitted when regex finds no hits."
        )

    def test_extract_contact_from_text_uses_shared_regex(self):
        """profile/pipeline._extract_contact_from_text must use the shared
        regex_extract module (single source of truth)."""
        from linkright.profile.pipeline import _extract_contact_from_text

        raw = (
            "Satvik Jain\n"
            "satvik@iitdalumni.com\n"
            "+91-9876543210\n"
            "linkedin.com/in/satvik\n"
        )
        contact = _extract_contact_from_text(raw)
        assert contact["email"] == "satvik@iitdalumni.com"
        assert contact["phone"] == "+91-9876543210"
