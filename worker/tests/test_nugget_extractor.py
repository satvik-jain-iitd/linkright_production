"""Tests for worker/app/tools/nugget_extractor.py

Story 4.5: 14 tests covering extraction, layer classification,
error handling, retry logic, and DB interaction.
"""

from __future__ import annotations

import asyncio
import json
import os
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

from app.tools.nugget_extractor import extract_nuggets, Nugget  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_SAMPLE_NUGGET_A = {
    "nugget_text": "Led 18-member team",
    "question": "What did you lead?",
    "alt_questions": ["Team size?", "What was the project?"],
    "answer": "Led 18-member cross-functional team reducing risk errors from 18% to 2%",
    "primary_layer": "A",
    "section_type": "work_experience",
    "life_domain": None,
    "resume_relevance": 0.9,
    "resume_section_target": "experience",
    "importance": "P0",
    "factuality": "fact",
    "temporality": "past",
    "company": "American Express",
    "role": "Sr Associate PM",
    "tags": ["leadership", "ML", "risk"],
    "leadership_signal": "team_lead",
}

_SAMPLE_NUGGET_B = {
    "nugget_text": "Relocated to New Delhi for career growth",
    "question": "Why did you relocate?",
    "alt_questions": ["Where are you based?"],
    "answer": "Relocated from Pune to New Delhi in 2022 to join American Express and grow in FinTech",
    "primary_layer": "B",
    "section_type": None,
    "life_domain": "Logistics",
    "resume_relevance": 0.3,
    "resume_section_target": None,
    "importance": "P3",
    "factuality": "fact",
    "temporality": "past",
    "company": None,
    "role": None,
    "tags": ["relocation"],
    "leadership_signal": "none",
}


def _nugget_to_markdown(nugget: dict) -> str:
    """Render a nugget dict as the markdown format the extractor parses
    (matches `_parse_markdown_nuggets` in worker/app/tools/nugget_extractor.py).
    """
    parts = ["## nugget"]
    # Map the test-fixture key names to the markdown keys the parser reads.
    # `nugget_text`, `question`, `alt_questions` are NOT consumed by the
    # markdown parser — only `type`/`section_type`, `company`, `role`,
    # `importance`, `answer`, `tags` matter.
    # Layer B nuggets (life domain) — derive type from life_domain when
    # section_type is None, so the F05 work-experience-must-have-company
    # validator doesn't drop them.
    section_type = nugget.get("section_type") or nugget.get("type")
    if not section_type:
        if nugget.get("life_domain"):
            section_type = nugget["life_domain"].lower()
        else:
            section_type = "work_experience"
    parts.append(f"type: {section_type}")
    if nugget.get("company") is not None:
        parts.append(f"company: {nugget['company']}")
    if nugget.get("role") is not None:
        parts.append(f"role: {nugget['role']}")
    parts.append(f"importance: {nugget.get('importance', 'P2')}")
    parts.append(f"answer: {nugget.get('answer', '')}")
    tags = nugget.get("tags") or []
    if tags:
        parts.append(f"tags: {', '.join(tags)}")
    if nugget.get("life_domain"):
        parts.append(f"life_domain: {nugget['life_domain']}")
    if nugget.get("primary_layer"):
        parts.append(f"primary_layer: {nugget['primary_layer']}")
    return "\n".join(parts)


def _groq_response(nuggets: list[dict]) -> dict:
    """Build a minimal Groq API response envelope.

    Extractor switched from JSON → Markdown output in commit b12a184
    ("nugget extractor markdown switch"). The mocked response now emits the
    same `## nugget` block format that the production prompt asks for and
    that `_parse_markdown_nuggets` consumes.
    """
    # Keep `json` import alive for tests that mock other JSON payloads.
    _ = json  # noqa: F841
    markdown = "\n\n".join(_nugget_to_markdown(n) for n in nuggets)
    return {
        "choices": [
            {"message": {"content": markdown}}
        ]
    }


# Career text that fits in one batch (< 3000 chars)
_LONG_TEXT = (
    "American Express — New Delhi. Senior Associate Product Manager, Credit Risk. "
    "Led 18-member cross-functional team to redesign risk scoring pipeline, reducing "
    "errors from 18% to 2%. Drove GenAI root-cause analyzer from 0 to 85% coverage "
    "across 100M+ accounts. Owned DCLA feature shipped in 3 sprints."
)

# ---------------------------------------------------------------------------
# 1. test_extraction_returns_list
# ---------------------------------------------------------------------------

def test_extraction_returns_list(httpx_mock, fake_sb):
    """extract_nuggets with mocked Groq returns list[Nugget]."""
    httpx_mock.add_response(url=_GROQ_URL, json=_groq_response([_SAMPLE_NUGGET_A]))

    nuggets = asyncio.run(
        extract_nuggets("user-123", _LONG_TEXT, fake_sb, groq_api_key="fake-key")
    )
    assert isinstance(nuggets, list)
    assert len(nuggets) >= 1
    assert all(isinstance(n, Nugget) for n in nuggets)


