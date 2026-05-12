"""Tests for `linkright stories` — Pillar 3 Story Bank CRUD.

Covers: schema validation, CRUD flows, --from-nugget pre-fill, prefix
resolution, text-search fallback, MongoDB-unreachable error path.

We use a minimal in-memory `FakeCollection` because mongomock isn't a
declared test dep and MagicMock-on-pymongo gets noisy fast (find().sort()
.limit() chain is awkward to mock cleanly).
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from click.testing import CliRunner

_ROOT = Path(__file__).parents[1] / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from linkright.db.collections import CareerStory, COLLECTIONS, VECTOR_COLLECTIONS  # noqa: E402
from linkright.stories.cli import stories_group, _resolve_story  # noqa: E402


# ── Minimal in-memory FakeCollection ───────────────────────────────────────

class FakeObjectId:
    """Stand-in for bson.ObjectId — unique 24-char hex string."""
    _counter = 0

    def __init__(self, hex_str: str | None = None):
        if hex_str is None:
            FakeObjectId._counter += 1
            hex_str = f"{FakeObjectId._counter:024x}"
        if not re.match(r"^[0-9a-f]{24}$", hex_str):
            raise ValueError(f"invalid ObjectId: {hex_str}")
        self.hex_str = hex_str

    def __str__(self) -> str:
        return self.hex_str

    def __eq__(self, other) -> bool:
        return isinstance(other, FakeObjectId) and self.hex_str == other.hex_str

    def __hash__(self) -> int:
        return hash(self.hex_str)


class FakeInsertResult:
    def __init__(self, oid: FakeObjectId):
        self.inserted_id = oid


class FakeCursor:
    """Supports .sort() + .limit() chain like pymongo."""
    def __init__(self, docs: list[dict]):
        self._docs = list(docs)

    def sort(self, key, direction=-1):
        if isinstance(key, str):
            self._docs.sort(key=lambda d: d.get(key) or datetime.min.replace(tzinfo=timezone.utc),
                            reverse=(direction == -1))
        return self

    def limit(self, n: int):
        self._docs = self._docs[:n]
        return self

    def __iter__(self):
        return iter(self._docs)


class FakeCollection:
    """Minimal pymongo-Collection stand-in with regex + nested-key support."""

    def __init__(self) -> None:
        self.docs: list[dict] = []

    def insert_one(self, doc: dict) -> FakeInsertResult:
        if self._is_duplicate(doc):
            raise ValueError(
                f"E11000 duplicate key error: title '{doc.get('title')}' "
                f"already exists for user_id '{doc.get('user_id')}'"
            )
        oid = FakeObjectId()
        d = {"_id": oid, **doc}
        self.docs.append(d)
        return FakeInsertResult(oid)

    @staticmethod
    def _matches(doc: dict, query: dict) -> bool:
        for k, v in query.items():
            if k == "$or":
                if not any(FakeCollection._matches(doc, sub) for sub in v):
                    return False
                continue
            actual = doc.get(k)
            if isinstance(v, dict):
                if "$regex" in v:
                    pattern = v["$regex"]
                    flags = re.IGNORECASE if v.get("$options", "") == "i" else 0
                    if isinstance(actual, list):
                        if not any(re.search(pattern, str(item), flags) for item in actual):
                            return False
                    else:
                        if actual is None or not re.search(pattern, str(actual), flags):
                            return False
                else:
                    # Fail LOUDLY on unsupported operators so PR 2 fixture reuse
                    # doesn't silently mismatch (e.g., $in / $gte / $ne for the
                    # JD-requirement-id filter). AR round-1 catch.
                    raise NotImplementedError(
                        f"FakeCollection: unsupported query operator(s) {list(v.keys())} "
                        f"on field '{k}'. Extend _matches if PR 2 needs this."
                    )
            else:
                if isinstance(actual, list) and not isinstance(v, list):
                    if v not in actual:
                        return False
                elif actual != v:
                    return False
        return True

    def _is_duplicate(self, doc: dict) -> bool:
        """Mimic the (user_id, title) unique index — block re-add of same title."""
        return any(
            d.get("user_id") == doc.get("user_id") and d.get("title") == doc.get("title")
            for d in self.docs
        )

    def find_one(self, query: dict) -> dict | None:
        for d in self.docs:
            if self._matches(d, query):
                return d
        return None

    def find(self, query: dict) -> FakeCursor:
        return FakeCursor([d for d in self.docs if self._matches(d, query)])

    def update_one(self, query: dict, update: dict) -> None:
        for d in self.docs:
            if self._matches(d, query):
                d.update(update.get("$set", {}))
                return

    def delete_one(self, query: dict) -> None:
        for i, d in enumerate(self.docs):
            if self._matches(d, query):
                self.docs.pop(i)
                return


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def fake_coll(monkeypatch) -> FakeCollection:
    """Patch _get_collection to return our FakeCollection."""
    coll = FakeCollection()
    monkeypatch.setattr("linkright.stories.cli._get_collection", lambda: coll)
    return coll


@pytest.fixture(autouse=True)
def patch_bson_objectid(monkeypatch):
    """Make bson.ObjectId in stories.cli import use our FakeObjectId.

    The stories.cli module imports bson lazily inside _resolve_story, so we
    need to patch the bson module entry in sys.modules.
    """
    fake_bson = type(sys)("bson")  # synthetic module
    fake_bson.ObjectId = FakeObjectId
    fake_bson_errors = type(sys)("bson.errors")
    fake_bson_errors.InvalidId = ValueError
    fake_bson.errors = fake_bson_errors
    monkeypatch.setitem(sys.modules, "bson", fake_bson)
    monkeypatch.setitem(sys.modules, "bson.errors", fake_bson_errors)


# ── Schema validation ──────────────────────────────────────────────────────

class TestCareerStorySchema:
    def test_minimal_valid(self):
        s = CareerStory(title="x", action="did", result="achieved")
        assert s.title == "x"
        assert s.user_id == "local"  # default from Base
        assert s.tags == []
        assert s.use_count == 0
        assert s.last_used_at is None

    def test_rejects_missing_required(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CareerStory(action="did", result="achieved")  # title missing
        with pytest.raises(ValidationError):
            CareerStory(title="x", result="achieved")  # action missing
        with pytest.raises(ValidationError):
            CareerStory(title="x", action="did")  # result missing

    def test_optional_fields_default(self):
        s = CareerStory(title="x", action="did", result="achieved")
        assert s.situation == ""
        assert s.task == ""
        assert s.jd_requirement_ids == []
        assert s.source_nugget_ids == []
        assert s.emb is None

    def test_serialization_roundtrip(self):
        s = CareerStory(
            title="Acme Bank Save", action="Built oracle", result="$1.2M saved",
            tags=["python", "leadership"], use_count=3,
        )
        as_dict = s.model_dump()
        s2 = CareerStory(**as_dict)
        assert s2.title == s.title
        assert s2.tags == ["python", "leadership"]
        assert s2.use_count == 3


# ── Registry checks (catches forgetting to wire migrations) ────────────────

class TestRegistryWiring:
    def test_career_stories_registered_in_collections(self):
        assert "career_stories" in COLLECTIONS
        assert COLLECTIONS["career_stories"] is CareerStory

    def test_career_stories_registered_for_vector_search(self):
        assert "career_stories" in VECTOR_COLLECTIONS
        assert VECTOR_COLLECTIONS["career_stories"] == "emb"


# ── CLI: list ──────────────────────────────────────────────────────────────

class TestListCmd:
    def test_empty(self, runner, fake_coll):
        result = runner.invoke(stories_group, ["list"])
        assert result.exit_code == 0
        assert "No stories yet" in result.output

    def test_filter_by_tag_no_match(self, runner, fake_coll):
        fake_coll.insert_one({
            "user_id": "local", "title": "Story A", "tags": ["python"],
            "action": "x", "result": "y", "updated_at": datetime.now(timezone.utc),
        })
        result = runner.invoke(stories_group, ["list", "--tag", "rust"])
        assert result.exit_code == 0
        assert "No stories with tag 'rust'" in result.output

    def test_populated(self, runner, fake_coll):
        fake_coll.insert_one({
            "user_id": "local", "title": "Acme Bank Oracle Save",
            "action": "Built migration", "result": "$1.2M saved",
            "tags": ["python", "leadership"], "use_count": 3,
            "updated_at": datetime.now(timezone.utc), "last_used_at": None,
        })
        result = runner.invoke(stories_group, ["list"])
        assert result.exit_code == 0
        assert "Acme Bank Oracle Save" in result.output
        assert "python" in result.output


# ── CLI: add ──────────────────────────────────────────────────────────────

class TestAddCmd:
    def test_yes_with_all_flags(self, runner, fake_coll):
        result = runner.invoke(stories_group, [
            "add", "--yes", "--title", "T", "--action", "A", "--result", "R",
            "--tags", "python, leadership",
        ])
        assert result.exit_code == 0, result.output
        assert "Story saved" in result.output
        assert len(fake_coll.docs) == 1
        d = fake_coll.docs[0]
        assert d["title"] == "T"
        assert d["action"] == "A"
        assert d["result"] == "R"
        assert d["tags"] == ["python", "leadership"]
        assert d["use_count"] == 0
        assert d["jd_requirement_ids"] == []
        assert d["source_nugget_ids"] == []
        assert d["situation"] == ""

    def test_yes_missing_required_fails(self, runner, fake_coll):
        # Missing --action when --yes is set
        result = runner.invoke(stories_group, [
            "add", "--yes", "--title", "T", "--result", "R",
        ])
        assert result.exit_code != 0
        assert "required" in result.output

    def test_whitespace_only_title_rejected(self, runner, fake_coll):
        """AR round-1 blocker: whitespace-only inputs must be stripped + rejected
        BEFORE write so they don't become unreachable-by-prefix orphans."""
        result = runner.invoke(stories_group, [
            "add", "--yes", "--title", "   ", "--action", "A", "--result", "R",
        ])
        assert result.exit_code != 0
        assert "required" in result.output
        assert "non-empty" in result.output
        assert len(fake_coll.docs) == 0  # nothing written

    def test_whitespace_only_action_rejected(self, runner, fake_coll):
        result = runner.invoke(stories_group, [
            "add", "--yes", "--title", "T", "--action", "  \t  ", "--result", "R",
        ])
        assert result.exit_code != 0
        assert "non-empty" in result.output

    def test_whitespace_only_result_rejected(self, runner, fake_coll):
        result = runner.invoke(stories_group, [
            "add", "--yes", "--title", "T", "--action", "A", "--result", " ",
        ])
        assert result.exit_code != 0
        assert "non-empty" in result.output

    def test_padded_inputs_stripped_before_save(self, runner, fake_coll):
        """Leading/trailing whitespace stripped — exact strings stored."""
        result = runner.invoke(stories_group, [
            "add", "--yes",
            "--title", "  Padded Title  ",
            "--action", "  did stuff  ",
            "--result", "  outcome  ",
            "--tags", "  python , leadership  ",
        ])
        assert result.exit_code == 0, result.output
        d = fake_coll.docs[0]
        assert d["title"] == "Padded Title"
        assert d["action"] == "did stuff"
        assert d["result"] == "outcome"
        assert d["tags"] == ["python", "leadership"]

    def test_duplicate_title_friendly_error(self, runner, fake_coll):
        """AR round-1 blocker: the (user_id, title) unique index rejects
        duplicates. The CLI must catch DuplicateKeyError-like exceptions and
        surface an actionable message instead of a stack trace."""
        # Insert one
        runner.invoke(stories_group, [
            "add", "--yes", "--title", "Same Name",
            "--action", "A", "--result", "R",
        ])
        assert len(fake_coll.docs) == 1
        # Try to insert again with the same title
        result = runner.invoke(stories_group, [
            "add", "--yes", "--title", "Same Name",
            "--action", "different", "--result", "different",
        ])
        assert result.exit_code != 0
        assert "already exists" in result.output
        assert "Same Name" in result.output
        assert len(fake_coll.docs) == 1  # Second insert blocked

    def test_interactive_prompts(self, runner, fake_coll):
        # User types each field at the prompt
        result = runner.invoke(stories_group, ["add"], input=(
            "My Title\n"
            "Some context\n"
            "Build the thing\n"
            "Did it\n"
            "Achieved $1M\n"
            "tag1, tag2\n"
        ))
        assert result.exit_code == 0, result.output
        assert "Story saved" in result.output
        d = fake_coll.docs[0]
        assert d["title"] == "My Title"
        assert d["situation"] == "Some context"
        assert d["task"] == "Build the thing"
        assert d["action"] == "Did it"
        assert d["result"] == "Achieved $1M"
        assert d["tags"] == ["tag1", "tag2"]

    def test_from_nugget_prefills_result(self, runner, fake_coll, monkeypatch):
        # Mock _resolve_nugget to return a fake nugget
        monkeypatch.setattr(
            "linkright.stories.cli._resolve_nugget",
            lambda q: ("Drove $1.2M in savings via AML automation", "nugget-xyz"),
        )
        # User accepts prefilled `result`, fills other fields
        result = runner.invoke(stories_group, [
            "add", "--from-nugget", "AML",
            "--yes", "--title", "Acme Bank", "--action", "Built oracle",
        ])
        assert result.exit_code == 0, result.output
        d = fake_coll.docs[0]
        assert d["result"] == "Drove $1.2M in savings via AML automation"
        assert d["source_nugget_ids"] == ["nugget-xyz"]

    def test_from_nugget_no_match(self, runner, fake_coll, monkeypatch):
        monkeypatch.setattr(
            "linkright.stories.cli._resolve_nugget",
            lambda q: (None, None),
        )
        result = runner.invoke(stories_group, [
            "add", "--from-nugget", "nonexistent",
            "--yes", "--title", "T", "--action", "A", "--result", "R",
        ])
        assert result.exit_code == 0, result.output
        assert "No nugget matched" in result.output
        d = fake_coll.docs[0]
        assert d["source_nugget_ids"] == []


