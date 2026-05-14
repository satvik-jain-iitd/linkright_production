"""Retrieval tests using a deterministic fake embedder + isolated EvidenceStore."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from linkright.enrich.retrieval import (
    MAX_TAG_BOOST,
    TAG_BOOST_PER_OVERLAP,
    retrieve_atom_pool,
    retrieve_atoms_for_query,
    _count_tag_overlap,
    _tokenize,
)
from linkright.evidence.ingest import ingest_file
from linkright.evidence.schemas import Atom, EvidenceTier
from linkright.evidence.store import EvidenceStore


def fake_embed(text: str):
    """Hash-based deterministic vec — keeps tests fast + reproducible."""
    import hashlib
    import math
    h = hashlib.sha256(text.encode()).digest()
    raw = list(h) * (384 // len(h) + 1)
    raw = raw[:384]
    norm = math.sqrt(sum(v * v for v in raw)) or 1.0
    return [v / norm for v in raw], {"tier": "fake", "model": "fake_sha256", "dim": 384}


@pytest.fixture
def isolated_lr_home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LINKRIGHT_HOME", str(tmp_path / "lr"))
    return tmp_path / "lr"


def _ingest_memo(tmp_path, name, source_type="additional_info", atoms_yaml=None):
    """Build + ingest a memo file with given atoms list."""
    body_atoms = atoms_yaml or [
        {
            "title": "Walmart partnership",
            "tags": ["walmart", "partnership"],
            "text": "Closed Walmart engineer swap in 2 weeks via reciprocal dashboard access.",
        },
        {
            "title": "SMB deprioritization",
            "tags": ["prioritization", "tradeoff"],
            "text": "Deprioritized SMB tier despite $1.2M pipeline using LTV-per-cycle model.",
        },
    ]
    atom_blocks = []
    for a in body_atoms:
        tags_yaml = "[" + ", ".join(a["tags"]) + "]"
        atom_blocks.append(textwrap.dedent(f"""\
            ## Atom: {a["title"]}
            date: 2024-03-01
            role: "Senior PM"
            company: AmEx
            tags: {tags_yaml}

            {a["text"]}
        """).strip())

    content = textwrap.dedent(f"""\
        ---
        source_type: {source_type}
        date: 2024-03-01
        author_role: "Senior PM"
        ---

        """) + "\n\n".join(atom_blocks) + "\n"

    p = tmp_path / name
    p.write_text(content)
    ingest_file(p, embed_fn=fake_embed)


# ── _tokenize ──────────────────────────────────────────────────────────────

def test_tokenize_lowercase_alnum():
    assert _tokenize("Walmart Partnership 2024") == {"walmart", "partnership", "2024"}


def test_tokenize_handles_punctuation():
    assert _tokenize("LTV-per-cycle, $1.2M") == {"ltv-per-cycle", "1", "2m"}


# ── _count_tag_overlap ─────────────────────────────────────────────────────

def test_tag_overlap_single_word_tags():
    atom = Atom(
        id="a1", evidence_id="ev_1", chunk_idx=0, atom_title="x", text="y",
        metadata={"tags": ["walmart", "partnership"]},
    )
    q_tokens = {"walmart", "engineer", "swap"}
    assert _count_tag_overlap(atom, q_tokens) == 1


def test_tag_overlap_multi_word_tag_counts_once():
    atom = Atom(
        id="a1", evidence_id="ev_1", chunk_idx=0, atom_title="x", text="y",
        metadata={"tags": ["customer success engineering"]},
    )
    q_tokens = {"customer", "engineering", "success"}
    # Multi-token tag still counts as 1 overlap — not 3
    assert _count_tag_overlap(atom, q_tokens) == 1


def test_tag_overlap_zero_when_no_match():
    atom = Atom(
        id="a1", evidence_id="ev_1", chunk_idx=0, atom_title="x", text="y",
        metadata={"tags": ["foo"]},
    )
    assert _count_tag_overlap(atom, {"bar", "baz"}) == 0


# ── retrieve_atoms_for_query ───────────────────────────────────────────────

def test_retrieve_atoms_returns_top_k(isolated_lr_home, tmp_path):
    _ingest_memo(tmp_path, "memo.md")
    hits = retrieve_atoms_for_query(
        "Walmart engineer swap", embed_fn=fake_embed, top_k=2,
    )
    assert len(hits) == 2
    # Hits sorted by score descending
    assert hits[0].score >= hits[1].score


def test_retrieve_atoms_empty_when_no_evidence(isolated_lr_home):
    hits = retrieve_atoms_for_query("anything", embed_fn=fake_embed)
    assert hits == []


def test_retrieve_atoms_tag_boost_applies(isolated_lr_home, tmp_path):
    _ingest_memo(tmp_path, "memo.md")
    # Query tokens include "walmart" → first atom's tag list contains "walmart"
    hits = retrieve_atoms_for_query("walmart partnership details", embed_fn=fake_embed, top_k=2)
    walmart_hits = [h for h in hits if "Walmart" in str(h.atom_id)]  # by id pattern
    # Find the Walmart atom — its tag_overlap should be ≥ 1
    walmart_hit = next((h for h in hits if h.tag_overlap >= 1), None)
    assert walmart_hit is not None
    assert walmart_hit.score >= walmart_hit.cosine_score  # boost applied


def test_retrieve_atoms_tier_filter(isolated_lr_home, tmp_path):
    # Two evidence: one diary, one additional_info
    _ingest_memo(tmp_path, "diary.md", source_type="diary")
    _ingest_memo(tmp_path, "ai.md", source_type="additional_info")

    # Filter to diary only
    hits = retrieve_atoms_for_query(
        "anything", embed_fn=fake_embed, tier_filter=["diary"], top_k=10,
    )
    # Each hit must come from diary tier
    store = EvidenceStore()
    diary_evidence_ids = {e.id for e in store.list_evidence() if e.tier == EvidenceTier.DIARY}
    for h in hits:
        atom_ev_id = h.atom_id.rsplit("_a", 1)[0]
        assert atom_ev_id in diary_evidence_ids


# ── retrieve_atom_pool ─────────────────────────────────────────────────────

def test_retrieve_atom_pool_dedupes_across_queries(isolated_lr_home, tmp_path):
    _ingest_memo(tmp_path, "memo.md")
    pool = retrieve_atom_pool(
        ["Walmart partnership", "engineer swap"],
        embed_fn=fake_embed,
        top_k_per_query=5,
    )
    # 2 unique atoms total in fixture; pool must not duplicate
    ids = [a.id for a in pool]
    assert len(ids) == len(set(ids))


def test_retrieve_atom_pool_empty_queries(isolated_lr_home):
    pool = retrieve_atom_pool([], embed_fn=fake_embed)
    assert pool == []
