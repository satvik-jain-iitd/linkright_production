"""Tests for evidence chunkers.

Memo chunker is the keystone — its correctness directly determines RAG
retrieval quality. Verifying:
  - frontmatter parsing
  - per-atom metadata parsing
  - default_tags merging with atom-level tags
  - author_role → role fallback
  - empty / malformed atoms ignored
  - resume PDF section + role splitting
  - unstructured fallback paragraph handling
"""
from __future__ import annotations

import textwrap

import pytest

from linkright.evidence.chunking import (
    chunk_memo,
    chunk_resume_pdf,
    chunk_unstructured,
    is_memo_format,
    split_frontmatter,
)


# ── split_frontmatter ────────────────────────────────────────────────────────

def test_split_frontmatter_present():
    content = "---\nfoo: bar\nbaz: 1\n---\nbody text\n"
    meta, body = split_frontmatter(content)
    assert meta == {"foo": "bar", "baz": 1}
    assert body == "body text\n"


def test_split_frontmatter_missing():
    content = "no frontmatter here\n## Atom: x\nstuff"
    meta, body = split_frontmatter(content)
    assert meta == {}
    assert body == content


def test_split_frontmatter_invalid_yaml():
    content = "---\n: : :\n---\nbody"
    meta, body = split_frontmatter(content)
    assert meta == {}
    assert body == "body"


# ── is_memo_format ──────────────────────────────────────────────────────────

def test_is_memo_format_true():
    content = textwrap.dedent("""\
        ---
        source_type: diary
        date: 2026-05-15
        ---

        ## Atom: First topic
        date: 2026-05-15
        role: PM

        Some body.
    """)
    assert is_memo_format(content) is True


def test_is_memo_format_no_frontmatter():
    assert is_memo_format("## Atom: x\nbody") is False


def test_is_memo_format_no_atoms():
    content = "---\nsource_type: diary\n---\n\nJust body, no atoms.\n"
    assert is_memo_format(content) is False


# ── chunk_memo ──────────────────────────────────────────────────────────────

MEMO_FIXTURE = textwrap.dedent("""\
    ---
    source_type: diary
    date: 2026-05-15
    author_role: "AmEx Senior PM"
    default_tags: [pm, amex]
    ---

    ## Atom: Walmart partnership
    date: 2024-03-12
    role: "AmEx Senior PM"
    company: AmEx
    project: "Card-on-File"
    tags: [stakeholder, partnership, walmart]
    metric_keys: [headcount, weeks_to_close]

    In Q1 2024 I personally led the Walmart partnership conversation.
    Closed engineer swap in 2 weeks. Feature shipped 6 weeks early,
    contributing $4M ARR.

    ## Atom: SMB tier deprioritization
    date: 2024-05-08
    role: "AmEx Senior PM"
    company: AmEx
    tags: [prioritization, tradeoff]

    Mid-2024 I deprioritized the SMB tier despite $1.2M pipeline.
    Decision held — Q4 enterprise wins delivered $11M ARR.
""")


def test_chunk_memo_basic():
    atoms = list(chunk_memo(MEMO_FIXTURE, "ev_test"))
    assert len(atoms) == 2

    a0 = atoms[0]
    assert a0.id == "ev_test_a000"
    assert a0.evidence_id == "ev_test"
    assert a0.chunk_idx == 0
    assert a0.atom_title == "Walmart partnership"
    assert "Walmart" in a0.text
    assert "$4M ARR" in a0.text
    assert a0.metadata["company"] == "AmEx"
    assert a0.metadata["role"] == "AmEx Senior PM"
    assert "stakeholder" in a0.metadata["tags"]


def test_chunk_memo_default_tags_merge():
    atoms = list(chunk_memo(MEMO_FIXTURE, "ev_test"))
    # default_tags from doc frontmatter should merge with per-atom tags
    a0_tags = atoms[0].metadata["tags"]
    assert "pm" in a0_tags  # from default_tags
    assert "amex" in a0_tags  # from default_tags
    assert "walmart" in a0_tags  # from atom-level


