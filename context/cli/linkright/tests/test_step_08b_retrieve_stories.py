"""Tests for `step_08b_retrieve_stories` — Story Bank ↔ tailor pipeline bridge.

Verifies retrieval logic + persistence without exercising the full 16-step
pipeline. Mocks MongoDB collection and the Oracle embedder.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_ROOT = Path(__file__).parents[1] / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ── Minimal in-memory FakeCollection (mirrors test_stories_cli.py) ─────────

class FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    def __iter__(self):
        return iter(self._docs)


class FakeCollection:
    def __init__(self):
        self.docs = []

    @staticmethod
    def _matches(doc, query):
        for k, v in query.items():
            if k == "$or":
                if not any(FakeCollection._matches(doc, sub) for sub in v):
                    return False
                continue
            actual = doc.get(k)
            if isinstance(v, dict):
                if "$regex" in v:
                    pattern = v["$regex"]
                    flags = re.IGNORECASE if v.get("$options") == "i" else 0
                    if isinstance(actual, list):
                        if not any(re.search(pattern, str(item), flags) for item in actual):
                            return False
                    else:
                        if actual is None or not re.search(pattern, str(actual), flags):
                            return False
                elif "$ne" in v:
                    if actual == v["$ne"]:
                        return False
                else:
                    raise NotImplementedError(f"unsupported op {list(v.keys())} on {k}")
            else:
                if actual != v:
                    return False
        return True

    def find(self, query):
        return FakeCursor([d for d in self.docs if self._matches(d, query)])

    def insert_one(self, doc):
        self.docs.append({"_id": f"oid-{len(self.docs)}", **doc})


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_artifacts(tmp_path, monkeypatch):
    """Repoint orchestrator's ARTIFACTS + neutralize logbook for step_08b
    tests. logbook.append() writes to a fixed `resume/logs/pipeline.log`
    that doesn't exist in test envs; we no-op it."""
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()

    from linkright.resume import orchestrator
    monkeypatch.setattr(orchestrator, "ARTIFACTS", artifacts)
    # Neutralize logbook.append + log() — both write to fixed paths under
    # `resume/logs/` that don't exist in test envs
    monkeypatch.setattr(orchestrator.logbook, "append",
                        lambda *a, **kw: None)
    monkeypatch.setattr(orchestrator, "log", lambda *a, **kw: None)
    return artifacts


@pytest.fixture
def fake_db_and_embedder(monkeypatch):
    """Set up a fake MongoDB + a controllable embedder for step_08b."""
    coll = FakeCollection()
    fake_db = {"career_stories": coll}

    monkeypatch.setattr("linkright.db.mongo.get_db", lambda: fake_db)
    monkeypatch.setattr("linkright.db.mongo.ping", lambda: True)
    return coll


# ── Tests ──────────────────────────────────────────────────────────────────

def test_returns_empty_when_mongo_unreachable(monkeypatch, tmp_artifacts):
    """If MongoDB ping fails, step_08b skips cleanly and returns []."""
    monkeypatch.setattr("linkright.db.mongo.ping", lambda: False)

    from linkright.resume import orchestrator

    result = orchestrator.step_08b_retrieve_stories({"jd_keywords": ["AML"], "role_title": "PM"})
    assert result == []
    # No artifact file written
    assert not (tmp_artifacts / "08b_retrieved_stories.json").exists()


def test_returns_empty_when_no_query_signal(monkeypatch, tmp_artifacts, fake_db_and_embedder):
    """No JD keywords AND no role title → can't build a query → skip."""
    from linkright.resume import orchestrator

    result = orchestrator.step_08b_retrieve_stories({})
    assert result == []


def test_text_fallback_returns_matches(monkeypatch, tmp_artifacts, fake_db_and_embedder):
    """When embedder returns nothing, regex fallback fires and finds stories."""
    fake_db_and_embedder.insert_one({
        "user_id": "local",
        "title": "AmEx AML Migration",
        "situation": "Pipeline broke", "task": "Restore in 24h",
        "action": "Built oracle for AML signals",
        "result": "$1.2M annual savings",
        "tags": ["python", "leadership"],
        "emb": None,
    })
    fake_db_and_embedder.insert_one({
        "user_id": "local",
        "title": "Stripe API Refactor",
        "situation": "Latency", "task": "Reduce p99",
        "action": "Designed REST endpoints",
        "result": "10x throughput",
        "tags": ["api", "performance"],
        "emb": None,
    })

    from linkright.resume import orchestrator
    # Force vector path to fail by making embedder return falsy
    monkeypatch.setattr(orchestrator.embedder, "embed", lambda q: ([], {}))

    result = orchestrator.step_08b_retrieve_stories({
        "jd_keywords": ["AML", "compliance"],
        "role_title": "Risk PM",
    })

    titles = [r["title"] for r in result]
    assert "AmEx AML Migration" in titles
    assert "Stripe API Refactor" not in titles
    # Persisted artifact
    artifact = tmp_artifacts / "08b_retrieved_stories.json"
    assert artifact.exists()
    persisted = json.loads(artifact.read_text())
    assert len(persisted) == 1
    assert persisted[0]["title"] == "AmEx AML Migration"


