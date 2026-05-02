"""Unit tests for Stage 2 dual-write: job_scores.rank population.

Covers:
  - _dual_write_job_scores_rank sets rank for top-N jobs (M2)
  - _dual_write_job_scores_rank clears stale rank for jobs that fell out (M6)
  - user_daily_top_20 write path is preserved (M3)
  - Graceful degradation when job_scores.rank column missing (42703 error)
"""
from __future__ import annotations

import os
import sys
from unittest import mock

import pytest

# Env vars must be set before any worker module import triggers config.py
mock.patch.dict(
    os.environ,
    {"SUPABASE_URL": "https://fake.supabase.co", "SUPABASE_KEY": "fake-key"},
).start()

_WORKER_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _WORKER_ROOT not in sys.path:
    sys.path.insert(0, os.path.abspath(_WORKER_ROOT))

from app.pipeline.recommender import _dual_write_job_scores_rank  # noqa: E402


# ---------------------------------------------------------------------------
# Minimal FakeTable / FakeSB that tracks UPDATE calls
# ---------------------------------------------------------------------------

class _FakeUpdateChain:
    """Chainable UPDATE stub that records mutations on the parent rows list."""

    def __init__(self, rows: list[dict], payload: dict) -> None:
        self._rows = rows
        self._payload = payload
        self._filters: list[tuple] = []
        self._not_in_col: str | None = None
        self._not_in_vals: list | None = None
        self._not_is_null_col: str | None = None

    def eq(self, col: str, val) -> "_FakeUpdateChain":
        self._filters.append((col, val))
        return self

    def not_(self) -> "_FakeUpdateChain":  # pragma: no cover
        return self  # not used directly — see not_

    def execute(self):
        matched = list(self._rows)
        for col, val in self._filters:
            matched = [r for r in matched if r.get(col) == val]
        if self._not_in_col and self._not_in_vals is not None:
            matched = [r for r in matched if r.get(self._not_in_col) not in self._not_in_vals]
        if self._not_is_null_col:
            matched = [r for r in matched if r.get(self._not_is_null_col) is not None]
        for row in matched:
            row.update(self._payload)
        return type("_R", (), {"data": matched})()


class _FakeQueryChain:
    """Chainable SELECT/UPDATE/INSERT stub."""

    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self._filters: list[tuple] = []
        self._update_payload: dict | None = None
        self._not_in_col: str | None = None
        self._not_in_vals: list | None = None
        self._not_is_null_col: str | None = None

    def update(self, payload: dict) -> "_FakeQueryChain":
        self._update_payload = payload
        return self

    def eq(self, col: str, val) -> "_FakeQueryChain":
        self._filters.append((col, val))
        return self

    # Support .not_.is_("rank", "null") and .not_.in_("col", vals) chaining
    @property
    def not_(self) -> "_NotProxy":
        return _NotProxy(self)

    def execute(self):
        matched = list(self._rows)
        for col, val in self._filters:
            matched = [r for r in matched if r.get(col) == val]
        if self._not_in_col and self._not_in_vals is not None:
            matched = [r for r in matched if r.get(self._not_in_col) not in self._not_in_vals]
        if self._not_is_null_col:
            matched = [r for r in matched if r.get(self._not_is_null_col) is not None]
        if self._update_payload is not None:
            for row in matched:
                row.update(self._update_payload)
        return type("_R", (), {"data": matched})()


class _NotProxy:
    """Proxies .not_.is_() and .not_.in_() to the parent chain."""

    def __init__(self, chain: _FakeQueryChain) -> None:
        self._chain = chain

    def is_(self, col: str, val: str) -> _FakeQueryChain:
        # .not_.is_("rank", "null") means rank IS NOT NULL
        if val == "null":
            self._chain._not_is_null_col = col
        return self._chain

    def in_(self, col: str, vals: list) -> _FakeQueryChain:
        self._chain._not_in_col = col
        self._chain._not_in_vals = vals
        return self._chain


class _FakeUpsertChain:
    """Chainable UPSERT stub — simulates ON CONFLICT DO UPDATE SET."""

    def __init__(self, rows: list[dict], payload: list[dict], on_conflict: str) -> None:
        self._rows = rows
        self._payload = payload
        self._conflict_cols = [c.strip() for c in on_conflict.split(",") if c.strip()]

    def execute(self):
        for item in self._payload:
            # Find existing row matching all conflict columns
            match = next(
                (r for r in self._rows
                 if all(r.get(c) == item.get(c) for c in self._conflict_cols)),
                None,
            )
            if match is not None:
                match.update(item)
            else:
                self._rows.append(dict(item))
        return type("_R", (), {"data": list(self._payload)})()