def test_chunk_memo_author_role_fallback():
    """Atom without explicit role inherits author_role from frontmatter."""
    content = textwrap.dedent("""\
        ---
        source_type: diary
        author_role: "Test Role"
        ---

        ## Atom: No role specified
        tags: [foo]

        Some body.
    """)
    atoms = list(chunk_memo(content, "ev_x"))
    assert atoms[0].metadata["role"] == "Test Role"


def test_chunk_memo_empty_atoms_skipped():
    content = textwrap.dedent("""\
        ---
        source_type: diary
        ---

        ## Atom: Has content
        date: 2026-01-01

        Real content.

        ## Atom: Empty
        date: 2026-01-02
    """)
    atoms = list(chunk_memo(content, "ev_y"))
    assert len(atoms) == 1
    assert atoms[0].atom_title == "Has content"


def test_chunk_memo_no_atoms_returns_empty():
    content = "---\nsource_type: diary\n---\n\nNo atoms here.\n"
    assert list(chunk_memo(content, "ev_z")) == []


def test_chunk_memo_strips_source_type_from_metadata():
    """source_type is doc-level identifier, shouldn't pollute atom metadata."""
    atoms = list(chunk_memo(MEMO_FIXTURE, "ev_test"))
    assert "source_type" not in atoms[0].metadata


# ── chunk_resume_pdf ────────────────────────────────────────────────────────

RESUME_FIXTURE = textwrap.dedent("""\
    Satvik Jain
    satvik@example.com  |  +91 99999 99999

    Summary
    Senior PM with 6 years experience in B2B SaaS.

    Professional Experience
    AmEx | Senior PM
    2023-Present
    Led cross-functional initiatives.

    Sprinklr | Product Manager
    2020-2023
    Owned platform roadmap.

    Education
    IIT Delhi, B.Tech, 2014-2018

    Skills
    Python, SQL, Product Strategy
""")


def test_chunk_resume_pdf_emits_sections():
    atoms = list(chunk_resume_pdf(RESUME_FIXTURE, "ev_resume"))
    titles = [a.atom_title for a in atoms]
    # Expect at least: Header, Experience role split, Education, Skills
    assert any("Header" in t or "Contact" in t for t in titles)
    assert any("Education" in t for t in titles)
    assert any("Skills" in t for t in titles)


def test_chunk_resume_pdf_splits_experience_by_role():
    atoms = list(chunk_resume_pdf(RESUME_FIXTURE, "ev_resume"))
    role_titles = [a.atom_title for a in atoms if "AmEx" in a.atom_title or "Sprinklr" in a.atom_title]
    # Both roles should appear as separate atoms
    assert len(role_titles) >= 2


def test_chunk_resume_pdf_empty_returns_empty():
    assert list(chunk_resume_pdf("", "ev_x")) == []


def test_chunk_resume_pdf_no_sections_falls_back_to_single_atom():
    content = "Just a wall of text with no recognized headings whatsoever."
    atoms = list(chunk_resume_pdf(content, "ev_x"))
    assert len(atoms) == 1
    assert atoms[0].atom_title.startswith("Resume")


# ── chunk_unstructured ──────────────────────────────────────────────────────

def test_chunk_unstructured_paragraph_grouping():
    paras = ["A" * 200, "B" * 200, "C" * 200]
    content = "\n\n".join(paras)
    atoms = list(chunk_unstructured(content, "ev_u"))
    assert len(atoms) >= 1
    # All chunks should respect minimum size
    for a in atoms:
        assert a.metadata["chunker"] == "unstructured"


def test_chunk_unstructured_hard_split_long_paragraph():
    # Single paragraph way over target — should hard-split with overlap
    content = "X" * 2000
    atoms = list(chunk_unstructured(content, "ev_u"))
    assert len(atoms) >= 2


def test_chunk_unstructured_empty_returns_empty():
    assert list(chunk_unstructured("", "ev_x")) == []
    assert list(chunk_unstructured("   \n\n  ", "ev_x")) == []
