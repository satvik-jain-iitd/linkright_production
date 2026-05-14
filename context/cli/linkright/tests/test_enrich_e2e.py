"""End-to-end enrich pipeline test with LLM + embedder mocked.

Verifies the full Phase 3 loop:
  Profile w/ thin role → analyze → query gen → retrieve → propose →
  user accepts → promote → facts.jsonl + signals updated + history snap.
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from linkright.enrich.cli import enrich
from linkright.evidence.ingest import ingest_file
from linkright.evidence.schemas import EvidenceTier
from linkright.profile.v2_schemas import (
    CareerProfile,
    Fact,
    Role,
    Signal,
    SignalConfidence,
)
from linkright.profile.v2_store import (
    load_facts,
    load_signals,
    save_canonical_profile,
    write_facts,
    write_signals,
)


@pytest.fixture
def isolated_lr_home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LINKRIGHT_HOME", str(tmp_path / "lr"))
    return tmp_path / "lr"


def _fake_embed(text: str):
    import hashlib
    import math
    h = hashlib.sha256(text.encode()).digest()
    raw = list(h) * (384 // len(h) + 1)
    raw = raw[:384]
    norm = math.sqrt(sum(v * v for v in raw)) or 1.0
    return [v / norm for v in raw], {"tier": "fake", "model": "fake_sha256", "dim": 384}


def _seed_profile_with_thin_role():
    """Create a profile with one role + 1 fact (well below MIN_FACTS=5)."""
    profile = CareerProfile(
        id="profile_test",
        roles=[Role(id="role_amex_2023", company="AmEx", title="Senior PM",
                    start_date="2023-01", is_current=True)],
        current_archetype="ai_native_pm",
    )
    save_canonical_profile(profile, snapshot=False)
    write_facts([
        Fact(id="fact_001", text="Joined AmEx in Q1 2023",
             role_id="role_amex_2023", confidence=0.85, user_confirmed=True),
    ])
    write_signals([
        Signal(id="sig_x", canonical_name="ambiguity_handling",
               source_fact_ids=["fact_001"], recurrence_count=1,
               archetype_alignment=["ai_native_pm"]),
    ])


def _seed_evidence(tmp_path: Path):
    """Add an evidence memo so retrieval has atoms to find."""
    p = tmp_path / "context.md"
    p.write_text(textwrap.dedent("""\
        ---
        source_type: additional_info
        date: 2024-03-01
        author_role: "Senior PM"
        ---

        ## Atom: Walmart partnership negotiation
        date: 2024-03-12
        role: "Senior PM"
        company: AmEx
        tags: [walmart, partnership, stakeholder]

        I personally led the partnership conversation with Walmart's VP of
        Payments to swap 3 senior engineers into my pod for the card-on-file
        initiative. Closed in 2 weeks via reciprocal dashboard access.

        ## Atom: SMB tier deprioritization
        date: 2024-05-08
        role: "Senior PM"
        company: AmEx
        tags: [prioritization, tradeoff, decision]

        I deprioritized the SMB merchant tier from Q3 roadmap despite a $1.2M
        ARR pipeline. Used LTV-per-cycle model to defend the call to my VP.
    """))
    ingest_file(p, embed_fn=_fake_embed)


# ── Mocked LLM responses ──────────────────────────────────────────────────

def _fake_query_gen(system, user, response_schema, **kwargs):
    """Inspect prompt → return canned queries per gap."""
    if "Gaps to address" in user:
        # Cover the role gap + signal gap + archetype + metric gaps the
        # profile produces. The exact gap_ids depend on what analyze() returns
        # so we match by substring presence.
        gap_queries = []
        if "gap_role_role_amex_2023" in user:
            gap_queries.append({
                "gap_id": "gap_role_role_amex_2023",
                "queries": ["AmEx Walmart partnership specifics", "AmEx SMB prioritization decision"],
            })
        if "gap_signal_sig_x" in user:
            gap_queries.append({
                "gap_id": "gap_signal_sig_x",
                "queries": ["ambiguity handling specific examples"],
            })
        if "gap_archetype_ai_native_pm" in user:
            gap_queries.append({
                "gap_id": "gap_archetype_ai_native_pm",
                "queries": ["systems thinking AI native PM"],
            })
        if "gap_metrics_missing" in user:
            gap_queries.append({
                "gap_id": "gap_metrics_missing",
                "queries": ["quantitative outcomes"],
            })
        return json.dumps({"gap_queries": gap_queries}), {"provider": "fake"}

    if "Propose 0-" in user:
        # Return one fact proposal per call. Use first atom_id from prompt
        # (heuristic) so the citation matches retrieved atoms.
        # Extract first atom_id mentioned
        import re
        m = re.search(r"atom_id=(ev_\d+_a\d+)", user)
        atom_id = m.group(1) if m else "ev_001_a000"
        # Vary the proposal text slightly so dedupe is testable
        if "gap_role_role_amex_2023" in user:
            return json.dumps({
                "facts": [
                    {
                        "text": "Negotiated Walmart engineer swap in 2 weeks for card-on-file initiative at AmEx",
                        "role_id": "role_amex_2023",
                        "evidence_atom_ids": [atom_id],
                        "confidence": 0.92,
                        "metric_extracted": {"headcount": 3, "duration_months": 0.5},
                    },
                ]
            }), {"provider": "fake"}
        elif "gap_signal_sig_x" in user:
            return json.dumps({
                "facts": [
                    {
                        "text": "Deprioritized SMB tier despite $1.2M pipeline using LTV-per-cycle model",
                        "role_id": "role_amex_2023",
                        "evidence_atom_ids": [atom_id],
                        "confidence": 0.88,
                    },
                ]
            }), {"provider": "fake"}
        else:
            return json.dumps({"facts": []}), {"provider": "fake"}

    raise AssertionError(f"Unexpected LLM call: {user[:200]}")


# ════════════════════════════════════════════════════════════════════════════
# Tests
# ════════════════════════════════════════════════════════════════════════════

def test_enrich_dry_run_stops_after_query_gen(isolated_lr_home, tmp_path):
    _seed_profile_with_thin_role()
    _seed_evidence(tmp_path)

    runner = CliRunner()
    with patch("linkright.enrich.query_gen.gemini_chat_json", _fake_query_gen), \
         patch("linkright.resume.lib.embedder.embed", _fake_embed):
        result = runner.invoke(enrich, ["--dry-run"])

    assert result.exit_code == 0, result.output
    assert "Step 1: Gap analysis" in result.output
    assert "Step 2: Generating retrieval queries" in result.output
    assert "Step 3" not in result.output  # dry-run stops here
    # Run dir exists with gaps.json + queries.json
    runs = list((isolated_lr_home / "enrichment" / "enrichment_runs").iterdir())
    assert len(runs) == 1
    assert (runs[0] / "gaps.json").exists()
    assert (runs[0] / "queries.json").exists()


def test_enrich_full_pipeline_accepts_proposals(isolated_lr_home, tmp_path):
    _seed_profile_with_thin_role()
    _seed_evidence(tmp_path)

    initial_facts = len(load_facts())

    runner = CliRunner()
    # Accept all proposals at first prompt (auto-accept-rest per gap)
    user_input = "\n".join(["a"] * 10)

    with patch("linkright.enrich.query_gen.gemini_chat_json", _fake_query_gen), \
         patch("linkright.enrich.proposals.gemini_chat_json", _fake_query_gen), \
         patch("linkright.resume.lib.embedder.embed", _fake_embed):
        result = runner.invoke(enrich, [], input=user_input)

    assert result.exit_code == 0, result.output
    assert "Enrichment complete" in result.output

    # Facts grew
    final_facts = load_facts()
    assert len(final_facts) > initial_facts

    # New facts are confirmed + carry role_id
    new_facts = final_facts[initial_facts:]
    assert all(f.user_confirmed for f in new_facts)
    assert all(f.role_id == "role_amex_2023" for f in new_facts)

    # Pending facts cleared
    pending = isolated_lr_home / "enrichment" / "pending_facts.jsonl"
    assert not pending.exists()


def test_enrich_no_profile_aborts(isolated_lr_home):
    runner = CliRunner()
    result = runner.invoke(enrich, [])
    assert result.exit_code != 0
    assert "No CareerProfile found" in result.output


def test_enrich_no_gaps_exits_clean(isolated_lr_home, tmp_path):
    """Profile with enough facts → gap analysis returns nothing → clean exit."""
    profile = CareerProfile(
        id="profile_test",
        roles=[Role(id="role_x", company="X", title="PM")],
    )
    save_canonical_profile(profile, snapshot=False)
    write_facts([
        Fact(id=f"fact_{i:03d}", text=f"Built X with metric {i}%", role_id="role_x",
             user_confirmed=True, confidence=0.9)
        for i in range(1, 6)  # 5 facts → above MIN_FACTS_PER_ROLE threshold
    ])

    runner = CliRunner()
    result = runner.invoke(enrich, [])
    assert result.exit_code == 0
    assert "No gaps detected" in result.output


def test_enrich_focus_filter(isolated_lr_home, tmp_path):
    _seed_profile_with_thin_role()
    _seed_evidence(tmp_path)

    runner = CliRunner()
    with patch("linkright.enrich.query_gen.gemini_chat_json", _fake_query_gen), \
         patch("linkright.resume.lib.embedder.embed", _fake_embed):
        result = runner.invoke(enrich, ["--focus", "metric", "--dry-run"])

    assert result.exit_code == 0
    # Only metric gaps surfaced
    assert "[metric]" in result.output
    # Other kinds suppressed
    assert "[role]" not in result.output
    assert "[signal]" not in result.output
