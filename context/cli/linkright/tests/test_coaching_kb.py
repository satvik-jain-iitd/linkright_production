"""Tests for Phase 5 — Coaching KB chunker, routing, and builder."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from linkright.coaching_kb.build import (
    MIN_CHUNK_CHARS,
    TARGET_CHUNK_CHARS,
    build_playbook,
    chunk_doc,
    is_kb_built,
    load_playbook_chunks,
    load_playbook_embeddings,
)
from linkright.coaching_kb.routing import (
    KB_PHASE_ROUTING,
    all_phases,
    all_referenced_docs,
    docs_for_phase,
    phases_for_doc,
)


def fake_embed(text: str):
    """Hash-based 384-dim deterministic vec — fast + reproducible."""
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


# ════════════════════════════════════════════════════════════════════════════
# Routing — pure data integrity
# ════════════════════════════════════════════════════════════════════════════

def test_routing_table_non_empty():
    assert len(KB_PHASE_ROUTING) >= 20  # we shipped ~30 phases


def test_routing_all_values_are_lists_of_md_filenames():
    for phase, docs in KB_PHASE_ROUTING.items():
        assert isinstance(docs, list)
        assert len(docs) >= 1, f"phase '{phase}' has no docs"
        for d in docs:
            assert d.endswith(".md"), f"phase '{phase}' doc '{d}' missing .md ext"


def test_docs_for_phase_known():
    docs = docs_for_phase("intro_question")
    assert "interview_intro_positioning_guide.md" in docs


def test_docs_for_phase_unknown_returns_empty():
    assert docs_for_phase("nonexistent_phase") == []


def test_phases_for_doc_reverse_lookup():
    phases = phases_for_doc("interview_stories_positioning_guide.md")
    assert "behavioral_question" in phases
    assert "ideal_answer_construction" in phases


def test_phases_for_doc_unknown_returns_empty():
    assert phases_for_doc("totally_invented.md") == []


def test_all_phases_sorted():
    p = all_phases()
    assert p == sorted(p)


def test_all_referenced_docs_returns_unique_set():
    refs = all_referenced_docs()
    assert isinstance(refs, set)
    assert len(refs) >= 25  # we reference at least 25 unique docs


# ════════════════════════════════════════════════════════════════════════════
# chunk_doc — heading-based chunking correctness
# ════════════════════════════════════════════════════════════════════════════

SIMPLE_DOC = textwrap.dedent("""\
    # The Document Title

    Some preamble text that is long enough to be a real chunk on its own,
    not just a single line of throwaway. We want this preamble paragraph
    to comfortably exceed the MIN_CHUNK_CHARS threshold so the chunker
    treats it as a standalone preamble chunk in the output stream.

    ## First Section

    Content of the first section. This needs to be substantive enough that
    it crosses MIN_CHUNK_CHARS and survives as its own chunk. Long enough
    to capture the spirit of a real research-doc paragraph.

    ## Second Section

    Content of the second section. Similarly verbose so the chunker emits
    a real second chunk rather than merging it as a tiny fragment back
    into the first. Should be its own atom in the output.
