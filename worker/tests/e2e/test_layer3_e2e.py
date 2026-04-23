"""Layer 3: E2E pipeline tests — full scan→score→top20 on mock DB.

Verifies complete pipeline flow without real network calls.
Injects fixture discoveries and asserts top-20 ranking is correct.

Run: pytest worker/tests/e2e/test_layer3_e2e.py -m e2e -v
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

_WORKER_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
if os.path.abspath(_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, os.path.abspath(_WORKER_ROOT))

from tests.e2e.fixtures import FIXTURE_JDS, FIXTURE_MAP, PM_USER_PREFS, PM_USER_TAGS

pytestmark = pytest.mark.e2e

USER_ID = "e2e-test-user-pm-001"


# ---------------------------------------------------------------------------
# Extended FakeSupabase — supports all pipeline tables
# ---------------------------------------------------------------------------

class ExtendedFakeSB:
    """Extends FakeSupabaseClient to support all pipeline table operations."""

    def __init__(self):
        self._tables: dict[str, list[dict]] = {
            "job_discoveries": [],
            "job_scores": [],
            "user_daily_top_20": [],
            "user_preferences": [],
            "career_nuggets": [],
            "companies_global": [],
            "company_watchlist": [],
            "user_notifications": [],
        }

    def table(self, name: str) -> "_TableProxy":
        if name not in self._tables:
            self._tables[name] = []
        return _TableProxy(self._tables[name], self._tables)

    def seed_user_prefs(self, user_id: str, **prefs):
        row = {"user_id": user_id, **PM_USER_PREFS, **prefs}
        self._tables["user_preferences"].append(row)

    def seed_nuggets(self, user_id: str, tags: list[str]):
        self._tables["career_nuggets"].append({"user_id": user_id, "tags": tags})

    def seed_company(self, slug: str, ats_provider: str, ats_identifier: str, **extra):
        self._tables["companies_global"].append({
            "company_slug": slug,
            "display_name": slug.title(),
            "ats_provider": ats_provider,
            "ats_identifier": ats_identifier,
            "brand_tier": "strong",
            "tier_flags": [],
            "stage": "series_b",
            "supports_remote": "TRUE",
            "sponsors_visa_usa": "TRUE",
            **extra,
        })

    def inject_discovery(
        self,
        title: str = "Senior Product Manager",
        company: str = "TestCo",
        jd_text: str = "",
        job_url: str | None = None,
        days_old: int = 0,
        user_id: str | None = None,
    ) -> dict:
        row = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title,
            "company_name": company,
            "job_url": job_url or f"https://example.com/job/{uuid.uuid4().hex[:8]}",
            "jd_text": jd_text,
            "company_slug": company.lower().replace(" ", "_"),
            "discovered_at": (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat(),
            "liveness_status": "active",
            "status": "new",
            "enrichment_status": "done" if jd_text else "pending",
            "source_type": "api_test",
        }
        self._tables["job_discoveries"].append(row)
        return row

    def count(self, table: str, **filters) -> int:
        rows = self._tables.get(table, [])
        for k, v in filters.items():
            rows = [r for r in rows if r.get(k) == v]
        return len(rows)


class _TableProxy:
    """Chainable table proxy over a list of dicts."""

    def __init__(self, rows: list[dict], all_tables: dict):
        self._rows = rows
        self._all = all_tables
        self._filters: list[tuple] = []
        self._negate: bool = False
        self._or_filters: list[str] = []
        self._gte_filters: list[tuple] = []
        self._in_filters: list[tuple] = []
        self._not_null_col: str | None = None
        self._order_col: str | None = None
        self._order_desc: bool = False
        self._limit_n: int | None = None
        self._insert_payload: Any = None
        self._update_payload: dict | None = None
        self._delete: bool = False
        self._count_mode: bool = False

    def select(self, *a, count: str | None = None, **kw):
        if count:
            self._count_mode = True
        return self

    def eq(self, col: str, val) -> "_TableProxy":
        self._filters.append((col, val))
        return self

    def in_(self, col: str, vals: list) -> "_TableProxy":
        self._in_filters.append((col, vals))
        return self

    def gte(self, col: str, val: str) -> "_TableProxy":
        self._gte_filters.append((col, val))
        return self

    def or_(self, expr: str) -> "_TableProxy":
        self._or_filters.append(expr)
        return self

    @property
    def not_(self) -> "_TableProxy":
        self._negate = True
        return self

    def is_(self, col: str, val) -> "_TableProxy":
        # .not_.is_("col", "null") = exclude nulls; .is_("col", "null") = only nulls
        if val in ("null", None):
            tag = "__is_not_null__" if self._negate else "__is_null__"
            self._filters.append((tag, col))
            self._negate = False
        return self

    def order(self, col: str, desc: bool = False) -> "_TableProxy":
        self._order_col = col
        self._order_desc = desc
        return self

    def limit(self, n: int) -> "_TableProxy":
        self._limit_n = n
        return self

    def lte(self, col: str, val) -> "_TableProxy":
        return self  # Not critical for tests

    def maybe_single(self) -> "_TableProxy":
        self._limit_n = 1
        return self

    def insert(self, payload) -> "_TableProxy":
        self._insert_payload = payload
        return self

    def update(self, payload: dict) -> "_TableProxy":
        self._update_payload = payload
        return self

    def delete(self) -> "_TableProxy":
        self._delete = True
        return self

    def execute(self):
        if self._insert_payload is not None:
            payload = self._insert_payload
            if isinstance(payload, dict):
                payload = [payload]
            self._rows.extend(payload)
            return _R(list(payload))

        if self._delete:
            matched = self._apply_filters(self._rows)
            for r in matched:
                if r in self._rows:
                    self._rows.remove(r)
            return _R([])

        if self._update_payload is not None:
            matched = self._apply_filters(self._rows)
            for r in matched:
                r.update(self._update_payload)
            return _R(matched)

        matched = self._apply_filters(self._rows)

        if self._order_col:
            matched = sorted(matched, key=lambda r: r.get(self._order_col) or "", reverse=self._order_desc)

        if self._limit_n:
            matched = matched[:self._limit_n]

        result = _R(matched)
        if self._count_mode:
            result.count = len(matched)
        if self._limit_n == 1:
            result.data = matched[0] if matched else None
        return result

    def _apply_filters(self, rows: list[dict]) -> list[dict]:
        matched = rows[:]
        for col, val in self._filters:
            if col == "__is_null__":
                matched = [r for r in matched if r.get(val) is None]
            elif col == "__is_not_null__":
                matched = [r for r in matched if r.get(val) is not None]
            else:
                matched = [r for r in matched if r.get(col) == val]
        for col, vals in self._in_filters:
            matched = [r for r in matched if r.get(col) in vals]
        for col, val in self._gte_filters:
            matched = [r for r in matched if (r.get(col) or "") >= val]
        if self._or_filters:
            # Simple: pass everything (can't fully parse Supabase or_ syntax)
            pass
        return matched


class _R:
    def __init__(self, data):
        self.data = data
        self.count = len(data) if isinstance(data, list) else (1 if data else 0)


# ---------------------------------------------------------------------------
# E2E Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_score_application_produces_valid_score_pm():
    """score_application returns valid score for PM fixture JD with seeded user data."""
    from app.pipeline.scoring import score_application

    sb = ExtendedFakeSB()
    sb.seed_user_prefs(USER_ID)
    sb.seed_nuggets(USER_ID, PM_USER_TAGS)

    fixture = FIXTURE_MAP["pm_remote_yes"]
    result = await score_application(
        user_id=USER_ID,
        jd_text=fixture.jd_text,
        supabase_client=sb,
        discovery={"title": "Product Manager - Platform AI", "company_slug": "testco"},
    )

    print(f"\n  E2E score: {result.overall_score:.2f} ({result.overall_grade}) → {result.recommended_action}")
    print(f"  archetype={result.role_archetype} culture={result.culture_signals.score}")
    print(f"  keywords_matched={result.keywords_matched[:5]}")

    assert 1.0 <= result.overall_score <= 5.0
    assert result.overall_grade in {"A", "B", "C", "D", "F"}
    assert result.recommended_action in {"apply_now", "worth_it", "maybe", "skip"}
    assert result.role_archetype == "PM"
    # With PM tags seeded, skill_match should be > neutral
    assert result.skill_match.score >= 2.0, "Expected some skill matching with seeded PM tags"


@pytest.mark.asyncio
async def test_score_red_flag_jd_gets_lower_score():
    """Red-flag JD scores lower than strong PM JD."""
    from app.pipeline.scoring import score_application

    class MinimalSB:
        def table(self, n): return self
        def select(self, *a, **kw): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def maybe_single(self): return self
        def execute(self):
            class R:
                data = None
                count = 0
            return R()

    strong_result = await score_application(
        "u1", FIXTURE_MAP["strong_faang_jd"].jd_text, MinimalSB(),
        discovery={"title": "Lead Product Manager"},
    )
    red_flag_result = await score_application(
        "u1", FIXTURE_MAP["red_flag_jd"].jd_text, MinimalSB(),
        discovery={"title": "Product Manager Needed URGENTLY"},
    )

    print(f"\n  Strong JD: {strong_result.overall_score:.2f} ({strong_result.recommended_action})")
    print(f"  Red flag JD: {red_flag_result.overall_score:.2f} ({red_flag_result.recommended_action})")

    assert strong_result.overall_score >= red_flag_result.overall_score, \
        f"Strong JD ({strong_result.overall_score}) should score >= red flag ({red_flag_result.overall_score})"


@pytest.mark.asyncio
async def test_top20_ranking_from_multiple_discoveries():
    """compute_and_store_top_20 correctly ranks discoveries by score."""
    from app.pipeline.scoring import score_application
    from app.pipeline.recommender import compute_and_store_top_20

    sb = ExtendedFakeSB()
    sb.seed_user_prefs(USER_ID)
    sb.seed_nuggets(USER_ID, PM_USER_TAGS)

    # Inject 4 discoveries with different JDs
    for i, fixture in enumerate(FIXTURE_JDS[:4]):
        disc = sb.inject_discovery(
            title=fixture.jd_text.split("\n")[0][:60],
            company=f"Company{i}",
            jd_text=fixture.jd_text,
            days_old=i,
        )
        # Pre-score each discovery
        score_result = await score_application(USER_ID, fixture.jd_text, sb, discovery=disc)
        sb.table("job_scores").insert({
            "user_id": USER_ID,
            "job_discovery_id": disc["id"],
            "overall_score": score_result.overall_score,
            "overall_grade": score_result.overall_grade,
            "recommended_action": score_result.recommended_action,
            "dimensions": score_result.dimensions,
            "role_archetype": score_result.role_archetype,
            "skill_gaps": score_result.skill_gaps,
            "hard_blockers": score_result.hard_blockers,
            "keywords_matched": score_result.keywords_matched,
            "legitimacy_tier": "unknown",
        }).execute()

    ranked = compute_and_store_top_20(sb, USER_ID)

    print(f"\n  Ranked {len(ranked)} discoveries")
    for r in ranked[:3]:
        print(f"    rank={r['rank']} score={r['final_score']:.3f}")

    assert len(ranked) >= 1, "Should have at least 1 ranked discovery"
    assert ranked[0]["rank"] == 1, "First entry should be rank 1"
    # Ranks should be in order
    for i in range(len(ranked) - 1):
        assert ranked[i]["final_score"] >= ranked[i + 1]["final_score"], \
            f"Rank {i+1} score {ranked[i]['final_score']} < rank {i+2} score {ranked[i+1]['final_score']}"


@pytest.mark.asyncio
async def test_dedup_same_url_not_inserted_twice():
    """Two calls with same job_url result in only 1 discovery in DB."""
    from app.pipeline.scanner_themuse import scan_themuse_jobs
    from unittest.mock import AsyncMock, MagicMock, patch
    from tests.e2e.fixtures import MOCK_THEMUSE_RESPONSE

    sb = ExtendedFakeSB()
    sb.seed_user_prefs(USER_ID)

    def mock_get_factory():
        call_count = [0]
        async def mock_get(*args, **kwargs):
            call_count[0] += 1
            params = kwargs.get("params", {})
            if params.get("page", 0) == 0:
                return _make_resp(MOCK_THEMUSE_RESPONSE)
            return _make_resp({"results": []})
        return mock_get

    def _make_resp(data):
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = data
        r.raise_for_status = MagicMock()
        return r

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = mock_get_factory()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        # First scan
        result1 = await scan_themuse_jobs(sb, ["product manager"], [])

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client2 = AsyncMock()
        mock_client2.get = mock_get_factory()
        mock_client2.__aenter__ = AsyncMock(return_value=mock_client2)
        mock_client2.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client2

        # Second scan — same response = same URLs
        result2 = await scan_themuse_jobs(sb, ["product manager"], [])

    discoveries = sb._tables["job_discoveries"]
    urls = [d["job_url"] for d in discoveries]
    unique_urls = set(urls)

    print(f"\n  Dedup test: run1_fetched={result1.fetched} run2_fetched={result2.fetched}")
    print(f"  Total discoveries={len(discoveries)} unique_urls={len(unique_urls)}")

    assert len(urls) == len(unique_urls), \
        f"Duplicate URLs found! Total={len(urls)} unique={len(unique_urls)}"
    assert result2.skipped_dup >= result2.fetched, \
        "Second run should have skipped all as duplicates"


@pytest.mark.asyncio
async def test_all_fixture_jds_score_consistently():
    """All 6 fixture JDs: score is consistent with action (score→action contract)."""
    from app.pipeline.scoring import score_application, score_to_action

    class MinimalSB:
        def table(self, n): return self
        def select(self, *a, **kw): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def maybe_single(self): return self
        def execute(self):
            class R:
                data = None
                count = 0
            return R()

    failures = []
    for fixture in FIXTURE_JDS:
        result = await score_application("u1", fixture.jd_text, MinimalSB(),
                                         discovery={"title": fixture.jd_text.split("\n")[0][:80]})
        # Score→action consistency
        expected = score_to_action(result.overall_score, bool(result.hard_blockers))
        if result.recommended_action != expected:
            failures.append(f"{fixture.name}: action={result.recommended_action} but score={result.overall_score:.2f} → expected {expected}")
        # Score in range
        if not (1.0 <= result.overall_score <= 5.0):
            failures.append(f"{fixture.name}: score {result.overall_score} out of [1,5]")

        print(f"  {fixture.name}: {result.overall_score:.2f} ({result.overall_grade}) → {result.recommended_action}")

    assert failures == [], "Consistency failures:\n" + "\n".join(failures)


@pytest.mark.asyncio
async def test_recency_decay_older_jobs_rank_lower():
    """Older discoveries rank lower than newer ones with same score."""
    from app.pipeline.recommender import _recency_decay

    decay_0d = _recency_decay(0)
    decay_3d = _recency_decay(3)
    decay_7d = _recency_decay(7)
    decay_14d = _recency_decay(14)

    print(f"\n  Recency decay: 0d={decay_0d:.3f} 3d={decay_3d:.3f} 7d={decay_7d:.3f} 14d={decay_14d:.3f}")

    assert decay_0d > decay_3d > decay_7d > decay_14d, "Decay should be strictly decreasing"
    assert decay_0d == pytest.approx(1.0, abs=0.001), "Fresh job decay should be ~1.0"
    assert decay_14d >= 0.1, "14-day old job should retain at least 10% weight"