# ---------------------------------------------------------------------------
# 2. test_extraction_count_15_to_25
# ---------------------------------------------------------------------------

@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_extraction_count_15_to_25(httpx_mock, fake_sb):
    """Satvik fixture text → Groq returns 20 nuggets → list has 15-25 nuggets."""
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    with open(os.path.join(fixtures_dir, "career_satvik.txt"), encoding="utf-8") as fh:
        career_text = fh.read()

    # Build 20 nuggets — satvik text splits into 2 batches, mock both
    twenty_nuggets = [dict(_SAMPLE_NUGGET_A, nugget_text=f"Achievement #{i}") for i in range(20)]
    ten_nuggets = twenty_nuggets[:10]

    # Each batch call gets a response (mock both; second may or may not be used)
    httpx_mock.add_response(url=_GROQ_URL, json=_groq_response(ten_nuggets))
    httpx_mock.add_response(url=_GROQ_URL, json=_groq_response(ten_nuggets))

    with mock.patch("asyncio.sleep", return_value=None):
        nuggets = asyncio.run(
            extract_nuggets("user-satvik", career_text, fake_sb, groq_api_key="fake-key")
        )
    assert 15 <= len(nuggets) <= 25


# ---------------------------------------------------------------------------
# 3. test_layer_a_classification
# ---------------------------------------------------------------------------

def test_layer_a_classification(httpx_mock, fake_sb):
    """Nugget with work_experience → primary_layer == 'A'."""
    httpx_mock.add_response(url=_GROQ_URL, json=_groq_response([_SAMPLE_NUGGET_A]))

    nuggets = asyncio.run(
        extract_nuggets("user-123", _LONG_TEXT, fake_sb, groq_api_key="fake-key")
    )
    layer_a = [n for n in nuggets if n.primary_layer == "A"]
    assert len(layer_a) >= 1
    assert layer_a[0].section_type == "work_experience"


# ---------------------------------------------------------------------------
# 4. test_layer_b_classification
# ---------------------------------------------------------------------------

def test_layer_b_classification(httpx_mock, fake_sb):
    """Personal/life nugget → primary_layer == 'B'."""
    httpx_mock.add_response(url=_GROQ_URL, json=_groq_response([_SAMPLE_NUGGET_B]))

    nuggets = asyncio.run(
        extract_nuggets("user-123", _LONG_TEXT, fake_sb, groq_api_key="fake-key")
    )
    layer_b = [n for n in nuggets if n.primary_layer == "B"]
    assert len(layer_b) >= 1
    assert layer_b[0].life_domain == "Logistics"


# ---------------------------------------------------------------------------
# 5. test_groq_rate_limit_fallback
# ---------------------------------------------------------------------------

@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_groq_rate_limit_fallback(httpx_mock, fake_sb):
    """Primary key 429s exhaust → BYOK key tried and succeeds."""
    # Primary key: all 5 attempts 429 (initial + 4 backoffs)
    for _ in range(5):
        httpx_mock.add_response(url=_GROQ_URL, status_code=429)
    # BYOK key succeeds
    httpx_mock.add_response(url=_GROQ_URL, json=_groq_response([_SAMPLE_NUGGET_A]))

    with mock.patch("asyncio.sleep", return_value=None):
        nuggets = asyncio.run(
            extract_nuggets(
                "user-123",
                _LONG_TEXT,
                fake_sb,
                groq_api_key="primary-key",
                byok_api_key="byok-key",
            )
        )

    assert isinstance(nuggets, list)
    assert len(nuggets) >= 1


# ---------------------------------------------------------------------------
# 6. test_malformed_json_retry
# ---------------------------------------------------------------------------

def test_malformed_json_retry(httpx_mock, fake_sb):
    """Bad JSON first call → fix prompt sent → good JSON second call → nuggets returned."""
    bad_json = '{"invalid json here...['
    good_response = _groq_response([_SAMPLE_NUGGET_A])

    # First call: extraction returns bad JSON
    httpx_mock.add_response(
        url=_GROQ_URL,
        json={"choices": [{"message": {"content": bad_json}}]},
    )
    # Second call: fix prompt returns good JSON
    httpx_mock.add_response(url=_GROQ_URL, json=good_response)

    nuggets = asyncio.run(
        extract_nuggets("user-123", _LONG_TEXT, fake_sb, groq_api_key="fake-key")
    )
    assert isinstance(nuggets, list)
    assert len(nuggets) >= 1


# ---------------------------------------------------------------------------
# 7. test_malformed_json_both_fail
# ---------------------------------------------------------------------------

def test_malformed_json_both_fail(httpx_mock, fake_sb):
    """Bad JSON on both calls → empty list, no exception raised."""
    bad_json = 'not json at all %%'

    # First call: bad JSON
    httpx_mock.add_response(
        url=_GROQ_URL,
        json={"choices": [{"message": {"content": bad_json}}]},
    )
    # Second call (fix prompt): still bad JSON
    httpx_mock.add_response(
        url=_GROQ_URL,
        json={"choices": [{"message": {"content": bad_json}}]},
    )

    nuggets = asyncio.run(
        extract_nuggets("user-123", _LONG_TEXT, fake_sb, groq_api_key="fake-key")
    )
    assert nuggets == []