# ── CLI: edit ─────────────────────────────────────────────────────────────

class TestEditCmd:
    def test_edit_by_title_prefix(self, runner, fake_coll):
        fake_coll.insert_one({
            "user_id": "local", "title": "Acme Bank Save",
            "action": "Old action", "result": "Old result",
            "situation": "", "task": "", "tags": ["x"],
        })
        # Edit: keep title, change action, keep rest
        result = runner.invoke(stories_group, ["edit", "Acme Bank"], input=(
            "\n"                # title — keep
            "\n"                # situation — keep
            "\n"                # task — keep
            "New action\n"      # action — change
            "\n"                # result — keep
            "\n"                # tags — keep
        ))
        assert result.exit_code == 0, result.output
        assert "Updated" in result.output
        assert fake_coll.docs[0]["action"] == "New action"
        assert fake_coll.docs[0]["result"] == "Old result"

    def test_edit_not_found(self, runner, fake_coll):
        result = runner.invoke(stories_group, ["edit", "Nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_edit_no_changes(self, runner, fake_coll):
        fake_coll.insert_one({
            "user_id": "local", "title": "Test Story",
            "action": "a", "result": "r",
            "situation": "", "task": "", "tags": [],
        })
        # Press Enter at every prompt — keep all current values
        result = runner.invoke(stories_group, ["edit", "Test"], input="\n\n\n\n\n\n")
        assert result.exit_code == 0
        assert "No changes" in result.output

    def test_edit_rejects_empty_title(self, runner, fake_coll):
        """AR round-2 blocker fix: edit must validate non-empty title (same
        guard as add). Previously a user could clear the title field and
        write a corrupt document."""
        fake_coll.insert_one({
            "user_id": "local", "title": "Test Story",
            "action": "a", "result": "r",
            "situation": "", "task": "", "tags": [],
        })
        # User clears title → input "  \n" then Enter for rest
        result = runner.invoke(stories_group, ["edit", "Test"], input=(
            "   \n"     # title — clear
            "\n"        # situation — keep
            "\n"        # task — keep
            "\n"        # action — keep
            "\n"        # result — keep
            "\n"        # tags — keep
        ))
        assert result.exit_code != 0
        assert "cannot be empty" in result.output
        # Document still has original title
        assert fake_coll.docs[0]["title"] == "Test Story"

    def test_edit_rejects_empty_action(self, runner, fake_coll):
        fake_coll.insert_one({
            "user_id": "local", "title": "Test Story",
            "action": "old action", "result": "r",
            "situation": "", "task": "", "tags": [],
        })
        result = runner.invoke(stories_group, ["edit", "Test"], input=(
            "\n"        # title — keep
            "\n"        # situation — keep
            "\n"        # task — keep
            " \n"       # action — clear (whitespace)
            "\n"        # result — keep
            "\n"        # tags — keep
        ))
        assert result.exit_code != 0
        assert "cannot be empty" in result.output
        assert fake_coll.docs[0]["action"] == "old action"

    def test_edit_strips_whitespace(self, runner, fake_coll):
        """Edit must strip leading/trailing whitespace before saving (same as add)."""
        fake_coll.insert_one({
            "user_id": "local", "title": "Padded Title",
            "action": "old", "result": "r",
            "situation": "", "task": "", "tags": [],
        })
        result = runner.invoke(stories_group, ["edit", "Padded"], input=(
            "\n"                # title — keep
            "\n"                # situation — keep
            "\n"                # task — keep
            "  new action  \n"  # action — change with surrounding whitespace
            "\n"                # result — keep
            "\n"                # tags — keep
        ))
        assert result.exit_code == 0, result.output
        assert "Updated" in result.output
        assert fake_coll.docs[0]["action"] == "new action"  # stripped on save


# ── CLI: delete ───────────────────────────────────────────────────────────

class TestDeleteCmd:
    def test_delete_with_yes(self, runner, fake_coll):
        fake_coll.insert_one({
            "user_id": "local", "title": "Doomed", "action": "a", "result": "r",
            "situation": "", "task": "", "tags": [],
        })
        result = runner.invoke(stories_group, ["delete", "Doomed", "--yes"])
        assert result.exit_code == 0, result.output
        assert "Deleted: Doomed" in result.output
        assert fake_coll.docs == []

    def test_delete_confirm_no_aborts(self, runner, fake_coll):
        fake_coll.insert_one({
            "user_id": "local", "title": "Saved", "action": "a", "result": "r",
            "situation": "", "task": "", "tags": [],
        })
        result = runner.invoke(stories_group, ["delete", "Saved"], input="n\n")
        assert result.exit_code == 0
        assert "Cancelled" in result.output
        assert len(fake_coll.docs) == 1  # not deleted

    def test_delete_not_found(self, runner, fake_coll):
        result = runner.invoke(stories_group, ["delete", "Ghost", "--yes"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()


# ── CLI: search ───────────────────────────────────────────────────────────

class TestSearchCmd:
    def test_search_text_fallback(self, runner, fake_coll, monkeypatch):
        # Mock Oracle to fail → text fallback path
        monkeypatch.setattr(
            "linkright.stories.cli.stories_group", stories_group,
        )
        fake_coll.insert_one({
            "user_id": "local", "title": "Acme Bank Migration",
            "action": "Built oracle to AML", "result": "$1.2M saved",
            "tags": ["python"],
        })
        fake_coll.insert_one({
            "user_id": "local", "title": "Stripe API",
            "action": "Designed REST integration", "result": "10x velocity",
            "tags": ["api"],
        })
        # Force Oracle unavailable by patching its import to raise
        with patch.dict(sys.modules, {"linkright.llm.oracle": None}):
            result = runner.invoke(stories_group, ["search", "oracle"])
        assert result.exit_code == 0, result.output
        # "Acme Bank Migration" matches via "oracle" in action
        assert "Acme Bank Migration" in result.output
        assert "Stripe API" not in result.output

    def test_search_no_match(self, runner, fake_coll):
        fake_coll.insert_one({
            "user_id": "local", "title": "X", "action": "a", "result": "r",
            "tags": [],
        })
        with patch.dict(sys.modules, {"linkright.llm.oracle": None}):
            result = runner.invoke(stories_group, ["search", "zzznothing"])
        assert result.exit_code == 0
        assert "No stories matching" in result.output

    def test_search_query_too_short(self, runner, fake_coll):
        with patch.dict(sys.modules, {"linkright.llm.oracle": None}):
            result = runner.invoke(stories_group, ["search", "ab"])
        assert result.exit_code == 0
        assert "too short" in result.output.lower()


# ── _resolve_story helper ─────────────────────────────────────────────────

class TestResolveStory:
    def test_resolves_by_objectid_string(self, fake_coll):
        oid = FakeObjectId()
        fake_coll.docs.append({
            "_id": oid, "user_id": "local", "title": "X",
        })
        doc = _resolve_story(fake_coll, str(oid))
        assert doc is not None
        assert doc["title"] == "X"

    def test_resolves_by_title_prefix(self, fake_coll):
        fake_coll.insert_one({
            "user_id": "local", "title": "Unique Story Title",
        })
        doc = _resolve_story(fake_coll, "Unique")
        assert doc is not None
        assert doc["title"] == "Unique Story Title"

    def test_returns_none_when_not_found(self, fake_coll):
        assert _resolve_story(fake_coll, "Ghost") is None

    def test_ambiguous_prefix_exits_with_error(self, fake_coll):
        fake_coll.insert_one({"user_id": "local", "title": "AAA First"})
        fake_coll.insert_one({"user_id": "local", "title": "AAA Second"})
        with pytest.raises(SystemExit):
            _resolve_story(fake_coll, "AAA")


# ── MongoDB-unreachable error path ────────────────────────────────────────

def test_get_collection_exits_when_mongo_unreachable(runner, monkeypatch):
    """If `ping()` returns False, _get_collection should print actionable
    error and exit non-zero."""
    monkeypatch.setattr("linkright.db.mongo.ping", lambda: False)
    # Don't use the fake_coll fixture — let the real _get_collection fire
    result = runner.invoke(stories_group, ["list"])
    assert result.exit_code == 1
    assert "MongoDB unreachable" in result.output
    assert "linkright init" in result.output


# ── FakeCollection contract — fail loudly on unsupported ops (AR round-1) ──

class TestFakeCollectionRobustness:
    """The fixture itself must fail loudly when PR 2 uses query operators it
    doesn't support, so tests don't silently pass with wrong results."""

    def test_unknown_operator_raises(self):
        coll = FakeCollection()
        coll.insert_one({"user_id": "local", "title": "X", "tags": ["a"]})
        # PR 2 might use $in for tag filtering — fixture must holler
        with pytest.raises(NotImplementedError, match="unsupported query operator"):
            coll.find_one({"user_id": "local", "tags": {"$in": ["a", "b"]}})

    def test_gte_operator_raises(self):
        # PR 2 might use $gte for last_used_at filtering
        coll = FakeCollection()
        coll.insert_one({"user_id": "local", "title": "X", "use_count": 5})
        with pytest.raises(NotImplementedError):
            coll.find_one({"use_count": {"$gte": 3}})


# ── retrieve_stars now reads career_stories (AR round-1 wire-up) ──────────

class TestRetrieveStarsReadsCareerStories:
    """AR round-1 blocker fix: `retrieve_stars()` must surface stories from
    the new `career_stories` collection so `linkright interview prep` works
    end-to-end after `linkright stories add`."""

    def test_reads_from_career_stories_primary(self, monkeypatch):
        from linkright.interview import star_retriever as sr

        career_coll = FakeCollection()
        career_coll.insert_one({
            "user_id": "local",
            "title": "Acme Bank AML Save",
            "situation": "Pipeline broke", "task": "Restore in 24h",
            "action": "Built oracle", "result": "$1.2M saved",
            "tags": ["python"],
        })
        legacy_coll = FakeCollection()  # empty — no legacy data

        fake_db = {"career_stories": career_coll, "user_context": legacy_coll}
        monkeypatch.setattr("linkright.db.mongo.get_db", lambda: fake_db)
        monkeypatch.setattr("linkright.db.mongo.ping", lambda: True)
        # Force vector path to fail → text fallback fires
        monkeypatch.setattr(sr, "oracle_embed", lambda *a, **kw: [])

        results = sr.retrieve_stars("AML pipeline")
        assert len(results) == 1
        assert results[0]["title"] == "Acme Bank AML Save"
        # `body` is composed from STAR fields
        assert "Pipeline broke" in results[0]["body"]
        assert "Built oracle" in results[0]["body"]
        assert "$1.2M saved" in results[0]["body"]

    def test_falls_back_to_legacy_user_context_when_career_stories_empty(self, monkeypatch):
        from linkright.interview import star_retriever as sr

        career_coll = FakeCollection()  # empty — new user
        legacy_coll = FakeCollection()
        legacy_coll.insert_one({
            "user_id": "local", "kind": "story",
            "title": "Old Story",
            "body": "Pre-Story-Bank narrative about AML",
            "tags": ["python"],
        })

        fake_db = {"career_stories": career_coll, "user_context": legacy_coll}
        monkeypatch.setattr("linkright.db.mongo.get_db", lambda: fake_db)
        monkeypatch.setattr("linkright.db.mongo.ping", lambda: True)
        monkeypatch.setattr(sr, "oracle_embed", lambda *a, **kw: [])

        results = sr.retrieve_stars("AML pipeline")
        assert len(results) == 1
        assert results[0]["title"] == "Old Story"
        assert "Pre-Story-Bank narrative" in results[0]["body"]

    def test_merges_career_stories_with_legacy_debriefs(self, monkeypatch):
        """AR round-2 blocker fix: `linkright interview debrief` writes to
        `user_context`. Previous all-or-nothing precedence (career_stories
        wins, legacy dropped entirely) caused debrief notes to silently
        disappear from interview prep the moment a user added one story bank
        entry. Now BOTH surface, with career_stories ranked first."""
        from linkright.interview import star_retriever as sr

        career_coll = FakeCollection()
        career_coll.insert_one({
            "user_id": "local", "title": "AML Migration Story",
            "action": "AML thing", "result": "saved money", "tags": [],
        })
        legacy_coll = FakeCollection()
        legacy_coll.insert_one({
            "user_id": "local", "kind": "story",
            "title": "Past AML Debrief", "body": "AML narrative from interview", "tags": ["debrief"],
        })

        fake_db = {"career_stories": career_coll, "user_context": legacy_coll}
        monkeypatch.setattr("linkright.db.mongo.get_db", lambda: fake_db)
        monkeypatch.setattr("linkright.db.mongo.ping", lambda: True)
        monkeypatch.setattr(sr, "oracle_embed", lambda *a, **kw: [])

        results = sr.retrieve_stars("AML")
        titles = [r["title"] for r in results]
        # BOTH surface — career_stories first, legacy second
        assert "AML Migration Story" in titles
        assert "Past AML Debrief" in titles
        assert titles.index("AML Migration Story") < titles.index("Past AML Debrief")

    def test_merge_dedup_by_id(self, monkeypatch):
        """If somehow the same _id appears in both collections (unlikely but
        possible during legacy migration), dedup by _id — primary wins."""
        from linkright.interview import star_retriever as sr

        shared_id = FakeObjectId()
        career_coll = FakeCollection()
        career_coll.docs.append({
            "_id": shared_id, "user_id": "local",
            "title": "Career Version",
            "action": "AML", "result": "saved", "tags": [],
        })
        legacy_coll = FakeCollection()
        legacy_coll.docs.append({
            "_id": shared_id, "user_id": "local", "kind": "story",
            "title": "Legacy Version", "body": "AML legacy", "tags": [],
        })

        fake_db = {"career_stories": career_coll, "user_context": legacy_coll}
        monkeypatch.setattr("linkright.db.mongo.get_db", lambda: fake_db)
        monkeypatch.setattr("linkright.db.mongo.ping", lambda: True)
        monkeypatch.setattr(sr, "oracle_embed", lambda *a, **kw: [])

        results = sr.retrieve_stars("AML")
        # Only career version surfaces — dedup by _id, primary wins
        assert len(results) == 1
        assert results[0]["title"] == "Career Version"

    def test_merge_respects_k_cap(self, monkeypatch):
        """If primary returns 3 hits and legacy returns 5 (matching), k=4
        means we get 3 primary + 1 legacy = 4 total."""
        from linkright.interview import star_retriever as sr

        career_coll = FakeCollection()
        for i in range(3):
            career_coll.insert_one({
                "user_id": "local", "title": f"Career Story {i}",
                "action": f"AML action {i}", "result": "x", "tags": [],
            })
        legacy_coll = FakeCollection()
        for i in range(5):
            legacy_coll.insert_one({
                "user_id": "local", "kind": "story",
                "title": f"Legacy Story {i}", "body": f"AML legacy {i}", "tags": [],
            })

        fake_db = {"career_stories": career_coll, "user_context": legacy_coll}
        monkeypatch.setattr("linkright.db.mongo.get_db", lambda: fake_db)
        monkeypatch.setattr("linkright.db.mongo.ping", lambda: True)
        monkeypatch.setattr(sr, "oracle_embed", lambda *a, **kw: [])

        results = sr.retrieve_stars("AML", k=4)
        assert len(results) == 4
        career_count = sum(1 for r in results if r["title"].startswith("Career"))
        assert career_count == 3  # all career stories included
        legacy_count = sum(1 for r in results if r["title"].startswith("Legacy"))
        assert legacy_count == 1  # one legacy fills the remaining slot

    def test_returns_empty_when_mongo_unreachable(self, monkeypatch):
        from linkright.interview import star_retriever as sr
        monkeypatch.setattr("linkright.db.mongo.ping", lambda: False)
        assert sr.retrieve_stars("anything") == []
