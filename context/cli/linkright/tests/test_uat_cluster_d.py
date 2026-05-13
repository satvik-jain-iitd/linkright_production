"""UAT Cluster D — Profile Logic — fix verification.

Six behavioural fixes shipped in `fix/uat-d-profile-logic`:

  #25 — typed nuggets: facts (education, certifications, awards) and skills
        are classified separately from experience so the retrieval pool
        no longer mixes static facts with achievement bullets.
  #26 — priority ordering: P0 → P3 sort applied at every read site
        (persist, append, render) so newly-enriched nuggets land in
        the correct bucket regardless of insertion order.
  #27 — entity resolution fallback: when the LLM marks a nugget's
        company as "unknown"/"none" but the parsed-resume header has it,
        the deterministic resolver fills it in.
  #28 — gap-filling: work_experience nuggets missing role/company/dates
        are surfaced via parse_and_extract result['gaps']; CLI uses
        this to prompt or warn the user.
  #31 — fluff-metric detection: vague nuggets like "Increased business
        value by 100%" are rejected at extraction time and demoted by
        audit.
  #32 — audit phase: standalone re-pass re-classifies, re-resolves,
        flags fluff, and re-sorts the on-disk jsonl + highlights.

Each TestClass corresponds to one bug. Each test holds tight on a
single invariant — order doesn't matter, mocks are minimal.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# ─────────────────────────────────────────────────────────────────────
# #25 — Typed nuggets: fact / experience / skill classification
# ─────────────────────────────────────────────────────────────────────

class TestNuggetClassification:
    def test_education_classified_as_fact(self):
        from linkright.profile.nugget_utils import class_of
        nug = {"type": "education", "answer": "MBA at IIM"}
        assert class_of(nug) == "fact"

    def test_certification_classified_as_fact(self):
        from linkright.profile.nugget_utils import class_of
        nug = {"type": "certification", "answer": "AWS Solutions Architect"}
        assert class_of(nug) == "fact"

    def test_award_classified_as_fact(self):
        from linkright.profile.nugget_utils import class_of
        nug = {"type": "award", "answer": "President's club 2024"}
        assert class_of(nug) == "fact"

    def test_skill_classified_as_skill(self):
        from linkright.profile.nugget_utils import class_of
        nug = {"type": "skill", "answer": "Python, SQL, A/B testing"}
        assert class_of(nug) == "skill"

    def test_work_experience_classified_as_experience(self):
        from linkright.profile.nugget_utils import class_of
        nug = {"type": "work_experience", "answer": "Shipped onboarding"}
        assert class_of(nug) == "experience"

    def test_unknown_type_defaults_to_experience(self):
        """Defensive fallback — legacy nuggets without a type field
        must not silently disappear from retrieval."""
        from linkright.profile.nugget_utils import class_of
        nug = {"answer": "did some stuff"}
        assert class_of(nug) == "experience"

    def test_explicit_nugget_class_overrides_type(self):
        """An explicit `nugget_class` field takes precedence — supports
        future cases where a single type maps to multiple classes."""
        from linkright.profile.nugget_utils import class_of
        nug = {"type": "education", "nugget_class": "experience"}
        assert class_of(nug) == "experience"

    def test_classify_in_place_stamps_missing_fields(self):
        from linkright.profile.nugget_utils import classify_in_place
        nuggets = [
            {"type": "work_experience"},
            {"type": "education"},
            {"type": "skill"},
            {"type": "work_experience", "nugget_class": "experience"},  # already set
        ]
        touched = classify_in_place(nuggets)
        assert touched == 3  # the pre-stamped row is skipped
        assert nuggets[0]["nugget_class"] == "experience"
        assert nuggets[1]["nugget_class"] == "fact"
        assert nuggets[2]["nugget_class"] == "skill"

    def test_persist_stamps_nugget_class(self, tmp_path):
        """End-to-end: persist() writes nuggets.jsonl with nugget_class
        on every row (#25 schema is stable on disk, not just in memory)."""
        import numpy as np
        from linkright.profile.pipeline import persist

        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        # Stub source PDF (persist reads SHA but never opens it for
        # content; an empty file is fine for the sha hash).
        src_pdf = tmp_path / "resume.pdf"
        src_pdf.write_bytes(b"%PDF-1.4\n%fake\n")

        result = {
            "nuggets": [
                {"type": "work_experience", "company": "Acme", "role": "PM",
                 "answer": "Shipped 100M+ users", "importance": "P0",
                 "emb": list(np.zeros(384, dtype=np.float32))},
                {"type": "education", "company": "IIM",
                 "answer": "MBA 2020", "importance": "P2",
                 "emb": list(np.zeros(384, dtype=np.float32))},
                {"type": "skill", "answer": "Python",
                 "importance": "P3",
                 "emb": list(np.zeros(384, dtype=np.float32))},
            ]
        }
        persist(profile_dir, src_pdf, result)
        # Each persisted row carries a class field.
        rows = [json.loads(l) for l in (profile_dir / "nuggets.jsonl").read_text().splitlines() if l.strip()]
        classes = {r.get("nugget_class") for r in rows}
        assert classes == {"experience", "fact", "skill"}


# ─────────────────────────────────────────────────────────────────────
# #26 — Priority ordering: P0 first regardless of insertion order
# ─────────────────────────────────────────────────────────────────────

class TestPrioritySort:
    def test_sort_orders_p0_before_p3(self):
        from linkright.profile.nugget_utils import sort_by_priority
        nuggets = [
            {"importance": "P3", "answer": "z"},
            {"importance": "P0", "answer": "a"},
            {"importance": "P2", "answer": "y"},
            {"importance": "P1", "answer": "b"},
        ]
        out = sort_by_priority(nuggets)
        assert [n["importance"] for n in out] == ["P0", "P1", "P2", "P3"]

    def test_sort_is_stable_within_bucket(self):
        """Within the same priority, insertion order is preserved.
        Critical: a freshly-added P0 (appended last) keeps its
        end-of-bucket position rather than jumping over older P0s."""
        from linkright.profile.nugget_utils import sort_by_priority
        nuggets = [
            {"importance": "P0", "answer": "first_p0", "nugget_index": 1},
            {"importance": "P2", "answer": "first_p2", "nugget_index": 2},
            {"importance": "P0", "answer": "second_p0", "nugget_index": 3},
        ]
        out = sort_by_priority(nuggets)
        assert out[0]["nugget_index"] == 1
        assert out[1]["nugget_index"] == 3
        assert out[2]["nugget_index"] == 2

    def test_unknown_importance_sorts_last(self):
        from linkright.profile.nugget_utils import sort_by_priority
        nuggets = [
            {"importance": "???", "answer": "weird"},
            {"importance": "P0", "answer": "ok"},
        ]
        out = sort_by_priority(nuggets)
        assert out[0]["importance"] == "P0"
        assert out[1]["importance"] == "???"

    def test_persist_writes_priority_sorted_jsonl(self, tmp_path):
        """End-to-end: persist() rewrites nuggets.jsonl in priority order
        even when the LLM emitted them in P2 → P0 → P1 order."""
        import numpy as np
        from linkright.profile.pipeline import persist

        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        src_pdf = tmp_path / "resume.pdf"
        src_pdf.write_bytes(b"%PDF-1.4\n")

        result = {
            "nuggets": [
                {"type": "work_experience", "company": "Acme", "role": "PM",
                 "answer": "p2-thing", "importance": "P2",
                 "emb": list(np.zeros(384, dtype=np.float32))},
                {"type": "work_experience", "company": "Acme", "role": "PM",
                 "answer": "p0-thing", "importance": "P0",
                 "emb": list(np.zeros(384, dtype=np.float32))},
                {"type": "work_experience", "company": "Acme", "role": "PM",
                 "answer": "p1-thing", "importance": "P1",
                 "emb": list(np.zeros(384, dtype=np.float32))},
            ]
        }
        persist(profile_dir, src_pdf, result)
        rows = [json.loads(l) for l in (profile_dir / "nuggets.jsonl").read_text().splitlines() if l.strip()]
        assert [r["importance"] for r in rows] == ["P0", "P1", "P2"]


# ─────────────────────────────────────────────────────────────────────
# #27 — Entity resolution: fill 'unknown' company when in parsed/text
# ─────────────────────────────────────────────────────────────────────

class TestEntityResolution:
    def test_unknown_company_resolved_from_parsed_companies(self):
        """When company is 'none' but parsed.companies contains a name
        that appears in the nugget's answer, the resolver fills it in."""
        from linkright.profile.nugget_utils import resolve_entity
        nug = {
            "company": "none", "role": "PM",
            "answer": "Shipped onboarding at American Express to 30M+ users",
        }
        parsed = {"companies": [{"name": "American Express", "title": "PM"}]}
        out = resolve_entity(nug, parsed=parsed)
        assert out["company"] == "American Express"
        assert out["_entity_resolved_by"] == "parsed_companies"

    def test_unknown_role_filled_from_company_match(self):
        from linkright.profile.nugget_utils import resolve_entity
        nug = {
            "company": "none", "role": "none",
            "answer": "Drove $2M savings as Senior PM at Sprinklr",
        }
        parsed = {"companies": [{"name": "Sprinklr", "title": "Senior PM"}]}
        out = resolve_entity(nug, parsed=parsed)
        assert out["company"] == "Sprinklr"
        assert out["role"] == "Senior PM"

    def test_non_missing_company_is_preserved(self):
        """The resolver MUST NOT overwrite an LLM-set value (avoids
        regression risk if the LLM disagrees with the parser)."""
        from linkright.profile.nugget_utils import resolve_entity
        nug = {
            "company": "Acme Bank", "role": "PM",
            "answer": "Shipped onboarding at American Express",
        }
        parsed = {"companies": [{"name": "American Express", "title": "PM"}]}
        out = resolve_entity(nug, parsed=parsed)
        assert out["company"] == "Acme Bank"  # untouched

    def test_raw_text_pattern_fallback(self):
        """When parsed companies is empty, the 'at <Company>' pattern
        fallback works as long as the candidate name appears in raw text."""
        from linkright.profile.nugget_utils import resolve_entity
        nug = {
            "company": "unknown", "role": "PM",
            "answer": "Built dashboard at Stripe processing 100M+ rows",
        }
        raw = "Work experience: Stripe 2020-2023, PM."
        out = resolve_entity(nug, parsed={}, raw_text=raw)
        assert out["company"] == "Stripe"
        assert out["_entity_resolved_by"] == "raw_text_pattern"


# ─────────────────────────────────────────────────────────────────────
# #28 — Gap-filling loop targets
# ─────────────────────────────────────────────────────────────────────

class TestGapFilling:
    def test_missing_role_flagged(self):
        from linkright.profile.nugget_utils import gap_filling_targets
        nuggets = [
            {"type": "work_experience", "company": "Acme", "role": "",
             "answer": "Shipped a thing", "nugget_index": 7},
        ]
        gaps = gap_filling_targets(nuggets)
        assert len(gaps) == 1
        assert "role" in gaps[0]["missing"]
        assert gaps[0]["nugget_index"] == 7

    def test_missing_company_flagged(self):
        from linkright.profile.nugget_utils import gap_filling_targets
        nuggets = [
            {"type": "work_experience", "company": "none", "role": "PM",
             "answer": "Did stuff"},
        ]
        gaps = gap_filling_targets(nuggets)
        assert len(gaps) == 1
        assert "company" in gaps[0]["missing"]

    def test_missing_dates_flagged(self):
        from linkright.profile.nugget_utils import gap_filling_targets
        nuggets = [
            {"type": "work_experience", "company": "Acme", "role": "PM",
             "answer": "Did stuff"},  # no start_date / date_range
        ]
        gaps = gap_filling_targets(nuggets)
        assert "dates" in gaps[0]["missing"]

    def test_complete_nugget_not_flagged(self):
        from linkright.profile.nugget_utils import gap_filling_targets
        nuggets = [
            {"type": "work_experience", "company": "Acme", "role": "PM",
             "answer": "Did stuff", "start_date": "Jan 2024"},
        ]
        assert gap_filling_targets(nuggets) == []

    def test_skill_nuggets_not_flagged(self):
        """Skills don't need role/company — only experience nuggets do."""
        from linkright.profile.nugget_utils import gap_filling_targets
        nuggets = [
            {"type": "skill", "answer": "Python"},
        ]
        assert gap_filling_targets(nuggets) == []

    def test_independent_project_not_flagged(self):
        """Independent projects conventionally have no company."""
        from linkright.profile.nugget_utils import gap_filling_targets
        nuggets = [
            {"type": "independent_project", "company": "none",
             "answer": "Side project"},
        ]
        assert gap_filling_targets(nuggets) == []

    def test_gaps_capped_at_5(self):
        """Bounded surface — never display a 30-question inquisition."""
        from linkright.profile.nugget_utils import gap_filling_targets
        nuggets = [
            {"type": "work_experience", "company": "", "role": "",
             "answer": f"thing {i}"}
            for i in range(10)
        ]
        assert len(gap_filling_targets(nuggets)) == 5


# ─────────────────────────────────────────────────────────────────────
# #31 — Fluff-metric detection
# ─────────────────────────────────────────────────────────────────────

class TestFluffDetection:
    def test_business_value_100pct_flagged(self):
        """The canonical UAT example."""
        from linkright.profile.nugget_utils import is_fluff_metric
        assert is_fluff_metric("Increased business value by 100%")

    def test_stakeholder_value_200pct_flagged(self):
        from linkright.profile.nugget_utils import is_fluff_metric
        assert is_fluff_metric("Drove stakeholder value 200%")

    def test_10x_synergy_flagged(self):
        from linkright.profile.nugget_utils import is_fluff_metric
        assert is_fluff_metric("Boosted synergy 10x across teams")

    def test_significantly_improved_morale_flagged(self):
        """Intensifier + fluff noun (no number) — still vague."""
        from linkright.profile.nugget_utils import is_fluff_metric
        assert is_fluff_metric("Significantly improved team morale")

    def test_concrete_revenue_metric_passes(self):
        """Two-signal rule: 'revenue' is concrete, NOT a fluff noun."""
        from linkright.profile.nugget_utils import is_fluff_metric
        assert not is_fluff_metric("Increased revenue 100% YoY")

    def test_concrete_users_metric_passes(self):
        from linkright.profile.nugget_utils import is_fluff_metric
        assert not is_fluff_metric("Grew users 200% in Q3")

    def test_test_coverage_100pct_passes(self):
        """'100% test coverage' is a real metric, not fluff."""
        from linkright.profile.nugget_utils import is_fluff_metric
        assert not is_fluff_metric("Shipped 100% test coverage in Q3")

    def test_no_number_no_intensifier_passes(self):
        from linkright.profile.nugget_utils import is_fluff_metric
        assert not is_fluff_metric("Drove engagement campaign across 6 markets")

    def test_extract_from_answer_rejects_fluff(self, monkeypatch):
        """End-to-end: enrich.extract_from_answer drops a fluff response
        before persisting (returns None)."""
        from linkright.profile import enrich

        # Stub the LLM call to return a fluff nugget.
        def fake_tier_chat(*args, **kwargs):
            return (
                '{"nugget_text": "Increased business value by 100%", '
                '"company": "Acme", "role": "PM", "importance": "P0", '
                '"type": "work_experience"}',
                {"provider": "stub"},
            )
        # The function imports tier_chat lazily from linkright.llm.direct.
        import linkright.llm.direct as direct_mod
        monkeypatch.setattr(direct_mod, "tier_chat", fake_tier_chat)

        parent = {"company": "Acme", "role": "PM",
                  "nugget_text": "Did some PM work"}
        result = enrich.extract_from_answer(parent, "What was the impact?",
                                            "I increased business value")
        assert result is None  # fluff rejected at extraction time


# ─────────────────────────────────────────────────────────────────────
# #32 — Audit / cleanup phase
# ─────────────────────────────────────────────────────────────────────

class TestAuditPhase:
    def test_audit_demotes_existing_fluff(self):
        """audit_nuggets() finds fluff in pre-existing nuggets and
        demotes them to P3 with a flag."""
        from linkright.profile.nugget_utils import audit_nuggets
        nuggets = [
            {"type": "work_experience", "company": "Acme", "role": "PM",
             "answer": "Increased business value by 100%",
             "importance": "P0"},
            {"type": "work_experience", "company": "Acme", "role": "PM",
             "answer": "Grew users 200% in Q3", "importance": "P0"},
        ]
        counts = audit_nuggets(nuggets, parsed={}, raw_text="")
        assert counts["fluff_demoted"] == 1
        assert counts["reprioritised"] == 1
        # Fluff nugget demoted to P3, has the flag.
        fluff = nuggets[0]
        assert fluff["importance"] == "P3"
        assert "fluff_metric" in fluff["_audit_flags"]
        # Concrete-metric nugget untouched.
        assert nuggets[1]["importance"] == "P0"
        assert "_audit_flags" not in nuggets[1]

    def test_audit_backfills_missing_class(self):
        """Legacy nuggets without `nugget_class` get one stamped on
        first audit (#25 schema backfill path)."""
        from linkright.profile.nugget_utils import audit_nuggets
        nuggets = [
            {"type": "education", "answer": "MBA 2020"},
            {"type": "work_experience", "answer": "Did PM work"},
        ]
        counts = audit_nuggets(nuggets, parsed={}, raw_text="")
        assert counts["classified"] == 2
        assert nuggets[0]["nugget_class"] == "fact"
        assert nuggets[1]["nugget_class"] == "experience"

    def test_audit_resolves_unknown_company(self):
        from linkright.profile.nugget_utils import audit_nuggets
        nuggets = [
            {"type": "work_experience", "company": "unknown", "role": "PM",
             "answer": "Shipped onboarding at Acme Corp",
             "importance": "P1"},
        ]
        parsed = {"companies": [{"name": "Acme Corp", "title": "PM"}]}
        counts = audit_nuggets(nuggets, parsed=parsed, raw_text="")
        assert counts["entity_resolved"] == 1
        assert nuggets[0]["company"] == "Acme Corp"

    def test_audit_idempotent(self):
        """Running audit twice doesn't double-demote or double-flag."""
        from linkright.profile.nugget_utils import audit_nuggets
        nuggets = [
            {"type": "work_experience", "company": "Acme", "role": "PM",
             "answer": "Increased business value by 100%",
             "importance": "P0"},
        ]
        first = audit_nuggets(nuggets, parsed={}, raw_text="")
        second = audit_nuggets(nuggets, parsed={}, raw_text="")
        assert first["fluff_demoted"] == 1
        assert second["fluff_demoted"] == 0
        assert nuggets[0]["_audit_flags"] == ["fluff_metric"]  # no dupes
        assert nuggets[0]["importance"] == "P3"

    def test_run_audit_end_to_end(self, tmp_path):
        """run_audit() reads nuggets.jsonl, mutates, re-sorts, rewrites."""
        from linkright.profile.audit import run_audit

        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        # metadata.yaml present — required gate
        (profile_dir / "metadata.yaml").write_text(
            "n_nuggets: 2\nn_highlights: 1\n", encoding="utf-8"
        )
        # Pre-existing jsonl with a fluff P0 + a clean P1.
        rows = [
            {"type": "work_experience", "company": "Acme", "role": "PM",
             "answer": "Increased business value by 100%",
             "importance": "P0"},
            {"type": "work_experience", "company": "Acme", "role": "PM",
             "answer": "Shipped 100M+ events/day analytics platform",
             "importance": "P1"},
        ]
        with open(profile_dir / "nuggets.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

        counts = run_audit(profile_dir)
        assert counts["wrote_files"]
        assert counts["fluff_demoted"] == 1

        # Verify on disk: fluff is now P3, sort order is P1 → P3.
        written = [json.loads(l) for l in (profile_dir / "nuggets.jsonl").read_text().splitlines() if l.strip()]
        assert [r["importance"] for r in written] == ["P1", "P3"]
        assert "fluff_metric" in written[1]["_audit_flags"]

        # highlights.jsonl drops the demoted nugget (P3 is not a highlight).
        highlights = [json.loads(l) for l in (profile_dir / "highlights.jsonl").read_text().splitlines() if l.strip()]
        assert len(highlights) == 1
        assert highlights[0]["importance"] == "P1"

    def test_run_audit_no_changes_no_write(self, tmp_path):
        """Idempotent at the file layer: clean profile → no rewrite."""
        from linkright.profile.audit import run_audit
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        (profile_dir / "metadata.yaml").write_text("n_nuggets: 1\n", encoding="utf-8")
        rows = [
            {"type": "work_experience", "company": "Acme", "role": "PM",
             "answer": "Shipped 100M+ events/day analytics platform",
             "importance": "P1", "nugget_class": "experience"},
        ]
        with open(profile_dir / "nuggets.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        mtime_before = (profile_dir / "nuggets.jsonl").stat().st_mtime_ns
        counts = run_audit(profile_dir)
        assert not counts["wrote_files"]
        mtime_after = (profile_dir / "nuggets.jsonl").stat().st_mtime_ns
        assert mtime_before == mtime_after
