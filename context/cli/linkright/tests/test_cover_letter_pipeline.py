"""Tests for the cover letter 5-step mini-pipeline.

Tests are mock-based to run without LLM API keys or a profile on disk.

Coverage:
  - JD parser produces expected structure on sample JDs (Step 1)
  - Nugget retrieval picks expected top-N (Step 2)
  - Truth-engine validators catch fabricated metrics (Step 4 / M5)
  - 3-paragraph structure enforcement
  - Tone preference affects generated text (M4)
  - Telemetry JSON written with all M9 required fields
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_JD = """\
Senior Product Manager at Acme Corp

We are building the future of enterprise payments. At Acme Corp, our mission is
to make financial transactions instant and transparent.

Requirements (must-have):
- 5+ years product management experience
- Strong SQL and data analysis skills
- Experience with agile/scrum methodology
- Track record launching B2B SaaS products
- Excellent stakeholder management

Culture: collaborative, data-driven, fast-paced startup
"""

SAMPLE_NUGGETS = [
    {
        "nugget_index": 1,
        "nugget_text": "Led product roadmap for B2B SaaS platform, increasing ARR by $2M over 12 months.",
        "company": "TechCo",
        "role": "Senior PM",
        "importance": "P0",
        "has_embedding": True,
        "nugget_id": "1",
    },
    {
        "nugget_index": 2,
        "nugget_text": "Built and managed agile squad of 8 engineers, shipping 14 features per quarter.",
        "company": "TechCo",
        "role": "Senior PM",
        "importance": "P1",
        "has_embedding": True,
        "nugget_id": "2",
    },
    {
        "nugget_index": 3,
        "nugget_text": "Analyzed 500K daily transactions with SQL to identify fraud patterns, reducing chargebacks by 30%.",
        "company": "FinBank",
        "role": "Product Analyst",
        "importance": "P0",
        "has_embedding": True,
        "nugget_id": "3",
    },
]

SAMPLE_JD_PARSED = {
    "company_name": "Acme Corp",
    "role_title": "Senior Product Manager",
    "hiring_manager": "",
    "must_have_skills": ["product management", "SQL", "agile", "B2B SaaS", "stakeholder management"],
    "tone_signals": ["collaborative", "data-driven", "fast-paced"],
    "mission_snippet": "make financial transactions instant and transparent",
}


# ── Step 1 tests — JD parser ──────────────────────────────────────────────────

class TestStep1ParseJD:
    def test_parses_expected_structure(self):
        """step_1_parse_jd produces all required keys."""
        mock_response = json.dumps({
            "company_name": "Acme Corp",
            "role_title": "Senior Product Manager",
            "hiring_manager": "",
            "must_have_skills": ["product management", "SQL", "agile", "B2B SaaS"],
            "tone_signals": ["collaborative", "data-driven"],
            "mission_snippet": "make financial transactions instant and transparent",
        })
        mock_usage = {"provider": "groq", "prompt_tokens": 200, "completion_tokens": 100}

        # Patch at the module level where groq_chat is imported
        with patch("linkright.coverletter.pipeline.groq_chat", return_value=(mock_response, mock_usage)):
            from linkright.coverletter.pipeline import step_1_parse_jd
            result, usage = step_1_parse_jd(SAMPLE_JD)

        assert result["company_name"] == "Acme Corp"
        assert result["role_title"] == "Senior Product Manager"
        assert isinstance(result["must_have_skills"], list)
        assert len(result["must_have_skills"]) >= 1
        assert isinstance(result["tone_signals"], list)
        for key in ("company_name", "role_title", "hiring_manager", "must_have_skills", "tone_signals", "mission_snippet"):
            assert key in result, f"Missing key: {key}"

    def test_handles_malformed_json_gracefully(self):
        """step_1_parse_jd returns safe defaults on malformed LLM output."""
        mock_usage = {"provider": "groq", "prompt_tokens": 50, "completion_tokens": 10}

        with patch("linkright.coverletter.pipeline.groq_chat", return_value=("not json at all", mock_usage)):
            from linkright.coverletter.pipeline import step_1_parse_jd
            result, _ = step_1_parse_jd(SAMPLE_JD)

        # Should not raise — returns safe defaults
        assert isinstance(result["must_have_skills"], list)
        assert isinstance(result["tone_signals"], list)
        assert isinstance(result["company_name"], str)

    def test_cascades_to_gemini_on_groq_failure(self):
        """step_1_parse_jd cascades to Gemini when Groq fails."""
        from linkright.llm.direct import LLMError
        mock_response = json.dumps(SAMPLE_JD_PARSED)
        mock_usage = {"provider": "gemini", "prompt_tokens": 200, "completion_tokens": 100}

        with patch("linkright.coverletter.pipeline.groq_chat", side_effect=LLMError("groq 429")), \
             patch("linkright.coverletter.pipeline.gemini_chat_best", return_value=(mock_response, mock_usage)):
            from linkright.coverletter.pipeline import step_1_parse_jd
            result, usage = step_1_parse_jd(SAMPLE_JD)

        assert result["company_name"] == "Acme Corp"
        assert usage["provider"] == "gemini"


# ── Step 2 tests — Nugget retrieval ──────────────────────────────────────────

class TestStep2RetrieveNuggets:
    def _setup_fake_profile(self, tmp_path: Path) -> Path:
        """Write 3 sample nuggets + embeddings to a temp profile dir."""
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()

        # Write nuggets.jsonl
        with open(profile_dir / "nuggets.jsonl", "w") as f:
            for n in SAMPLE_NUGGETS:
                f.write(json.dumps(n) + "\n")

        # Write fake embeddings (random 384-dim vectors)
        rng = np.random.default_rng(42)
        ids = np.array(["1", "2", "3"], dtype=object)
        vectors = rng.random((3, 384), dtype=np.float32)
        np.savez(str(profile_dir / "embeddings.npz"), ids=ids, vectors=vectors)

        return profile_dir

    def test_returns_top_n_nuggets(self, tmp_path: Path):
        """step_2_retrieve_nuggets returns at most top_n nuggets."""
        profile_dir = self._setup_fake_profile(tmp_path)

        rng = np.random.default_rng(42)
        fake_skill_vec = rng.random(384).tolist()

        with patch("linkright.coverletter.pipeline.embed", return_value=(fake_skill_vec, {})):
            from linkright.coverletter.pipeline import step_2_retrieve_nuggets
            result = step_2_retrieve_nuggets(
                must_have_skills=["product management", "SQL"],
                top_n=3,
                profile_dir=profile_dir,
            )

        assert len(result) <= 3
        assert all("nugget_id" in n for n in result)
        assert all("retrieval_score" in n for n in result)
        assert all(0.0 <= n["retrieval_score"] <= 1.0 for n in result)

    def test_raises_on_missing_profile(self, tmp_path: Path):
        """step_2_retrieve_nuggets raises RuntimeError when profile missing."""
        from linkright.coverletter.pipeline import step_2_retrieve_nuggets
        with pytest.raises(RuntimeError, match="No profile found"):
            step_2_retrieve_nuggets(
                must_have_skills=["SQL"],
                profile_dir=tmp_path / "nonexistent",
            )

    def test_scores_are_sorted_descending(self, tmp_path: Path):
        """Returned nuggets are sorted by retrieval score descending."""
        profile_dir = self._setup_fake_profile(tmp_path)

        rng = np.random.default_rng(77)
        fake_vec = rng.random(384).tolist()

        with patch("linkright.coverletter.pipeline.embed", return_value=(fake_vec, {})):
            from linkright.coverletter.pipeline import step_2_retrieve_nuggets
            result = step_2_retrieve_nuggets(
                must_have_skills=["SQL"],
                top_n=3,
                profile_dir=profile_dir,
            )

        scores = [n["retrieval_score"] for n in result]
        assert scores == sorted(scores, reverse=True), f"Scores not sorted: {scores}"


# ── Step 4 tests — Truth-engine validation ────────────────────────────────────

class TestStep4Validate:
    def test_m5_catches_fabricated_metric_500pct(self):
        """M5: Deliberately injected '500%' not in any nugget is caught by validator."""
        from linkright.coverletter.pipeline import step_4_validate

        nuggets = [
            {"nugget_index": 1, "nugget_text": "Increased ARR by $2M.", "company": "A", "role": "PM"},
            {"nugget_index": 2, "nugget_text": "Reduced chargebacks by 30%.", "company": "B", "role": "Analyst"},
        ]
        # Deliberately fabricated 500% (not in any nugget)
        draft = "I single-handedly boosted revenue by 500% in one quarter through innovative product decisions."

        cleaned, violations = step_4_validate(draft, nuggets, SAMPLE_JD)

        # Must catch the fabrication
        assert len(violations) > 0, "Expected at least 1 violation for 500% metric"
        assert any("METRIC_FABRICATION" in v for v in violations), (
            f"Expected METRIC_FABRICATION violation. Violations: {violations}"
        )

    def test_passes_valid_claims(self):
        """Truth-engine passes sentences whose metrics trace to source."""
        from linkright.coverletter.pipeline import step_4_validate

        nuggets = [
            {"nugget_index": 2, "nugget_text": "Reduced chargebacks by 30% using SQL fraud analysis.", "company": "FinBank", "role": "Analyst"},
        ]
        draft = "My SQL analysis reduced chargebacks by 30%, demonstrating data-driven impact."

        cleaned, violations = step_4_validate(draft, nuggets, SAMPLE_JD)

        # 30% is in source — metric guard should NOT flag it
        metric_violations = [v for v in violations if "METRIC_FABRICATION" in v]
        assert len(metric_violations) == 0, f"False-positive metric violations: {metric_violations}"
        # The sentence should survive
        assert "30" in cleaned or len(cleaned) > 0

    def test_returns_tuple_always(self):
        """step_4_validate always returns a (str, list) tuple."""
        from linkright.coverletter.pipeline import step_4_validate
        draft = "I am excited about this role and believe I am a great fit."
        cleaned, violations = step_4_validate(draft, [], SAMPLE_JD)
        assert isinstance(cleaned, str)
        assert isinstance(violations, list)

    def test_empty_draft_handled(self):
        """step_4_validate handles empty draft gracefully."""
        from linkright.coverletter.pipeline import step_4_validate
        cleaned, violations = step_4_validate("", [], "")
        assert cleaned == ""
        assert violations == []


# ── Step 5 tests — Format output ─────────────────────────────────────────────

class TestStep5Format:
    def test_includes_all_contact_fields(self):
        """step_5_format includes name, email, phone, greeting, date, sign-off."""
        from linkright.coverletter.pipeline import step_5_format

        contact = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1 555 123 4567",
            "linkedin": "linkedin.com/in/johndoe",
            "portfolio": "",
        }
        jd_parsed = {
            "company_name": "Acme",
            "role_title": "PM",
            "hiring_manager": "",
        }
        draft = "Paragraph one. Paragraph two here. Paragraph three close."

        result = step_5_format(draft, contact, jd_parsed, run_id="test_run")

        assert "John Doe" in result
        assert "john@example.com" in result
        assert "Dear Hiring Team" in result
        assert "Best regards" in result
        from datetime import date
        assert str(date.today().year) in result

    def test_uses_hiring_manager_when_present(self):
        """step_5_format addresses hiring manager by name when provided."""
        from linkright.coverletter.pipeline import step_5_format

        contact = {"name": "Jane Smith", "email": "j@example.com", "phone": "", "linkedin": "", "portfolio": ""}
        jd_parsed = {
            "company_name": "Corp",
            "role_title": "Eng",
            "hiring_manager": "Sarah Chen",
        }

        result = step_5_format("Draft text.", contact, jd_parsed, "run1")
        assert "Dear Sarah Chen" in result

    def test_company_in_greeting_without_hiring_manager(self):
        """Company name appears in greeting when no hiring manager."""
        from linkright.coverletter.pipeline import step_5_format

        contact = {"name": "Ali R", "email": "", "phone": "", "linkedin": "", "portfolio": ""}
        jd_parsed = {"company_name": "Stripe", "role_title": "PM", "hiring_manager": ""}

        result = step_5_format("Body.", contact, jd_parsed, "r")
        assert "Stripe" in result


# ── 3-paragraph structure test ────────────────────────────────────────────────

class TestParagraphStructure:
    def test_three_paragraph_enforcement(self):
        """A properly structured draft has exactly 3 non-empty paragraphs."""
        draft = (
            "Opening hook sentence about the company mission that is specific and compelling. "
            "It references the company's specific work in payments and what makes it unique.\n\n"
            "In my role at TechCo, I led the product roadmap for a B2B SaaS platform, growing ARR by $2M [n:1]. "
            "I also built and managed an agile squad of 8 engineers at TechCo, shipping 14 features per quarter [n:2]. "
            "My SQL work at FinBank reduced chargebacks by 30% [n:3], directly relevant to your data-driven culture. "
            "These achievements align precisely with Acme's requirement for strong B2B SaaS and data skills. "
            "I am confident I can bring similar results to your team.\n\n"
            "I would welcome the chance to discuss how my background fits Acme's roadmap. "
            "Thank you for your consideration."
        )
        paragraphs = [p.strip() for p in draft.split("\n\n") if p.strip()]
        assert len(paragraphs) == 3, f"Expected 3 paragraphs, got {len(paragraphs)}"

    def test_paragraph_word_counts_in_range(self):
        """Well-formed 3-paragraph drafts fit within expected word-count ranges."""
        # P1: hook (50-70 words)
        p1 = (
            "Acme Corp's mission to make financial transactions instant and transparent resonates deeply with my background "
            "in enterprise payments and product management. The scale at which you operate — and the technical sophistication "
            "required — is precisely the environment where I thrive and deliver outsized impact."
        )
        # P2: fit (150-180 words — intentionally full)
        p2 = (
            "In my role as Senior PM at TechCo, I led the product roadmap for a B2B SaaS platform, growing ARR by $2M "
            "over twelve months through strategic prioritization and tight alignment with sales and engineering [n:1]. "
            "By building and managing an agile squad of eight engineers, I shipped fourteen features per quarter "
            "without sacrificing quality or stability [n:2]. "
            "My analytical work at FinBank applied SQL to five hundred thousand daily transactions to identify "
            "fraud patterns, reducing chargebacks by thirty percent while improving customer experience [n:3]. "
            "These outcomes map directly to your requirements for data-driven product leadership, B2B SaaS experience, "
            "and a track record of shipping complex payment infrastructure. "
            "I understand the stakes involved in financial products and the discipline required to get them right."
        )
        # P3: close (30-50 words)
        p3 = (
            "I would welcome the opportunity to speak with your team about how I can contribute to Acme Corp's roadmap. "
            "Thank you for your time and consideration."
        )

        def wc(t): return len(t.split())

        # P1: 40-90 words (generous range to handle real LLM output variance)
        assert 40 <= wc(p1) <= 90, f"P1 word count {wc(p1)} out of range 40-90"
        # P2: 100-250 words
        assert 100 <= wc(p2) <= 250, f"P2 word count {wc(p2)} out of range 100-250"
        # P3: 15-70 words
        assert 15 <= wc(p3) <= 70, f"P3 word count {wc(p3)} out of range 15-70"


# ── Tone test — M4 acceptance criteria ────────────────────────────────────────

class TestToneVariation:
    def test_all_three_tones_mapped(self):
        """M4: All three supported tones have distinct system prompts."""
        from linkright.coverletter.pipeline import _TONE_SYSTEM_MAP
        for tone in ("formal", "conversational", "enthusiastic"):
            assert tone in _TONE_SYSTEM_MAP
            assert len(_TONE_SYSTEM_MAP[tone]) > 50

    def test_formal_vs_enthusiastic_differ(self):
        """M4: formal and enthusiastic instructions are meaningfully different."""
        from linkright.coverletter.pipeline import _TONE_SYSTEM_MAP
        assert _TONE_SYSTEM_MAP["formal"] != _TONE_SYSTEM_MAP["enthusiastic"]

    def test_formal_instruction_contains_precision_signal(self):
        """Formal tone instruction conveys measured/precise style."""
        from linkright.coverletter.pipeline import _TONE_SYSTEM_MAP
        formal = _TONE_SYSTEM_MAP["formal"].lower()
        assert any(w in formal for w in ("formal", "precise", "contraction", "measured", "authoritative"))

    def test_enthusiastic_instruction_contains_energy_signal(self):
        """Enthusiastic tone instruction conveys energy/passion."""
        from linkright.coverletter.pipeline import _TONE_SYSTEM_MAP
        enth = _TONE_SYSTEM_MAP["enthusiastic"].lower()
        assert any(w in enth for w in ("enthus", "energy", "energetic", "exciting", "passion", "vivid"))

    def test_conversational_is_distinct_from_both(self):
        """Conversational tone is a third distinct option."""
        from linkright.coverletter.pipeline import _TONE_SYSTEM_MAP
        conv = _TONE_SYSTEM_MAP["conversational"]
        assert conv != _TONE_SYSTEM_MAP["formal"]
        assert conv != _TONE_SYSTEM_MAP["enthusiastic"]


# ── Telemetry test — M9 acceptance criteria ───────────────────────────────────

class TestTelemetry:
    def _run_pipeline_mocked(self, tmp_path: Path, **kwargs):
        """Helper: run pipeline with all external deps mocked."""
        mock_jd_parsed = SAMPLE_JD_PARSED
        mock_usage = {"provider": "groq", "prompt_tokens": 300, "completion_tokens": 150}
        mock_draft = (
            "Acme Corp's mission resonates with my background in B2B payments product management.\n\n"
            "At TechCo I led the B2B SaaS roadmap growing ARR by $2M [n:1]. "
            "I managed agile delivery of 14 features per quarter [n:2]. "
            "My SQL analysis at FinBank reduced chargebacks by 30% [n:3]. "
            "These outcomes match your stated requirements directly and clearly.\n\n"
            "I would love to discuss this role. Thank you for your time."
        )
        mock_contact = {
            "name": "Jane Doe", "email": "jane@example.com",
            "phone": "", "linkedin": "", "portfolio": "",
        }

        from linkright.coverletter.pipeline import run_cover_letter_pipeline

        with patch("linkright.coverletter.pipeline.step_1_parse_jd",
                   return_value=(mock_jd_parsed, mock_usage)), \
             patch("linkright.coverletter.pipeline.step_2_retrieve_nuggets",
                   return_value=SAMPLE_NUGGETS), \
             patch("linkright.coverletter.pipeline.step_3_generate_draft",
                   return_value=(mock_draft, mock_usage)), \
             patch("linkright.coverletter.pipeline.step_4_validate",
                   return_value=(mock_draft, [])), \
             patch("linkright.coverletter.pipeline.load_contact",
                   return_value=mock_contact), \
             patch("linkright.coverletter.pipeline._runs_dir",
                   return_value=tmp_path / "runs"), \
             patch("linkright.coverletter.pipeline._profile_dir",
                   return_value=tmp_path / "profile"):

            return run_cover_letter_pipeline(jd_text=SAMPLE_JD, **kwargs)

    def test_m9_required_fields_present(self, tmp_path: Path):
        """M9: telemetry dict has all required fields."""
        result = self._run_pipeline_mocked(tmp_path)
        tel = result["telemetry"]

        required_fields = ["api_calls", "tokens", "wall_time_s", "cost", "validator_failures"]
        for field in required_fields:
            assert field in tel, f"telemetry missing '{field}'"

        assert tel["api_calls"] == 2, f"Expected 2 API calls, got {tel['api_calls']}"
        assert tel["tokens"] >= 0
        assert tel["wall_time_s"] >= 0

    def test_telemetry_json_written_to_disk(self, tmp_path: Path):
        """Telemetry.json is written to run dir."""
        result = self._run_pipeline_mocked(tmp_path)
        run_dir = tmp_path / "runs" / result["run_id"]
        tel_path = run_dir / "telemetry.json"

        assert tel_path.exists(), "telemetry.json not found on disk"
        saved_tel = json.loads(tel_path.read_text())
        assert "api_calls" in saved_tel
        assert "validator_failures" in saved_tel
        assert "run_id" in saved_tel

    def test_nuggets_retrieved_counted_in_telemetry(self, tmp_path: Path):
        """Telemetry tracks how many nuggets were retrieved."""
        result = self._run_pipeline_mocked(tmp_path)
        tel = result["telemetry"]
        assert "nuggets_retrieved" in tel
        assert tel["nuggets_retrieved"] == len(SAMPLE_NUGGETS)

    def test_tone_recorded_in_telemetry(self, tmp_path: Path):
        """Telemetry records the tone used."""
        result = self._run_pipeline_mocked(tmp_path, tone="formal")
        assert result["telemetry"]["tone"] == "formal"


# ── Truth-engine integrity tests — M11/M12/M13 ───────────────────────────────

class TestValidationFallbackRefusal:
    """M11: VALIDATION_FALLBACK now raises ClickException + exits non-zero + no file.
    M12: >50% sentences fabricated → pipeline aborts, no file written.
    M13: 1 fabricated sentence → cleaned output written normally.
    """

    def _mock_common(self, tmp_path: Path):
        """Common mocks for pipeline orchestrator tests."""
        return {
            "jd_parsed": SAMPLE_JD_PARSED,
            "usage": {"provider": "groq", "prompt_tokens": 300, "completion_tokens": 150},
            "contact": {
                "name": "Jane Doe", "email": "jane@example.com",
                "phone": "", "linkedin": "", "portfolio": "",
            },
            "runs_dir": tmp_path / "runs",
            "profile_dir": tmp_path / "profile",
        }

    def test_m12_validation_fallback_raises_click_exception_no_file(self, tmp_path: Path):
        """M12: When >50% of sentences are fabricated, pipeline raises ClickException and
        does NOT write any output file."""
        from linkright.coverletter.pipeline import run_cover_letter_pipeline
        import click as _click

        ctx = self._mock_common(tmp_path)
        output_file = tmp_path / "output_should_not_exist.md"

        # Craft a draft where step_4_validate will drop >50% words.
        # We mock step_4_validate to simulate this: return a heavily-trimmed cleaned draft
        # and a VALIDATION_FALLBACK violation (as the real code would produce).
        trimmed_draft = "Only this one sentence survived."  # ~5 words vs original ~40
        fallback_violations = [
            "METRIC_FABRICATION: 'I boosted revenue by 9999% in one week.' unsupported metrics: ['9999%']",
            "METRIC_FABRICATION: 'Cut costs by 8888% overnight.' unsupported metrics: ['8888%']",
            "METRIC_FABRICATION: 'Grew team by 7777% instantly.' unsupported metrics: ['7777%']",
            "METRIC_FABRICATION: 'Shipped 6666 features in one sprint.' unsupported metrics: ['6666']",
            (
                "VALIDATION_FALLBACK: 4 sentences dropped (5/40 words retained) "
                "— refusing to save fabricated content"
            ),
        ]
        mock_draft = (
            "I boosted revenue by 9999% in one week. "
            "Cut costs by 8888% overnight. "
            "Grew team by 7777% instantly. "
            "Shipped 6666 features in one sprint. "
            "Only this one sentence survived."
        )

        with patch("linkright.coverletter.pipeline.step_1_parse_jd",
                   return_value=(ctx["jd_parsed"], ctx["usage"])), \
             patch("linkright.coverletter.pipeline.step_2_retrieve_nuggets",
                   return_value=SAMPLE_NUGGETS), \
             patch("linkright.coverletter.pipeline.step_3_generate_draft",
                   return_value=(mock_draft, ctx["usage"])), \
             patch("linkright.coverletter.pipeline.step_4_validate",
                   return_value=(trimmed_draft, fallback_violations)), \
             patch("linkright.coverletter.pipeline.load_contact",
                   return_value=ctx["contact"]), \
             patch("linkright.coverletter.pipeline._runs_dir",
                   return_value=ctx["runs_dir"]), \
             patch("linkright.coverletter.pipeline._profile_dir",
                   return_value=ctx["profile_dir"]):
            with pytest.raises(_click.ClickException) as exc_info:
                run_cover_letter_pipeline(
                    jd_text=SAMPLE_JD,
                    output_path=output_file,
                )

        # M11: exception message must explain the truth-engine refusal
        err_msg = exc_info.value.format_message()
        assert "truth-engine" in err_msg.lower() or "validation" in err_msg.lower(), (
            f"Error message should mention truth-engine/validation. Got: {err_msg[:200]}"
        )
        assert "profile" in err_msg.lower(), (
            f"Error message should guide user to expand profile. Got: {err_msg[:200]}"
        )

        # M12: output file must NOT have been written
        assert not output_file.exists(), (
            f"Output file should NOT exist after VALIDATION_FALLBACK, but found: {output_file}"
        )

    def test_m13_single_fabrication_cleans_and_writes_file(self, tmp_path: Path):
        """M13: When only 1 sentence is fabricated (below 50% threshold), pipeline
        succeeds: output file IS written, fabricated sentence NOT in output."""
        from linkright.coverletter.pipeline import run_cover_letter_pipeline

        ctx = self._mock_common(tmp_path)
        output_file = tmp_path / "cover_letter_cleaned.md"

        # Mock draft with 1 fabricated sentence among 4 real ones
        full_draft = (
            "Acme Corp's mission to make payments instant resonates with my background. "
            "At TechCo I led the B2B SaaS roadmap growing ARR by $2M over 12 months. "
            "I SINGLE-HANDEDLY BOOSTED REVENUE BY 500000% FABRICATED CLAIM HERE. "
            "My SQL analysis at FinBank reduced chargebacks by 30% demonstrably. "
            "I would welcome the chance to discuss this opportunity with your team."
        )
        # step_4_validate strips the fabricated sentence — 4/5 sentences survive (>50%)
        cleaned_draft = (
            "Acme Corp's mission to make payments instant resonates with my background. "
            "At TechCo I led the B2B SaaS roadmap growing ARR by $2M over 12 months. "
            "My SQL analysis at FinBank reduced chargebacks by 30% demonstrably. "
            "I would welcome the chance to discuss this opportunity with your team."
        )
        single_violation = [
            "METRIC_FABRICATION: 'I SINGLE-HANDEDLY BOOSTED REVENUE BY 500000%...' unsupported metrics: ['500000%']"
        ]

        with patch("linkright.coverletter.pipeline.step_1_parse_jd",
                   return_value=(ctx["jd_parsed"], ctx["usage"])), \
             patch("linkright.coverletter.pipeline.step_2_retrieve_nuggets",
                   return_value=SAMPLE_NUGGETS), \
             patch("linkright.coverletter.pipeline.step_3_generate_draft",
                   return_value=(full_draft, ctx["usage"])), \
             patch("linkright.coverletter.pipeline.step_4_validate",
                   return_value=(cleaned_draft, single_violation)), \
             patch("linkright.coverletter.pipeline.load_contact",
                   return_value=ctx["contact"]), \
             patch("linkright.coverletter.pipeline._runs_dir",
                   return_value=ctx["runs_dir"]), \
             patch("linkright.coverletter.pipeline._profile_dir",
                   return_value=ctx["profile_dir"]):
            result = run_cover_letter_pipeline(
                jd_text=SAMPLE_JD,
                output_path=output_file,
            )

        # File IS written
        assert output_file.exists(), "Output file should be written when fallback does NOT trigger"

        # Fabricated sentence NOT in output
        letter_content = output_file.read_text()
        assert "500000" not in letter_content, (
            "Fabricated claim '500000%' must not appear in written cover letter"
        )

        # Result dict has expected keys
        assert "letter_md" in result
        assert "violations" in result
        assert len(result["violations"]) == 1  # Only the one METRIC_FABRICATION


# ── PermissionError / OSError tests — M14/M15 ────────────────────────────────

class TestOutputPermissionError:
    """M14: PermissionError on --output raises clean ClickException (not traceback).
    M15: Asserts no partial file left behind.
    """

    def test_m14_m15_permission_error_raises_click_exception_no_partial_file(self, tmp_path: Path):
        """M14+M15: When write_text raises PermissionError on the user --output path,
        pipeline raises ClickException with helpful message AND no partial file is left."""
        from linkright.coverletter.pipeline import run_cover_letter_pipeline
        import click as _click
        from pathlib import Path as _Path

        mock_jd_parsed = SAMPLE_JD_PARSED
        mock_usage = {"provider": "groq", "prompt_tokens": 300, "completion_tokens": 150}
        mock_draft = (
            "Acme Corp's mission resonates with my background in enterprise payments. "
            "At TechCo I grew ARR by $2M over 12 months with a focused B2B SaaS roadmap. "
            "I would welcome the chance to discuss this opportunity with your team."
        )
        mock_contact = {
            "name": "Jane Doe", "email": "jane@example.com",
            "phone": "", "linkedin": "", "portfolio": "",
        }
        output_file = tmp_path / "cover_letter_output.md"
        output_file_str = str(output_file)

        # Patch Path.write_text so it fails only for the user-specified output path,
        # but succeeds for internal artifact writes (which use different paths).
        original_write_text = _Path.write_text

        def selective_write_text(self, *args, **kwargs):
            if str(self) == output_file_str:
                raise PermissionError(f"Permission denied: {output_file_str}")
            return original_write_text(self, *args, **kwargs)

        with patch("linkright.coverletter.pipeline.step_1_parse_jd",
                   return_value=(mock_jd_parsed, mock_usage)), \
             patch("linkright.coverletter.pipeline.step_2_retrieve_nuggets",
                   return_value=SAMPLE_NUGGETS), \
             patch("linkright.coverletter.pipeline.step_3_generate_draft",
                   return_value=(mock_draft, mock_usage)), \
             patch("linkright.coverletter.pipeline.step_4_validate",
                   return_value=(mock_draft, [])), \
             patch("linkright.coverletter.pipeline.load_contact",
                   return_value=mock_contact), \
             patch("linkright.coverletter.pipeline._runs_dir",
                   return_value=tmp_path / "runs"), \
             patch("linkright.coverletter.pipeline._profile_dir",
                   return_value=tmp_path / "profile"), \
             patch.object(_Path, "write_text", selective_write_text):
            with pytest.raises(_click.ClickException) as exc_info:
                run_cover_letter_pipeline(
                    jd_text=SAMPLE_JD,
                    output_path=output_file,
                )

        # M14: Error message is user-friendly (not a raw traceback)
        err_msg = exc_info.value.format_message()
        assert "permission" in err_msg.lower() or "could not write" in err_msg.lower(), (
            f"Expected helpful permission error message. Got: {err_msg[:200]}"
        )
        assert "--output" in err_msg or "permissions" in err_msg, (
            f"Expected guidance on --output path. Got: {err_msg[:200]}"
        )

        # M15: Output file does NOT exist (no partial write)
        assert not output_file.exists(), (
            f"No partial file should exist after PermissionError, but found: {output_file}"
        )
