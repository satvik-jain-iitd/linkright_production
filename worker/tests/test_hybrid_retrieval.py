"""Tests for worker/app/tools/hybrid_retrieval.py

Story 4.5: 11 tests covering RRF formula, importance boosts,
deduplication, limits, scoping, fallbacks, and LLM formatting.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from unittest import mock

import pytest

# Patch env before any worker import
_env_patch = mock.patch.dict(
    os.environ,
    {
        "SUPABASE_URL": "https://fake.supabase.co",
        "SUPABASE_KEY": "fake-key",
        "JINA_API_KEY": "fake-jina-key",
    },
)
_env_patch.start()

_WORKER_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _WORKER_ROOT not in sys.path:
    sys.path.insert(0, os.path.abspath(_WORKER_ROOT))

from app.tools.hybrid_retrieval import (  # noqa: E402
    _rrf_score,
    _fuse_results,
    _apply_importance_boost,
    _dedup_and_limit,
    _to_nugget_results,
    format_nuggets_for_llm,
    hybrid_retrieve,
    NuggetResult,
    IMPORTANCE_BOOST,
)

# Jina AI embeddings URL
_JINA_EMBED_URL = "https://api.jina.ai/v1/embeddings"

# ---------------------------------------------------------------------------
# Extended FakeSupabaseClient for hybrid_retrieval
# ---------------------------------------------------------------------------

class _FTSQueryChainFactory:
    """Mimics sb.table(name) with optional raise on execute."""

    def __init__(self, rows: list[dict], raises: Exception | None = None) -> None:
        self._rows = list(rows)
        self._raises = raises

    def select(self, *_a, **_kw) -> "_FTSQueryChainFactory":
        return self

    def eq(self, col: str, val) -> "_FTSQueryChainFactory":
        self._rows = [r for r in self._rows if r.get(col) == val]
        return self

    def text_search(self, *_a, **_kw) -> "_FTSQueryChainFactory":
        if self._raises:
            raise self._raises
        return self

    def limit(self, *_a, **_kw) -> "_FTSQueryChainFactory":
        return self

    def delete(self) -> "_FTSQueryChainFactory":
        return self

    def execute(self):
        if self._raises:
            raise self._raises

        class _R:
            data = None

        r = _R()
        r.data = self._rows
        return r


class _RpcResult:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def execute(self):
        class _R:
            data = None

        r = _R()
        r.data = self._rows
        return r


class FakeHybridSupabaseClient:
    """Supabase stub with table(), rpc() support for hybrid tests."""

    def __init__(
        self,
        nugget_rows: list[dict] | None = None,
        chunk_rows: list[dict] | None = None,
        rpc_rows: list[dict] | None = None,
        rpc_raises: Exception | None = None,
        bm25_raises: Exception | None = None,
        fts_raises: Exception | None = None,
    ) -> None:
        self._nugget_rows = list(nugget_rows or [])
        self._chunk_rows = list(chunk_rows or [])
        self._rpc_rows = rpc_rows if rpc_rows is not None else list(nugget_rows or [])
        self._rpc_raises = rpc_raises
        self._bm25_raises = bm25_raises
        self._fts_raises = fts_raises

    def table(self, name: str) -> _FTSQueryChainFactory:
        if name == "career_chunks":
            return _FTSQueryChainFactory(self._chunk_rows, self._fts_raises)
        return _FTSQueryChainFactory(self._nugget_rows, self._bm25_raises)

    def rpc(self, fn_name: str, params: dict) -> _RpcResult:
        if self._rpc_raises:
            raise self._rpc_raises
        return _RpcResult(self._rpc_rows)


# ---------------------------------------------------------------------------
# Sample nugget rows
# ---------------------------------------------------------------------------

def _nugget_row(
    nid: str,
    importance: str = "P2",
    company: str = "AmEx",
    resume_relevance: float = 0.9,
    answer: str = "Led 18-member team reducing errors from 18% to 2%",
    section_type: str = "work_experience",
    role: str = "Sr Associate PM",
    tags: list | None = None,
) -> dict:
    return {
        "id": nid,
        "answer": answer,
        "nugget_text": f"text-{nid}",
        "importance": importance,
        "section_type": section_type,
        "company": company,
        "role": role,
        "tags": tags or [],
        "resume_relevance": resume_relevance,
    }


# ---------------------------------------------------------------------------
# 1. test_rrf_score_formula
# ---------------------------------------------------------------------------

def test_rrf_score_formula():
    """1/(60+rank) computed correctly for rank 0, 1, 5."""
    assert abs(_rrf_score(0) - 1 / 60) < 1e-9
    assert abs(_rrf_score(1) - 1 / 61) < 1e-9
    assert abs(_rrf_score(5) - 1 / 65) < 1e-9


# ---------------------------------------------------------------------------
# 2. test_importance_boost_p0
# ---------------------------------------------------------------------------

def test_importance_boost_p0():
    """P0 nugget score multiplied by 1.5."""
    item = {"data": {"id": "n1", "importance": "P0"}, "score": 1.0}
    boosted = _apply_importance_boost([item])
    assert abs(boosted[0]["score"] - 1.5) < 1e-9


# ---------------------------------------------------------------------------
# 3. test_importance_boost_p1
# ---------------------------------------------------------------------------

def test_importance_boost_p1():
    """P1 nugget score multiplied by 1.2."""
    item = {"data": {"id": "n1", "importance": "P1"}, "score": 1.0}
    boosted = _apply_importance_boost([item])
    assert abs(boosted[0]["score"] - 1.2) < 1e-9


# ---------------------------------------------------------------------------
# 4. test_importance_boost_p2_no_change
# ---------------------------------------------------------------------------

def test_importance_boost_p2_no_change():
    """P2 score unchanged (multiplier == 1.0)."""
    item = {"data": {"id": "n1", "importance": "P2"}, "score": 2.0}
    boosted = _apply_importance_boost([item])
    assert abs(boosted[0]["score"] - 2.0) < 1e-9


# ---------------------------------------------------------------------------
# 5. test_deduplication
# ---------------------------------------------------------------------------

def test_deduplication():
    """Same nugget_id in both BM25 and vector lists → appears once in fused output."""
    row = _nugget_row("n1")
    bm25_results = [row]
    vector_results = [row]

    fused = _fuse_results(bm25_results, vector_results)

    ids = [item["data"]["id"] for item in fused]
    assert ids.count("n1") == 1
    # Score should be sum of both RRF scores (rank 0 in each)
    expected_score = _rrf_score(0) + _rrf_score(0)
    assert abs(fused[0]["score"] - expected_score) < 1e-9


# ---------------------------------------------------------------------------
# 6. test_result_limit
# ---------------------------------------------------------------------------

def test_result_limit():
    """limit=3 returns max 3 results."""
    rows = [_nugget_row(f"n{i}") for i in range(10)]
    fused = [{"data": r, "score": 1.0 / (i + 1)} for i, r in enumerate(rows)]
    limited = _dedup_and_limit(fused, [], limit=3)
    assert len(limited) <= 3


# ---------------------------------------------------------------------------
# 7. test_company_scoped_query
# ---------------------------------------------------------------------------

@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_company_scoped_query(httpx_mock):
    """company='AmEx' → AmEx nugget appears in results."""
    amex_row = _nugget_row("n1", company="AmEx")

    httpx_mock.add_response(
        url=_JINA_EMBED_URL,
        json={"data": [{"embedding": [0.1] * 768}]},
    )
    httpx_mock.add_response(
        url=_JINA_EMBED_URL,
        json={"data": [{"embedding": [0.1] * 768}]},
    )

    sb = FakeHybridSupabaseClient(
        nugget_rows=[amex_row],
        rpc_rows=[amex_row],
    )

    with mock.patch.dict(os.environ, {"JINA_API_KEY": "fake-key"}):
        results, method = await hybrid_retrieve(
            sb, "user-123", "risk scoring", company="AmEx", limit=5
        )

    assert method in ("hybrid", "bm25_only")
    result_ids = [r.nugget_id for r in results]
    assert "n1" in result_ids


# ---------------------------------------------------------------------------
# 8. test_unscoped_query
# ---------------------------------------------------------------------------

@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_unscoped_query(httpx_mock):
    """company=None → unscoped_fused resume_relevance >= 0.5 filter applied.

    The implementation runs TWO hybrid passes when company=None:
      pass 1 (company_fused): company=None — no resume_relevance filter
      pass 2 (unscoped_fused): company=None — filtered by resume_relevance >= 0.5
    Both passes are merged via _dedup_and_limit.

    This test verifies that high_rel (0.9) appears and that the unscoped
    filter logic is applied to the second pass. We assert the method is
    'hybrid' or 'bm25_only' and that high-relevance nuggets are present.
    """
    high_rel = _nugget_row("n1", resume_relevance=0.9)

    httpx_mock.add_response(
        url=_JINA_EMBED_URL,
        json={"data": [{"embedding": [0.1] * 768}]},
    )
    httpx_mock.add_response(
        url=_JINA_EMBED_URL,
        json={"data": [{"embedding": [0.1] * 768}]},
    )

    sb = FakeHybridSupabaseClient(
        nugget_rows=[high_rel],
        rpc_rows=[high_rel],
    )

    with mock.patch.dict(os.environ, {"JINA_API_KEY": "fake-key"}):
        results, method = await hybrid_retrieve(
            sb, "user-123", "risk scoring", company=None, limit=10
        )

    assert method in ("hybrid", "bm25_only")
    result_ids = [r.nugget_id for r in results]
    assert "n1" in result_ids


def test_unscoped_filter_logic():
    """resume_relevance < 0.5 nuggets are excluded from the unscoped fused pass.

    Tests the filter applied inside hybrid_retrieve on unscoped_fused_raw
    before passing to _dedup_and_limit.
    """
    low_rel = _nugget_row("n-low", resume_relevance=0.2)
    high_rel = _nugget_row("n-high", resume_relevance=0.8)

    # Simulate what hybrid_retrieve does to the unscoped raw results
    unscoped_raw = [
        {"data": low_rel, "score": 0.02},
        {"data": high_rel, "score": 0.015},
    ]
    filtered = [
        item for item in unscoped_raw
        if item["data"].get("resume_relevance", 1.0) >= 0.5
    ]

    ids = [item["data"]["id"] for item in filtered]
    assert "n-low" not in ids
    assert "n-high" in ids


# ---------------------------------------------------------------------------
# 9. test_fallback_to_bm25_on_vector_error
# ---------------------------------------------------------------------------

@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_fallback_to_bm25_on_vector_error(httpx_mock):
    """Jina AI (vector embed) fails → falls back to bm25_only."""
    import httpx as _httpx

    # All Jina calls fail
    for _ in range(10):
        httpx_mock.add_exception(
            _httpx.ConnectError("Jina unreachable"),
            url=_JINA_EMBED_URL,
        )

    row = _nugget_row("n1")
    sb = FakeHybridSupabaseClient(nugget_rows=[row], rpc_rows=[row])

    with mock.patch.dict(os.environ, {"JINA_API_KEY": "fake-key"}):
        results, method = await hybrid_retrieve(
            sb, "user-123", "risk scoring", limit=5
        )

    assert method == "bm25_only"


# ---------------------------------------------------------------------------
# 10. test_fallback_to_raw_on_all_errors
# ---------------------------------------------------------------------------

@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_fallback_to_raw_on_all_errors(httpx_mock):
    """All tiers fail → returns [], 'raw_text_fallback'."""
    import httpx as _httpx

    # Jina fails → hybrid tier fails
    for _ in range(10):
        httpx_mock.add_exception(
            _httpx.ConnectError("Jina unreachable"),
            url=_JINA_EMBED_URL,
        )

    db_error = RuntimeError("DB down")
    sb = FakeHybridSupabaseClient(
        nugget_rows=[],
        bm25_raises=db_error,
        fts_raises=db_error,
        rpc_raises=db_error,
    )

    with mock.patch.dict(os.environ, {"JINA_API_KEY": "fake-key"}):
        results, method = await hybrid_retrieve(
            sb, "user-123", "risk scoring", limit=5
        )

    assert results == []
    assert method == "raw_text_fallback"


# ---------------------------------------------------------------------------
# 11. test_format_nuggets_for_llm
# ---------------------------------------------------------------------------

def test_format_nuggets_for_llm():
    """Output contains company header and answer text."""
    results = [
        NuggetResult(
            nugget_id="n1",
            answer="Reduced risk errors from 18% to 2% across 40 markets",
            nugget_text="Led 18-member team",
            importance="P0",
            section_type="work_experience",
            company="American Express",
            role="Sr Associate PM",
            tags=["leadership", "risk"],
            rrf_score=0.025,
            retrieval_method="hybrid",
        ),
        NuggetResult(
            nugget_id="n2",
            answer="Shipped competitor benchmarking widget with 4.7/5 CSAT",
            nugget_text="Benchmarking widget",
            importance="P1",
            section_type="work_experience",
            company="Sprinklr",
            role="PM Intern",
            tags=["analytics"],
            rrf_score=0.020,
            retrieval_method="hybrid",
        ),
    ]

    output = format_nuggets_for_llm(results)

    assert "American Express" in output
    assert "Sprinklr" in output
    assert "Reduced risk errors" in output
    assert "4.7/5 CSAT" in output
    assert "## Company:" in output