def test_vector_path_ranks_by_cosine(monkeypatch, tmp_artifacts, fake_db_and_embedder):
    """When embedder returns vectors, all stories with emb get cosine-scored
    and top-k returned by descending score."""
    fake_db_and_embedder.insert_one({
        "user_id": "local",
        "title": "High Match Story", "action": "x", "result": "y",
        "emb": [1.0, 0.0, 0.0],
    })
    fake_db_and_embedder.insert_one({
        "user_id": "local",
        "title": "Low Match Story", "action": "x", "result": "y",
        "emb": [0.0, 0.0, 1.0],
    })
    fake_db_and_embedder.insert_one({
        "user_id": "local",
        "title": "Mid Match Story", "action": "x", "result": "y",
        "emb": [0.7, 0.7, 0.0],
    })
    # Story without embedding — should NOT surface in vector path
    fake_db_and_embedder.insert_one({
        "user_id": "local",
        "title": "No Embedding Story", "action": "x", "result": "y",
        "emb": None,
    })

    from linkright.resume import orchestrator
    # Embedder returns a unit vector aligned with "High Match Story"
    monkeypatch.setattr(orchestrator.embedder, "embed", lambda q: ([1.0, 0.0, 0.0], {}))

    result = orchestrator.step_08b_retrieve_stories({
        "jd_keywords": ["x"], "role_title": "PM",
    }, k=10)

    titles = [r["title"] for r in result]
    # All 3 stories with emb should surface, ranked by cosine
    assert titles[0] == "High Match Story"  # cosine = 1.0
    assert "Mid Match Story" in titles
    assert "Low Match Story" in titles
    assert "No Embedding Story" not in titles  # filtered out by emb-not-null


def test_persists_with_score_field(monkeypatch, tmp_artifacts, fake_db_and_embedder):
    """Each persisted story has a numeric `score` field (cosine or fallback)."""
    fake_db_and_embedder.insert_one({
        "user_id": "local",
        "title": "AML Story", "action": "x", "result": "y",
        "tags": ["compliance"], "emb": None,
    })

    from linkright.resume import orchestrator
    monkeypatch.setattr(orchestrator.embedder, "embed", lambda q: ([], {}))

    result = orchestrator.step_08b_retrieve_stories(
        {"jd_keywords": ["AML"], "role_title": "Compliance PM"},
    )
    # Text fallback → score = 0.5
    assert len(result) == 1
    assert result[0]["score"] == 0.5

    persisted = json.loads((tmp_artifacts / "08b_retrieved_stories.json").read_text())
    assert isinstance(persisted[0]["score"], float)


def test_caps_at_k_results(monkeypatch, tmp_artifacts, fake_db_and_embedder):
    """k argument caps both vector and text-fallback paths."""
    for i in range(20):
        fake_db_and_embedder.insert_one({
            "user_id": "local",
            "title": f"Story {i}",
            "action": "AML thing", "result": "y",
            "tags": [], "emb": None,
        })

    from linkright.resume import orchestrator
    monkeypatch.setattr(orchestrator.embedder, "embed", lambda q: ([], {}))

    result = orchestrator.step_08b_retrieve_stories(
        {"jd_keywords": ["AML"], "role_title": "PM"},
        k=5,
    )
    assert len(result) == 5


def test_serialization_shape(monkeypatch, tmp_artifacts, fake_db_and_embedder):
    """Persisted entries have stable, JSON-safe schema."""
    fake_db_and_embedder.insert_one({
        "user_id": "local",
        "title": "Shape Test",
        "situation": "S", "task": "T",
        "action": "A shape thing", "result": "R shape outcome",
        "tags": ["t1", "t2"], "emb": None,
    })

    from linkright.resume import orchestrator
    monkeypatch.setattr(orchestrator.embedder, "embed", lambda q: ([], {}))

    result = orchestrator.step_08b_retrieve_stories(
        {"jd_keywords": ["shape"], "role_title": "PM"},
    )
    assert len(result) == 1
    r = result[0]
    expected_keys = {"_id", "title", "situation", "task", "action", "result", "tags", "score"}
    assert set(r.keys()) == expected_keys
    assert r["title"] == "Shape Test"
    assert r["situation"] == "S"
    assert r["tags"] == ["t1", "t2"]
    # Roundtrip JSON
    persisted = json.loads((tmp_artifacts / "08b_retrieved_stories.json").read_text())
    assert persisted == result