""")


def test_chunk_doc_basic_h2_split():
    chunks = list(chunk_doc(SIMPLE_DOC, "fixture.md"))
    titles = [c.headings_path[-1] for c in chunks]
    assert "First Section" in titles
    assert "Second Section" in titles
    # Each chunk has the document title at index 0
    for c in chunks:
        assert c.headings_path[0] == "The Document Title"


def test_chunk_doc_no_h2_emits_single_chunk():
    content = "# Doc Title\n\n" + ("This is a long enough body. " * 30)
    chunks = list(chunk_doc(content, "no_h2.md"))
    assert len(chunks) == 1
    assert chunks[0].chunk_idx == 0


def test_chunk_doc_assigns_phase_metadata():
    """Chunks from a doc referenced in routing should carry the phases list."""
    # interview_intro_positioning_guide.md is in routing under 'intro_question'
    content = "# Interview Intro Guide\n\n## Section One\n\n" + ("Body. " * 50)
    chunks = list(chunk_doc(content, "interview_intro_positioning_guide.md"))
    assert chunks
    assert "intro_question" in chunks[0].phases


def test_chunk_doc_unreferenced_doc_has_empty_phases():
    content = "# Random\n\n## Section\n\n" + ("Body. " * 50)
    chunks = list(chunk_doc(content, "some_random_doc_not_in_routing.md"))
    assert chunks
    assert chunks[0].phases == []


def test_chunk_doc_large_section_subsplits_at_h3():
    # H2 section larger than TARGET_CHUNK_CHARS, with H3 subsections
    big_paragraph = "Detailed paragraph content. " * 200  # ~5400 chars
    content = textwrap.dedent(f"""\
        # Doc Title

        ## Big Section

        {big_paragraph}

        ### Subsection A

        {big_paragraph}

        ### Subsection B

        {big_paragraph}
    """)
    chunks = list(chunk_doc(content, "big.md"))
    # Should produce multiple chunks, including the H3 subsections
    titles = [c.headings_path[-1] for c in chunks]
    assert "Subsection A" in titles
    assert "Subsection B" in titles


def test_chunk_doc_chunk_ids_unique_and_stable():
    chunks = list(chunk_doc(SIMPLE_DOC, "fixture.md"))
    ids = [c.id for c in chunks]
    assert len(ids) == len(set(ids))  # unique
    # Stable format: <doc_stem>__<slug>__<idx>
    for cid in ids:
        assert cid.count("__") >= 2


def test_chunk_doc_empty_returns_empty():
    assert list(chunk_doc("", "x.md")) == []
    assert list(chunk_doc("   \n\n  ", "x.md")) == []


# ════════════════════════════════════════════════════════════════════════════
# build_playbook — end-to-end with isolated source dir
# ════════════════════════════════════════════════════════════════════════════

def _seed_source_dir(tmp_path: Path) -> Path:
    src = tmp_path / "kb_source"
    src.mkdir()
    # Two valid docs
    (src / "interview_intro_positioning_guide.md").write_text(textwrap.dedent("""\
        # Intro Positioning Guide

        ## Opening Lines

        How to open with conviction in a 90-second introduction. The goal is
        to position yourself, not recite history. Lead with a punchy hook
        that signals seniority and immediately establishes the relevant axis
        for this specific role.

        ## Body Beats

        Three evidence beats with specific metrics. Each beat anchors a
        signal — leadership, ambiguity handling, or domain expertise. End
        with a clean handoff to the interviewer.
    """))
    (src / "interview_stories_positioning_guide.md").write_text(textwrap.dedent("""\
        # Stories Positioning Guide

        ## STAR Structure

        Situation, Task, Action, Result. The Action section dominates total
        speaking time. Use first-person 'I' for owned decisions. Quantify
        the outcome whenever possible — recruiters anchor on numbers.
    """))
    # One empty file (skip)
    (src / "empty.md").write_text("")
    return src


def test_build_playbook_happy_path(isolated_lr_home, tmp_path):
    src = _seed_source_dir(tmp_path)

    report = build_playbook(source_dir=src, embed_fn=fake_embed)

    assert report.docs_scanned == 3
    assert report.docs_chunked == 2  # empty file skipped
    assert report.chunks_total >= 2  # at least 2 H2 sections per doc
    assert report.chunks_embedded == report.chunks_total
    assert report.embedding_dim == 384
    assert any("empty.md" in s for s in report.skipped)

    # Output files present
    out = isolated_lr_home / "coaching_kb"
    assert (out / "playbook_chunks.jsonl").exists()
    assert (out / "playbook.npz").exists()


def test_build_playbook_persists_loadable_index(isolated_lr_home, tmp_path):
    src = _seed_source_dir(tmp_path)
    build_playbook(source_dir=src, embed_fn=fake_embed)

    chunks = load_playbook_chunks()
    assert len(chunks) >= 2

    ids, vecs = load_playbook_embeddings()
    assert len(ids) == len(chunks)
    assert vecs.shape[0] == len(ids)
    assert vecs.shape[1] == 384


def test_build_playbook_carries_phase_metadata(isolated_lr_home, tmp_path):
    """Chunks from intro_positioning doc should have intro_question phase."""
    src = _seed_source_dir(tmp_path)
    build_playbook(source_dir=src, embed_fn=fake_embed)

    chunks = load_playbook_chunks()
    intro_chunks = [c for c in chunks if c.doc_name == "interview_intro_positioning_guide.md"]
    assert intro_chunks
    assert all("intro_question" in c.phases for c in intro_chunks)


def test_build_playbook_missing_source_raises(isolated_lr_home, tmp_path):
    with pytest.raises(FileNotFoundError):
        build_playbook(source_dir=tmp_path / "does_not_exist", embed_fn=fake_embed)


def test_is_kb_built_false_before_build(isolated_lr_home):
    assert is_kb_built() is False


def test_is_kb_built_true_after_build(isolated_lr_home, tmp_path):
    src = _seed_source_dir(tmp_path)
    build_playbook(source_dir=src, embed_fn=fake_embed)
    assert is_kb_built() is True


def test_is_kb_built_false_when_chunks_empty(isolated_lr_home, tmp_path):
    """If source has only invalid docs → empty index → is_kb_built False."""
    src = tmp_path / "empty_src"
    src.mkdir()
    (src / "empty.md").write_text("")
    build_playbook(source_dir=src, embed_fn=fake_embed)
    assert is_kb_built() is False