class FakeJobScoresTable:
    """Dict-backed job_scores stub with upsert support."""

    def __init__(self, initial_rows: list[dict] | None = None) -> None:
        self.rows: list[dict] = list(initial_rows or [])
        self.upsert_call_count: int = 0

    def update(self, payload: dict) -> _FakeQueryChain:
        return _FakeQueryChain(self.rows).update(payload)

    def upsert(self, payload: list[dict], on_conflict: str = "") -> "_FakeUpsertChain":
        """Upsert stub — increments call counter and applies ON CONFLICT DO UPDATE."""
        self.upsert_call_count += 1
        return _FakeUpsertChain(self.rows, payload, on_conflict)


class FakeSupabaseClient:
    def __init__(self, job_scores_rows: list[dict] | None = None) -> None:
        self._job_scores = FakeJobScoresTable(job_scores_rows)
        self._other: dict[str, FakeJobScoresTable] = {}

    def table(self, name: str):
        if name == "job_scores":
            return self._job_scores
        if name not in self._other:
            self._other[name] = FakeJobScoresTable()
        return self._other[name]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ranked_rows(user_id: str, n: int, start_disc_id: int = 1) -> list[dict]:
    """Build synthetic ranked_rows as produced by compute_and_store_top_20."""
    return [
        {
            "user_id": user_id,
            "job_discovery_id": f"disc-{start_disc_id + i:04d}",
            "date_utc": "2026-05-02",
            "rank": i + 1,
            "final_score": round(0.9 - i * 0.01, 3),
            "reason": "recommended: apply_now",
        }
        for i in range(n)
    ]


def _make_job_score_rows(user_id: str, disc_ids: list[str], ranks: list[int | None]) -> list[dict]:
    """Build synthetic job_scores rows (as they'd be stored in DB)."""
    return [
        {
            "user_id": user_id,
            "job_discovery_id": did,
            "overall_score": 0.8,
            "rank": r,
        }
        for did, r in zip(disc_ids, ranks)
    ]


# ---------------------------------------------------------------------------
# Tests — M2: Dual-write sets rank for top-N rows
# ---------------------------------------------------------------------------

def test_dual_write_sets_rank_for_top_n():
    """After _dual_write_job_scores_rank, job_scores rows for top-N have rank populated."""
    user_id = "user-abc"
    n = 20
    ranked_rows = _make_ranked_rows(user_id, n)
    disc_ids = [r["job_discovery_id"] for r in ranked_rows]

    # Seed job_scores with those rows (rank=None initially)
    initial_scores = _make_job_score_rows(user_id, disc_ids, [None] * n)
    sb = FakeSupabaseClient(job_scores_rows=initial_scores)

    _dual_write_job_scores_rank(sb, user_id, ranked_rows)

    ranked_in_db = [
        row for row in sb._job_scores.rows
        if row["user_id"] == user_id and row["rank"] is not None
    ]
    assert len(ranked_in_db) == n, (
        f"Expected {n} ranked rows in job_scores, got {len(ranked_in_db)}"
    )

    # Verify rank values match 1..N in order
    by_disc = {r["job_discovery_id"]: r["rank"] for r in ranked_in_db}
    for expected_row in ranked_rows:
        did = expected_row["job_discovery_id"]
        assert by_disc.get(did) == expected_row["rank"], (
            f"Rank mismatch for {did}: expected {expected_row['rank']}, got {by_disc.get(did)}"
        )


# ---------------------------------------------------------------------------
# Tests — M6: Stale ranks cleared for jobs that dropped out of top-N
# ---------------------------------------------------------------------------

def test_dual_write_clears_stale_ranks():
    """Jobs that previously had rank but are NOT in current ranked_rows get rank=None."""
    user_id = "user-xyz"
    n = 5
    ranked_rows = _make_ranked_rows(user_id, n, start_disc_id=1)
    top_disc_ids = [r["job_discovery_id"] for r in ranked_rows]

    # Extra rows that WERE ranked last cycle (disc-0006, disc-0007) — should be cleared
    stale_disc_ids = ["disc-0006", "disc-0007"]
    all_scores = (
        _make_job_score_rows(user_id, top_disc_ids, [None] * n)
        + _make_job_score_rows(user_id, stale_disc_ids, [3, 5])  # previously ranked
    )
    sb = FakeSupabaseClient(job_scores_rows=all_scores)

    _dual_write_job_scores_rank(sb, user_id, ranked_rows)

    stale_rows = [
        row for row in sb._job_scores.rows
        if row["job_discovery_id"] in stale_disc_ids
    ]
    for row in stale_rows:
        assert row["rank"] is None, (
            f"Stale rank not cleared for {row['job_discovery_id']}: rank={row['rank']}"
        )


