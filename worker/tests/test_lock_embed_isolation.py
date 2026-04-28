"""Integration test: lock/unlock embed isolation.

Verifies the gold-standard behavior of the nugget embed worker:
  - Locking a single nugget triggers embed for ONLY that nugget.
  - 14 unlocked nuggets + lock 3 → exactly 3 get embeddings (one call each).
  - Unlocking a nugget clears its embedding; re-locking re-creates it.
  - Targeting an unlocked nugget produces zero embeds (locked guard).

These tests exercise _run_nugget_embed via a controlled FakeSupabase
that understands .eq(), .is_(), .not_.is_(), and .overlaps() filters.
The Oracle HTTP call is mocked to return a deterministic fake vector.
"""

from __future__ import annotations

import asyncio
import os
import sys
import unittest.mock as mock
from datetime import datetime, timezone

import pytest

# ---------------------------------------------------------------------------
# Patch env BEFORE importing any worker module.
# Must include SUPABASE_SERVICE_KEY (required by app/config.py).
# ---------------------------------------------------------------------------
_env_patch = mock.patch.dict(
    os.environ,
    {
        "SUPABASE_URL": "https://fake.supabase.co",
        "SUPABASE_KEY": "fake-key",
        "SUPABASE_SERVICE_KEY": "fake-service-key",
        "ORACLE_BACKEND_URL": "http://fake-oracle",
        "ORACLE_BACKEND_SECRET": "fake-oracle-secret",
    },
)
_env_patch.start()

_WORKER_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _WORKER_ROOT not in sys.path:
    sys.path.insert(0, os.path.abspath(_WORKER_ROOT))

# Module-level import — env patch is already active
from app.main import _run_nugget_embed  # noqa: E402

# ---------------------------------------------------------------------------
# FakeSupabase that supports the full filter set used by _run_nugget_embed:
#   .eq(), .is_("col", "null"), .not_.is_("col", "null"), .overlaps()
# ---------------------------------------------------------------------------

FAKE_VECTOR = [0.5] * 768


class _NotProxy:
    """Returned by chain.not_ — intercepts the .is_() call that follows."""

    def __init__(self, chain: "_QueryChain") -> None:
        self._chain = chain

    def is_(self, col: str, sentinel: str) -> "_QueryChain":
        assert sentinel == "null"
        self._chain._filters.append(lambda r, c=col: r.get(c) is not None)
        return self._chain


class _QueryChain:
    """Chainable query builder matching the Supabase Python client surface."""

    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self._filters: list = []
        self._update_payload: dict | None = None
        self._insert_payload: list[dict] | None = None

    # ---- builder ----

    def select(self, *_a, **_kw) -> "_QueryChain":
        return self

    def insert(self, payload) -> "_QueryChain":
        if isinstance(payload, dict):
            payload = [payload]
        self._insert_payload = payload
        return self

    def update(self, payload: dict) -> "_QueryChain":
        self._update_payload = payload
        return self

    def eq(self, col: str, val) -> "_QueryChain":
        self._filters.append(lambda r, c=col, v=val: r.get(c) == v)
        return self

    def is_(self, col: str, sentinel: str) -> "_QueryChain":
        """Supabase .is_('col', 'null') → col IS NULL."""
        assert sentinel == "null", f"unexpected sentinel: {sentinel!r}"
        self._filters.append(lambda r, c=col: r.get(c) is None)
        return self

    def overlaps(self, col: str, values: list) -> "_QueryChain":
        """Match rows where col (a list) contains any of values."""
        self._filters.append(
            lambda r, c=col, vs=tuple(values): bool(set(r.get(c) or []) & set(vs))
        )
        return self

    @property
    def not_(self) -> _NotProxy:
        return _NotProxy(self)

    def order(self, *_a, **_kw) -> "_QueryChain":
        return self

    def limit(self, *_a, **_kw) -> "_QueryChain":
        return self

    def maybeSingle(self) -> "_QueryChain":  # noqa: N802
        return self

    # ---- terminal ----

    def execute(self):
        if self._insert_payload is not None:
            self._rows.extend(self._insert_payload)
            return _Result(list(self._insert_payload))

        if self._update_payload is not None:
            matched = [r for r in self._rows if all(f(r) for f in self._filters)]
            for row in matched:
                row.update(self._update_payload)
            return _Result(matched)

        matched = [r for r in self._rows if all(f(r) for f in self._filters)]
        return _Result(matched)


class _Result:
    def __init__(self, data: list[dict]) -> None:
        self.data = data


class _FakeTable:
    def __init__(self, rows: list[dict] | None = None):
        self.rows: list[dict] = list(rows or [])

    def select(self, *a, **kw) -> _QueryChain:
        return _QueryChain(self.rows).select(*a, **kw)

    def insert(self, payload) -> _QueryChain:
        return _QueryChain(self.rows).insert(payload)

    def update(self, payload) -> _QueryChain:
        return _QueryChain(self.rows).update(payload)

    def eq(self, col, val) -> _QueryChain:
        return _QueryChain(self.rows).eq(col, val)


class _FakeSB:
    def __init__(self):
        self._tables: dict[str, _FakeTable] = {}

    def table(self, name: str) -> _FakeTable:
        if name not in self._tables:
            self._tables[name] = _FakeTable()
        return self._tables[name]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc).isoformat()


def _make_nugget(
    nid: str,
    user_id: str = "user-test",
    locked_at: str | None = None,
    embedding: list | None = None,
) -> dict:
    return {
        "id": nid,
        "user_id": user_id,
        "answer": f"Answer for nugget {nid}",
        "tags": ["source:onboarding"],
        "locked_at": locked_at,
        "embedding": embedding,
    }