# ---------------------------------------------------------------------------
# 8. test_empty_career_text
# ---------------------------------------------------------------------------

def test_empty_career_text(httpx_mock, fake_sb):
    """Empty string → empty list, no HTTP call made."""
    nuggets = asyncio.run(
        extract_nuggets("user-123", "", fake_sb, groq_api_key="fake-key")
    )
    assert nuggets == []
    # No HTTP requests should have been made
    assert httpx_mock.get_requests() == []


# ---------------------------------------------------------------------------
# 9. test_short_career_text
# ---------------------------------------------------------------------------

def test_short_career_text(httpx_mock, fake_sb):
    """< 50 chars → empty list returned, no HTTP call."""
    nuggets = asyncio.run(
        extract_nuggets("user-123", "Short text.", fake_sb, groq_api_key="fake-key")
    )
    assert nuggets == []
    assert httpx_mock.get_requests() == []


# ---------------------------------------------------------------------------
# 10. test_metadata_completeness
# ---------------------------------------------------------------------------

def test_metadata_completeness(httpx_mock, fake_sb):
    """Each nugget has importance, factuality, temporality fields."""
    httpx_mock.add_response(url=_GROQ_URL, json=_groq_response([_SAMPLE_NUGGET_A]))

    nuggets = asyncio.run(
        extract_nuggets("user-123", _LONG_TEXT, fake_sb, groq_api_key="fake-key")
    )
    assert len(nuggets) >= 1
    for n in nuggets:
        assert hasattr(n, "importance")
        assert hasattr(n, "factuality")
        assert hasattr(n, "temporality")
        assert n.importance in ("P0", "P1", "P2", "P3")
        assert n.factuality in ("fact", "opinion", "aspiration")
        assert n.temporality in ("past", "present", "future")


# ---------------------------------------------------------------------------
# 11. test_qa_answer_self_contained
# ---------------------------------------------------------------------------

def test_qa_answer_self_contained(httpx_mock, fake_sb):
    """answer field should be > 30 chars (self-contained per system prompt)."""
    httpx_mock.add_response(url=_GROQ_URL, json=_groq_response([_SAMPLE_NUGGET_A]))

    nuggets = asyncio.run(
        extract_nuggets("user-123", _LONG_TEXT, fake_sb, groq_api_key="fake-key")
    )
    assert len(nuggets) >= 1
    for n in nuggets:
        assert len(n.answer) > 30, f"Answer too short: '{n.answer}'"


# ---------------------------------------------------------------------------
# 12. test_re_upload_deletes_old
# ---------------------------------------------------------------------------

def test_re_upload_deletes_old(httpx_mock, fake_sb):
    """DELETE called on career_nuggets before INSERT (re-upload scenario).

    FakeTable does not implement .delete() — the implementation catches this
    exception and logs a warning. We verify the new nugget is inserted despite
    the delete failure (partial success case).
    """
    httpx_mock.add_response(url=_GROQ_URL, json=_groq_response([_SAMPLE_NUGGET_A]))

    asyncio.run(
        extract_nuggets("user-123", _LONG_TEXT, fake_sb, groq_api_key="fake-key")
    )

    # New nugget must be inserted even when delete raises
    rows = fake_sb.table("career_nuggets").rows
    new_rows = [r for r in rows if r.get("nugget_text") == "Led 18-member team"]
    assert len(new_rows) >= 1


# ---------------------------------------------------------------------------
# 13. test_no_exception_on_failure
# ---------------------------------------------------------------------------

def test_no_exception_on_failure(httpx_mock, fake_sb):
    """Network error → returns [], no exception raised."""
    import httpx as _httpx

    httpx_mock.add_exception(
        _httpx.ConnectError("Connection refused"),
        url=_GROQ_URL,
    )

    nuggets = asyncio.run(
        extract_nuggets("user-123", _LONG_TEXT, fake_sb, groq_api_key="fake-key")
    )
    assert nuggets == []


# ---------------------------------------------------------------------------
# 14. test_layer_constraint
# ---------------------------------------------------------------------------

def test_layer_constraint(httpx_mock, fake_sb):
    """Layer A nugget has section_type; Layer B nugget has life_domain."""
    httpx_mock.add_response(
        url=_GROQ_URL,
        json=_groq_response([_SAMPLE_NUGGET_A, _SAMPLE_NUGGET_B]),
    )

    nuggets = asyncio.run(
        extract_nuggets("user-123", _LONG_TEXT, fake_sb, groq_api_key="fake-key")
    )

    layer_a = [n for n in nuggets if n.primary_layer == "A"]
    layer_b = [n for n in nuggets if n.primary_layer == "B"]

    assert len(layer_a) >= 1
    assert len(layer_b) >= 1

    for n in layer_a:
        assert n.section_type is not None, f"Layer A nugget missing section_type: {n}"

    for n in layer_b:
        assert n.life_domain is not None, f"Layer B nugget missing life_domain: {n}"
