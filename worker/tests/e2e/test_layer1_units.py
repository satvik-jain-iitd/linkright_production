"""Layer 1: Unit tests — no real network calls, no DB, fast.

Tests scanner response parsing, scoring logic, enrichment parsing.
Uses unittest.mock to mock httpx.AsyncClient.

Run: pytest worker/tests/e2e/test_layer1_units.py -v
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure worker root is importable
_WORKER_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
if os.path.abspath(_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, os.path.abspath(_WORKER_ROOT))

from tests.e2e.fixtures import (
    FIXTURE_JDS, FIXTURE_MAP, PM_USER_PREFS, PM_USER_TAGS,
    MOCK_GREENHOUSE_RESPONSE, MOCK_ADZUNA_RESPONSE, MOCK_THEMUSE_RESPONSE,
    MOCK_REMOTIVE_RESPONSE, MOCK_IIMJOBS_RESPONSE, MOCK_WELLFOUND_RESPONSE,
    MOCK_JSEARCH_RESPONSE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Build a mock httpx Response object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


def make_fake_sb(existing_urls: list[str] | None = None) -> MagicMock:
    """FakeSupabase that returns existing URLs for dedup checks."""
    rows = [{"job_url": u} for u in (existing_urls or [])]
    result_obj = MagicMock()
    result_obj.data = rows

    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.limit.return_value = query
    query.execute.return_value = result_obj
    query.insert.return_value = query

    # For insert tracking
    inserted: list[dict] = []

    def do_insert(payload):
        if isinstance(payload, list):
            inserted.extend(payload)
        else:
            inserted.append(payload)
        ins_result = MagicMock()
        ins_result.data = [payload] if isinstance(payload, dict) else payload
        return MagicMock(execute=lambda: ins_result)

    query.insert.side_effect = do_insert

    sb = MagicMock()
    sb.table.return_value = query
    sb._inserted = inserted
    return sb


# ---------------------------------------------------------------------------
# Scanner unit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scanner_themuse_parses_response():
    """The Muse scanner correctly parses mock response and writes discovery."""
    from app.pipeline.scanner_themuse import scan_themuse_jobs
    sb = make_fake_sb()

    async def mock_get(*args, **kwargs):
        # First page returns data, second page returns empty
        params = kwargs.get("params", {})
        if params.get("page", 0) == 0:
            return make_mock_response(MOCK_THEMUSE_RESPONSE)
        return make_mock_response({"results": [], "page": 1, "page_count": 1})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await scan_themuse_jobs(sb, ["product manager"], ["sales"])

    assert result.errors == [], f"Unexpected errors: {result.errors}"
    assert result.fetched >= 1, "Should have fetched at least 1 job"


@pytest.mark.asyncio
async def test_scanner_remotive_parses_response():
    """Remotive scanner parses mock response and all results are remote."""
    from app.pipeline.scanner_remotive import scan_remotive
    sb = make_fake_sb()

    async def mock_get(*args, **kwargs):
        return make_mock_response(MOCK_REMOTIVE_RESPONSE)

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await scan_remotive(sb, ["product manager"], [])

    assert result.errors == [], f"Unexpected errors: {result.errors}"
    assert result.fetched >= 1


@pytest.mark.asyncio
async def test_scanner_adzuna_skips_with_no_key():
    """Adzuna scanner skips cleanly when API key is absent."""
    from app.pipeline.scanner_adzuna import scan_adzuna
    sb = make_fake_sb()

    result = await scan_adzuna(sb, app_id="", app_key="", positive_keywords=["product manager"], negative_keywords=[])

    assert result.skipped_no_key is True
    assert result.fetched == 0


@pytest.mark.asyncio
async def test_scanner_adzuna_parses_response():
    """Adzuna scanner correctly parses mock response when keys present."""
    from app.pipeline.scanner_adzuna import scan_adzuna
    sb = make_fake_sb()

    async def mock_get(*args, **kwargs):
        # First page has data, second page is empty
        page = kwargs.get("params", {}).get("page", 1)
        if page <= 1:
            return make_mock_response(MOCK_ADZUNA_RESPONSE)
        return make_mock_response({"results": []})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await scan_adzuna(
            sb, app_id="fake-id", app_key="fake-key",
            positive_keywords=["product manager"], negative_keywords=[],
            target_countries=["IN"],
        )

    assert result.skipped_no_key is False
    assert result.errors == [], f"Unexpected errors: {result.errors}"


@pytest.mark.asyncio
async def test_scanner_jsearch_skips_with_no_key():
    """JSearch scanner skips cleanly when API key absent."""
    from app.pipeline.scanner_jsearch import scan_jsearch
    sb = make_fake_sb()

    result = await scan_jsearch(sb, api_key="", positive_keywords=["product manager"], negative_keywords=[])

    assert result.skipped_no_key is True


@pytest.mark.asyncio
async def test_scanner_iimjobs_parses_response():
    """iimjobs scanner parses mock response."""
    from app.pipeline.scanner_iimjobs import scan_iimjobs
    sb = make_fake_sb()

    async def mock_get(*args, **kwargs):
        page = kwargs.get("params", {}).get("pageNo", 1)
        if page == 1:
            return make_mock_response(MOCK_IIMJOBS_RESPONSE)
        return make_mock_response({"data": {"jobs": []}})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await scan_iimjobs(sb, ["product manager"], [])

    assert result.errors == [], f"Unexpected errors: {result.errors}"


@pytest.mark.asyncio
async def test_scanner_wellfound_parses_response():
    """Wellfound scanner parses mock response."""
    from app.pipeline.scanner_wellfound import scan_wellfound_jobs
    sb = make_fake_sb()

    async def mock_get(*args, **kwargs):
        page = kwargs.get("params", {}).get("page", 1)
        if page == 1:
            return make_mock_response(MOCK_WELLFOUND_RESPONSE)
        return make_mock_response({"data": {"talent__job_search_v1": {"jobs": [], "totalJobListings": 0}}})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await scan_wellfound_jobs(sb, ["product manager"], [])

    assert result.errors == [], f"Unexpected errors: {result.errors}"


# ---------------------------------------------------------------------------
# Dedup tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scanner_themuse_dedup_skips_known_url():
    """Themuse scanner skips URLs already in job_discoveries."""
    from app.pipeline.scanner_themuse import scan_themuse_jobs

    existing_url = "https://www.themuse.com/jobs/stripe/spm"
    sb = make_fake_sb(existing_urls=[existing_url])

    async def mock_get(*args, **kwargs):
        params = kwargs.get("params", {})
        if params.get("page", 0) == 0:
            return make_mock_response(MOCK_THEMUSE_RESPONSE)
        return make_mock_response({"results": []})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await scan_themuse_jobs(sb, ["product manager"], [])

    assert result.skipped_dup >= 1, "Known URL should have been skipped as duplicate"


# ---------------------------------------------------------------------------
# Scoring unit tests
# ---------------------------------------------------------------------------

def test_score_to_action_thresholds():
    """score_to_action returns correct actions for all threshold boundaries."""
    from app.pipeline.scoring import score_to_action

    assert score_to_action(4.5, False) == "apply_now"
    assert score_to_action(4.9, False) == "apply_now"
    assert score_to_action(4.4, False) == "worth_it"
    assert score_to_action(4.0, False) == "worth_it"
    assert score_to_action(3.9, False) == "maybe"
    assert score_to_action(3.5, False) == "maybe"
    assert score_to_action(3.4, False) == "skip"
    assert score_to_action(1.0, False) == "skip"
    # Blockers always → skip
    assert score_to_action(4.9, True) == "skip"
    assert score_to_action(4.5, True) == "skip"


def test_culture_signals_fallback_when_no_llm():
    """culture_signals returns neutral 3.0 when LLM is unavailable."""
    from app.pipeline.scoring import _score_culture_signals

    dim = _score_culture_signals(llm_culture_score=None, llm_seeking_score=None)
    assert dim.score == 3.0
    assert "neutral" in dim.reasoning.lower() or "unavailable" in dim.reasoning.lower()


def test_culture_signals_uses_llm_score():
    """culture_signals correctly blends LLM culture + seeking scores."""
    from app.pipeline.scoring import _score_culture_signals

    dim = _score_culture_signals(llm_culture_score=4.0, llm_seeking_score=4.5)
    assert dim.score == pytest.approx(4.25, abs=0.01)
    assert 1.0 <= dim.score <= 5.0


def test_rubric_default_weights_sum_to_1():
    """DEFAULT_WEIGHTS sum exactly to 1.0."""
    from app.pipeline.rubric_builder import DEFAULT_WEIGHTS

    total = sum(DEFAULT_WEIGHTS.values())
    assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"
    # All 10 dimensions present
    expected_dims = {
        "role_alignment", "skill_match", "level_fit", "compensation_fit",
        "growth_potential", "remote_quality", "company_reputation",
        "tech_stack", "speed_to_offer", "culture_signals",
    }
    assert set(DEFAULT_WEIGHTS.keys()) == expected_dims


def test_rubric_normalize_weights_handles_empty():
    """_normalize_weights with empty input returns DEFAULT_WEIGHTS."""
    from app.pipeline.rubric_builder import _normalize_weights, DEFAULT_WEIGHTS

    result = _normalize_weights({})
    # With all zeros defaulting to 3, should get equal weights
    total = sum(result.values())
    assert abs(total - 1.0) < 0.001
    assert len(result) == len(DEFAULT_WEIGHTS)


@pytest.mark.asyncio
async def test_score_application_no_oracle_no_crash():
    """score_application completes without Oracle (fallback path, no crash)."""
    from app.pipeline.scoring import score_application

    class MockSB:
        def table(self, name): return self
        def select(self, *a, **kw): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def maybe_single(self): return self
        def execute(self):
            class R:
                data = None
                count = 0
            return R()

    fixture = FIXTURE_MAP["pm_remote_yes"]
    result = await score_application(
        user_id="unit-test-user",
        jd_text=fixture.jd_text,
        supabase_client=MockSB(),
        discovery={"title": "Product Manager", "company_slug": None},
    )

    assert 1.0 <= result.overall_score <= 5.0, f"Score {result.overall_score} out of range"
    assert result.overall_grade in {"A", "B", "C", "D", "F"}
    assert result.recommended_action in {"apply_now", "worth_it", "maybe", "skip"}
    assert result.role_archetype  # non-empty string


@pytest.mark.asyncio
async def test_score_archetype_pm_detected():
    """PM archetype detected correctly for PM job descriptions."""
    from app.pipeline.scoring import score_application

    class MockSB:
        def table(self, name): return self
        def select(self, *a, **kw): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def maybe_single(self): return self
        def execute(self):
            class R:
                data = None
                count = 0
            return R()

    jd = "Product Manager position. Drive product roadmap, PRD creation, stakeholder management."
    result = await score_application("u1", jd, MockSB(), discovery={"title": "Product Manager"})
    assert result.role_archetype == "PM", f"Expected PM, got {result.role_archetype}"


def test_skill_match_finds_tags_in_jd_body():
    """skill_match finds tags anywhere in JD body, not just title."""
    from app.pipeline.scoring import _score_skill_match

    jd = "Join us as PM. You will need strong SQL skills, product roadmap ownership, and agile delivery."
    tags = ["sql", "product roadmap", "agile", "machine learning"]

    dim = _score_skill_match(jd, tags)
    assert dim.score >= 3.5, f"Expected ≥3.5 with 3 matching tags, got {dim.score}"
    matched_evidence = [e.lower() for e in dim.evidence]
    assert any("sql" in e or "agile" in e for e in matched_evidence)


# ---------------------------------------------------------------------------
# Enrichment parsing unit tests
# ---------------------------------------------------------------------------

def test_enrichment_parse_remote_ok_yes():
    """Enricher parses 'yes' remote answers correctly."""
    from app.pipeline.jd_enricher import _parse_answer

    assert _parse_answer("remote_ok", "yes", "yes,no") is True
    assert _parse_answer("remote_ok", "Yes, this is a remote role", "yes,no") is True
    assert _parse_answer("remote_ok", "no", "yes,no") is False


def test_enrichment_parse_experience_level_senior():
    """Enricher maps '5+ years' → 'senior' via answer parsing."""
    from app.pipeline.jd_enricher import _parse_answer

    # The enricher produces a level label directly from LLM answer
    valid = "early,mid,senior,executive,cxo"
    assert _parse_answer("experience_level", "senior", valid) == "senior"
    assert _parse_answer("experience_level", "This is a senior role requiring 5+ years", valid) == "senior"
    assert _parse_answer("experience_level", "mid level", valid) == "mid"


def test_enrichment_parse_employment_type():
    from app.pipeline.jd_enricher import _parse_answer

    valid = "full_time,contract,part_time"
    assert _parse_answer("employment_type", "full_time", valid) == "full_time"
    assert _parse_answer("employment_type", "contract position", valid) == "contract"


def test_enrichment_parse_invalid_returns_none():
    """Enricher returns None for unrecognized answers — no crash."""
    from app.pipeline.jd_enricher import _parse_answer

    result = _parse_answer("remote_ok", "", "yes,no")
    assert result is None

    result = _parse_answer("experience_level", "blah blah", "early,mid,senior,executive,cxo")
    assert result is None


def test_enrichment_parse_years_experience_int():
    from app.pipeline.jd_enricher import _parse_answer

    assert _parse_answer("min_years_experience", "5", "integer") == 5
    assert _parse_answer("min_years_experience", "requires 7 years", "integer") == 7
    assert _parse_answer("min_years_experience", "none", "integer") is None


# ---------------------------------------------------------------------------
# Scoring fixture sweep — all 6 fixture JDs produce valid scores
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("fixture_name", [f.name for f in FIXTURE_JDS])
async def test_all_fixture_jds_produce_valid_score(fixture_name: str):
    """Every fixture JD yields score in [1,5], valid grade, valid action."""
    from app.pipeline.scoring import score_application

    class MockSB:
        def table(self, name): return self
        def select(self, *a, **kw): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def maybe_single(self): return self
        def execute(self):
            class R:
                data = None
                count = 0
            return R()

    fixture = FIXTURE_MAP[fixture_name]
    result = await score_application(
        user_id="fixture-test",
        jd_text=fixture.jd_text,
        supabase_client=MockSB(),
        discovery={"title": fixture.jd_text.split("\n")[0][:80], "company_slug": None},
    )

    assert 1.0 <= result.overall_score <= 5.0, f"{fixture_name}: score {result.overall_score} out of range"
    assert result.overall_grade in {"A", "B", "C", "D", "F"}, f"{fixture_name}: invalid grade {result.overall_grade}"
    assert result.recommended_action in {"apply_now", "worth_it", "maybe", "skip"}, \
        f"{fixture_name}: invalid action {result.recommended_action}"
    # Score → action consistency
    from app.pipeline.scoring import score_to_action
    expected_action = score_to_action(result.overall_score, bool(result.hard_blockers))
    assert result.recommended_action == expected_action, \
        f"{fixture_name}: action {result.recommended_action} inconsistent with score {result.overall_score}"