# ---------------------------------------------------------------------------
# Tests — Graceful degradation on missing column (42703)
# ---------------------------------------------------------------------------

def test_dual_write_ignores_missing_column_error(caplog):
    """If job_scores.rank column doesn't exist (migration 052 not run), log warning and continue."""
    import logging

    user_id = "user-degraded"
    ranked_rows = _make_ranked_rows(user_id, 3)

    class _ErrorTable:
        def update(self, *_a, **_kw):
            raise RuntimeError("column rank of relation job_scores does not exist (42703)")

        def upsert(self, *_a, **_kw):
            raise RuntimeError("column rank of relation job_scores does not exist (42703)")

    class _ErrorSb:
        def table(self, name: str):
            return _ErrorTable()

    with caplog.at_level(logging.WARNING, logger="app.pipeline.recommender"):
        # Should NOT raise — error is swallowed
        _dual_write_job_scores_rank(_ErrorSb(), user_id, ranked_rows)

    assert any("42703" in msg or "rank" in msg.lower() for msg in caplog.messages), (
        "Expected a warning log about missing column"
    )


# ---------------------------------------------------------------------------
# Tests — No-op on empty ranked list
# ---------------------------------------------------------------------------

def test_dual_write_noop_on_empty():
    """_dual_write_job_scores_rank with empty list does nothing."""
    sb = FakeSupabaseClient()
    # Should not raise
    _dual_write_job_scores_rank(sb, "user-empty", [])
    assert sb._job_scores.rows == []


# ---------------------------------------------------------------------------
# Tests — M9: Non-42703 exception with "rank" in message → classified ERROR
# ---------------------------------------------------------------------------

def test_non_42703_rank_substring_error_is_logged_as_error(caplog):
    """An exception whose message contains 'rank' but is NOT a 42703 error must be
    classified as ERROR — not silently swallowed as a warning.

    Regression guard for BLOCKER #1: the old code matched 'rank' substring, which
    would silently drop real failures such as a constraint named 'valid_rank' or a
    foreign-key error mentioning 'rank_id'.
    """
    import logging

    user_id = "user-error-classify"
    ranked_rows = _make_ranked_rows(user_id, 3)

    class _AmbiguousRankErrorTable:
        """Raises a non-42703 error whose message happens to contain 'rank'."""

        def upsert(self, *_a, **_kw):
            # e.g. FK violation on a column named "ranking_score", or a network
            # error on a URL that happens to contain "/rank/".
            raise RuntimeError("insert violates foreign key constraint valid_rank_fk on ranking_score")

        def update(self, *_a, **_kw):
            return self  # Phase 2 UPDATE — won't be reached but kept for safety

    class _AmbiguousSb:
        def table(self, name: str):
            return _AmbiguousRankErrorTable()

    with caplog.at_level(logging.DEBUG, logger="app.pipeline.recommender"):
        _dual_write_job_scores_rank(_AmbiguousSb(), user_id, ranked_rows)

    # Must have logged at ERROR level, not just WARNING
    error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert error_records, (
        "Expected at least one ERROR-level log for non-42703 exception containing 'rank'; "
        "got only: " + str([r.levelname + ": " + r.message for r in caplog.records])
    )
    # Must NOT have logged a misleading warning about missing column
    warning_about_migration = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "migration 052" in r.message
    ]
    assert not warning_about_migration, (
        "Non-42703 error was incorrectly classified as missing-column warning"
    )


# ---------------------------------------------------------------------------
# Tests — M10: Single upsert call regardless of ranked_rows length
# ---------------------------------------------------------------------------

def test_dual_write_issues_single_upsert_call():
    """_dual_write_job_scores_rank must issue exactly ONE upsert call (not N per-row).

    Regression guard for BLOCKER #2: the old code had a per-row UPDATE loop,
    which issued N sequential REST calls — N+1 query pattern.
    """
    user_id = "user-batch"
    n = 20  # deliberately choose TOP_K to stress-test
    ranked_rows = _make_ranked_rows(user_id, n)
    disc_ids = [r["job_discovery_id"] for r in ranked_rows]

    initial_scores = _make_job_score_rows(user_id, disc_ids, [None] * n)
    sb = FakeSupabaseClient(job_scores_rows=initial_scores)

    _dual_write_job_scores_rank(sb, user_id, ranked_rows)

    assert sb._job_scores.upsert_call_count == 1, (
        f"Expected exactly 1 upsert call, got {sb._job_scores.upsert_call_count}. "
        "N+1 query pattern must be replaced with a single batched upsert."
    )