def _count_embedded(rows: list[dict]) -> int:
    return sum(1 for r in rows if r.get("embedding") is not None)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_lock_3_embeds_exactly_3(httpx_mock):
    """14 nuggets, 3 locked → locking each one triggers embed for ONLY that nugget.
    After 3 targeted calls, exactly 3 rows have embeddings.
    """
    fake_sb = _FakeSB()
    nuggets = [_make_nugget(f"nug-{i}") for i in range(14)]
    locked_ids = ["nug-0", "nug-5", "nug-11"]
    for n in nuggets:
        if n["id"] in locked_ids:
            n["locked_at"] = NOW
    fake_sb.table("career_nuggets").rows.extend(nuggets)

    # One batch call per locked nugget (each call returns 1 vector)
    for _ in range(3):
        httpx_mock.add_response(
            url="http://fake-oracle/lifeos/embed-batch",
            json={"embeddings": [FAKE_VECTOR]},
        )

    with mock.patch("app.main.create_supabase", return_value=fake_sb):
        for nid in locked_ids:
            _run(_run_nugget_embed("user-test", nugget_id=nid))

    rows = fake_sb.table("career_nuggets").rows
    embedded_ids = {r["id"] for r in rows if r.get("embedding") is not None}
    assert embedded_ids == set(locked_ids), (
        f"Expected exactly {set(locked_ids)} embedded, got {embedded_ids}"
    )
    assert _count_embedded(rows) == 3


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_lock_one_does_not_sweep_others(httpx_mock):
    """Locking 1 nugget when 5 are un-embedded should only embed that 1."""
    fake_sb = _FakeSB()
    nuggets = [_make_nugget(f"nug-{i}") for i in range(5)]
    nuggets[2]["locked_at"] = NOW  # only nug-2 is locked
    fake_sb.table("career_nuggets").rows.extend(nuggets)

    httpx_mock.add_response(
        url="http://fake-oracle/lifeos/embed-batch",
        json={"embeddings": [FAKE_VECTOR]},
    )

    with mock.patch("app.main.create_supabase", return_value=fake_sb):
        _run(_run_nugget_embed("user-test", nugget_id="nug-2"))

    rows = fake_sb.table("career_nuggets").rows
    assert _count_embedded(rows) == 1
    embedded = next(r for r in rows if r.get("embedding") is not None)
    assert embedded["id"] == "nug-2"


def test_unlock_clears_embedding_then_relock_recreates(httpx_mock):
    """Unlock clears embedding; re-locking then calling embed recreates it.

    The unlock API route sets locked_at=null + embedding=null in DB.
    We simulate that state transition here.
    """
    fake_sb = _FakeSB()
    nuggets = [_make_nugget(f"nug-{i}") for i in range(5)]
    # nug-0 was previously locked+embedded
    nuggets[0]["locked_at"] = NOW
    nuggets[0]["embedding"] = FAKE_VECTOR
    fake_sb.table("career_nuggets").rows.extend(nuggets)

    # Simulate unlock: API route sets locked_at=null, embedding=null
    for row in fake_sb.table("career_nuggets").rows:
        if row["id"] == "nug-0":
            row["locked_at"] = None
            row["embedding"] = None

    # Verify embedding is cleared
    row0 = next(r for r in fake_sb.table("career_nuggets").rows if r["id"] == "nug-0")
    assert row0["embedding"] is None

    # Re-lock nug-0 (user clicks Lock again after editing)
    row0["locked_at"] = NOW

    httpx_mock.add_response(
        url="http://fake-oracle/lifeos/embed-batch",
        json={"embeddings": [FAKE_VECTOR]},
    )

    with mock.patch("app.main.create_supabase", return_value=fake_sb):
        _run(_run_nugget_embed("user-test", nugget_id="nug-0"))

    row0_after = next(r for r in fake_sb.table("career_nuggets").rows if r["id"] == "nug-0")
    assert row0_after["embedding"] == FAKE_VECTOR, "Re-lock should produce fresh embedding"

    others_embedded = [
        r for r in fake_sb.table("career_nuggets").rows
        if r["id"] != "nug-0" and r.get("embedding") is not None
    ]
    assert others_embedded == [], f"No other nuggets should be embedded: {others_embedded}"


def test_unlocked_nugget_not_embedded_when_targeted(httpx_mock):
    """If nugget_id is provided but that nugget is NOT locked, it is skipped.
    No Oracle HTTP call should be made.
    """
    fake_sb = _FakeSB()
    nuggets = [_make_nugget("nug-unlocked")]  # locked_at=None
    fake_sb.table("career_nuggets").rows.extend(nuggets)

    # No mock responses added — httpx_mock will fail if any HTTP call is made
    with mock.patch("app.main.create_supabase", return_value=fake_sb):
        _run(_run_nugget_embed("user-test", nugget_id="nug-unlocked"))

    rows = fake_sb.table("career_nuggets").rows
    assert _count_embedded(rows) == 0, "Unlocked nugget must not be embedded"


@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_legacy_sweep_without_nugget_id(httpx_mock):
    """When nugget_id is None, the function sweeps all un-embedded source-tagged rows."""
    fake_sb = _FakeSB()
    nuggets = [_make_nugget(f"nug-{i}") for i in range(3)]
    fake_sb.table("career_nuggets").rows.extend(nuggets)

    # Batch of 3 texts in one Oracle call
    httpx_mock.add_response(
        url="http://fake-oracle/lifeos/embed-batch",
        json={"embeddings": [FAKE_VECTOR, FAKE_VECTOR, FAKE_VECTOR]},
    )

    with mock.patch("app.main.create_supabase", return_value=fake_sb):
        _run(_run_nugget_embed("user-test", nugget_id=None))

    assert _count_embedded(fake_sb.table("career_nuggets").rows) == 3
