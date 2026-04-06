"""Tests for worker/app/tools/nugget_embedder.py

Story 4.5: 6 tests covering embedding shape, field selection,
failure handling, and tagging behavior.
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
    {"SUPABASE_URL": "https://fake.supabase.co", "SUPABASE_KEY": "fake-key"},
)
_env_patch.start()

_WORKER_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _WORKER_ROOT not in sys.path:
    sys.path.insert(0, os.path.abspath(_WORKER_ROOT))

from app.tools.nugget_embedder import embed_nuggets  # noqa: E402
from app.tools.nugget_extractor import Nugget  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Regex pattern matching Gemini embedContent URL regardless of query params
_GEMINI_EMBED_URL = re.compile(
    r"https://generativelanguage\.googleapis\.com/v1beta/models/"
    r"text-embedding-005:embedContent"
)

# Fake 768-dim vector
_FAKE_VECTOR: list[float] = [0.1] * 768


def _gemini_response(vector: list[float] | None = None) -> dict:
    """Build a minimal Gemini embedContent response."""
    vec = vector if vector is not None else _FAKE_VECTOR
    return {"embedding": {"values": vec}}


def _make_nugget(
    index: int = 0,
    answer: str = "Led 18-member cross-functional team reducing risk errors from 18% to 2%",
    nugget_id: str = "nugget-id-1",
) -> Nugget:
    """Build a minimal Nugget with the given answer."""
    n = Nugget(
        nugget_index=index,
        nugget_text="Led 18-member team",
        question="What did you lead?",
        alt_questions=["Team size?"],
        answer=answer,
        primary_layer="A",
        section_type="work_experience",
        importance="P0",
        factuality="fact",
        temporality="past",
    )
    n.id = nugget_id
    return n


# ---------------------------------------------------------------------------
# 1. test_embed_returns_list_of_vectors
# ---------------------------------------------------------------------------

def test_embed_returns_list_of_vectors(httpx_mock, fake_sb):
    """embed_nuggets returns list[list[float]]."""
    httpx_mock.add_response(
        url=_GEMINI_EMBED_URL,
        json=_gemini_response(),
    )

    nuggets = [_make_nugget(0)]
    result = asyncio.run(
        embed_nuggets(nuggets, "fake-gemini-key", fake_sb, "user-123")
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], list)
    assert all(isinstance(v, float) for v in result[0])


# ---------------------------------------------------------------------------
# 2. test_embed_768_dimensions
# ---------------------------------------------------------------------------

def test_embed_768_dimensions(httpx_mock, fake_sb):
    """Each returned embedding vector has exactly 768 floats."""
    httpx_mock.add_response(
        url=_GEMINI_EMBED_URL,
        json=_gemini_response(_FAKE_VECTOR),
    )

    nuggets = [_make_nugget(0)]
    result = asyncio.run(
        embed_nuggets(nuggets, "fake-gemini-key", fake_sb, "user-123")
    )

    assert len(result) == 1
    assert len(result[0]) == 768


# ---------------------------------------------------------------------------
# 3. test_embed_uses_answer_field
# ---------------------------------------------------------------------------

def test_embed_uses_answer_field(httpx_mock, fake_sb):
    """Gemini is called with nugget.answer text, not nugget_text."""
    answer_text = "Reduced p99 latency from 200ms to 40ms through async queue redesign"
    captured_bodies: list[dict] = []

    def capture_request(request):
        import json as _json
        try:
            body = _json.loads(request.content)
            captured_bodies.append(body)
        except Exception:
            pass
        import httpx as _httpx
        return _httpx.Response(200, json=_gemini_response())

    httpx_mock.add_callback(capture_request, url=_GEMINI_EMBED_URL)

    nugget = _make_nugget(0, answer=answer_text)
    asyncio.run(embed_nuggets([nugget], "fake-gemini-key", fake_sb, "user-123"))

    assert len(captured_bodies) == 1
    # The Gemini request body has content.parts[0].text == answer
    parts = captured_bodies[0]["content"]["parts"]
    assert parts[0]["text"] == answer_text


# ---------------------------------------------------------------------------
# 4. test_null_embedding_on_failure
# ---------------------------------------------------------------------------

def test_null_embedding_on_failure(httpx_mock, fake_sb):
    """Gemini 500 → empty list [] for that nugget's slot."""
    httpx_mock.add_response(
        url=_GEMINI_EMBED_URL,
        status_code=500,
    )

    nuggets = [_make_nugget(0)]
    result = asyncio.run(
        embed_nuggets(nuggets, "fake-gemini-key", fake_sb, "user-123")
    )

    assert result == [[]]


# ---------------------------------------------------------------------------
# 5. test_needs_embedding_tag_on_failure
# ---------------------------------------------------------------------------

def test_needs_embedding_tag_on_failure(httpx_mock, fake_sb):
    """Gemini 500 → failed nugget gets 'needs_embedding' tag in DB."""
    httpx_mock.add_response(
        url=_GEMINI_EMBED_URL,
        status_code=500,
    )

    # Pre-populate career_nuggets row with the nugget's id
    nugget_id = "nugget-abc-123"
    fake_sb.table("career_nuggets").rows.append(
        {"id": nugget_id, "tags": [], "user_id": "user-123"}
    )

    nugget = _make_nugget(0, nugget_id=nugget_id)
    asyncio.run(embed_nuggets([nugget], "fake-gemini-key", fake_sb, "user-123"))

    # Check DB row was updated with needs_embedding tag
    rows = fake_sb.table("career_nuggets").rows
    matching = [r for r in rows if r.get("id") == nugget_id]
    assert len(matching) == 1
    assert "needs_embedding" in matching[0].get("tags", [])


# ---------------------------------------------------------------------------
# 6. test_no_exception_on_total_failure
# ---------------------------------------------------------------------------

@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_no_exception_on_total_failure(httpx_mock, fake_sb):
    """All Gemini calls fail → returns list of [] entries, no exception raised."""
    import httpx as _httpx

    # Provide enough exceptions for 3 nuggets (each with up to 5 retry attempts)
    for _ in range(15):
        httpx_mock.add_exception(
            _httpx.ConnectError("Connection refused"),
            url=_GEMINI_EMBED_URL,
        )

    nuggets = [_make_nugget(i, nugget_id=f"nid-{i}") for i in range(3)]

    result = asyncio.run(
        embed_nuggets(nuggets, "fake-gemini-key", fake_sb, "user-123")
    )

    assert isinstance(result, list)
    assert all(slot == [] for slot in result)