# ---------------------------------------------------------------------------
# Tests — M3: verify user_daily_top_20 write is preserved (structural check)
# ---------------------------------------------------------------------------

def test_user_daily_top_20_write_path_untouched():
    """compute_and_store_top_20 source still contains user_daily_top_20 insert.

    We read the source directly (no import needed) to confirm the legacy write
    path was not removed.
    """
    import inspect
    import importlib.util

    # Read raw source — simplest and avoids module-import side effects
    with open(os.path.join(_WORKER_ROOT, "app", "pipeline", "recommender.py")) as f:
        src = f.read()

    # The legacy insert must still be present
    assert 'sb.table("user_daily_top_20").insert' in src, (
        "user_daily_top_20 insert was removed — Stage 2 must preserve the old write path"
    )
    # The dual-write call must also be present
    assert "_dual_write_job_scores_rank" in src, (
        "_dual_write_job_scores_rank call missing from compute_and_store_top_20"
    )


# ---------------------------------------------------------------------------
# Tests — M12/M13/M14/M15: migration 054 structural verification
# ---------------------------------------------------------------------------

def _read_migration(filename: str) -> str:
    """Read a migration file from website/db/migrations/ relative to the worktree root."""
    # _WORKER_ROOT is worker/ — go up one level to repo root, then into website/
    repo_root = os.path.abspath(os.path.join(_WORKER_ROOT, ".."))
    migration_path = os.path.join(repo_root, "website", "db", "migrations", filename)
    with open(migration_path) as f:
        return f.read()


def test_migration_054_exists_and_contains_constraint():
    """M12/M13: migration 054 file exists and adds the expected UNIQUE CONSTRAINT.

    This catches the regression where a developer ships the upsert code but
    forgets to add the migration that makes ON CONFLICT inference work.
    """
    sql = _read_migration("054_job_scores_unique_constraint.sql")

    # Must define the correct constraint name
    assert "uq_job_scores_user_discovery" in sql, (
        "Migration 054 must define constraint 'uq_job_scores_user_discovery'. "
        "PostgREST ON CONFLICT inference needs this exact non-partial constraint."
    )

    # Must be an ADD CONSTRAINT ... UNIQUE statement (not just an index)
    assert "ADD CONSTRAINT" in sql.upper(), (
        "Migration 054 must use ADD CONSTRAINT, not just CREATE INDEX. "
        "Only a UNIQUE CONSTRAINT (not a partial index) satisfies ON CONFLICT column-list inference."
    )

    # Must target the correct columns
    assert "user_id" in sql and "job_discovery_id" in sql, (
        "Migration 054 must reference both user_id and job_discovery_id columns."
    )


def test_migration_054_has_duplicate_guard():
    """M14: migration 054 contains the defensive duplicate-count guard.

    The DO $$ block prevents the ALTER TABLE from failing on a dirty DB by
    raising a descriptive error first.  Without this guard, the migration would
    fail with a generic Postgres constraint-violation message that is hard to
    diagnose.
    """
    sql = _read_migration("054_job_scores_unique_constraint.sql")

    assert "DO $$" in sql, (
        "Migration 054 must contain a DO $$ block for the duplicate-count guard."
    )
    assert "duplicate_count" in sql, (
        "Migration 054 DO $$ block must check for existing duplicate (user_id, job_discovery_id) pairs."
    )
    assert "RAISE EXCEPTION" in sql, (
        "Migration 054 DO $$ block must RAISE EXCEPTION when duplicates are found."
    )


def test_upsert_on_conflict_columns_match_constraint():
    """M15: recommender.py upsert on_conflict columns match migration 054 constraint columns.

    Reads both files as text. No Postgres connection needed — this is a pure
    source-level consistency check that catches typos in column names and ensures
    the constraint and the call site stay in sync.
    """
    # Read recommender source
    recommender_path = os.path.join(_WORKER_ROOT, "app", "pipeline", "recommender.py")
    with open(recommender_path) as f:
        recommender_src = f.read()

    # The upsert call must use the correct column list
    assert 'on_conflict="user_id,job_discovery_id"' in recommender_src, (
        "recommender.py upsert must use on_conflict='user_id,job_discovery_id' "
        "to match the uq_job_scores_user_discovery constraint from migration 054."
    )

    # Migration 054 must define those same two columns as the constraint
    sql = _read_migration("054_job_scores_unique_constraint.sql")
    assert "UNIQUE (user_id, job_discovery_id)" in sql, (
        "Migration 054 constraint must be UNIQUE (user_id, job_discovery_id) — "
        "column order must match the on_conflict parameter in recommender.py."
    )
