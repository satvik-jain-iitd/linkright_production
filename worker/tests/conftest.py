"""Shared pytest fixtures for worker tests.

Provides:
- FakeLLMProvider  — canned LLMProvider implementation
- FakeTable        — dict-backed Supabase table stub
- FakeSupabaseClient — table-routing stub
- fake_llm         — fixture returning FakeLLMProvider
- fake_sb          — fixture returning FakeSupabaseClient
- pipeline_ctx     — full PipelineContext with Satvik career fixture
- minimal_ctx      — PipelineContext with minimal career text
"""

from __future__ import annotations

import os
import sys
import pytest

# Make `worker/` importable as a root so we can do `from app.llm.base import ...`
# (worker has no pyproject.toml / setup.py, so it is not an installed package)
_WORKER_ROOT = os.path.join(os.path.dirname(__file__), "..")
if _WORKER_ROOT not in sys.path:
    sys.path.insert(0, os.path.abspath(_WORKER_ROOT))

from app.llm.base import LLMProvider, LLMResponse  # noqa: E402
from app.context import PipelineContext  # noqa: E402


# ---------------------------------------------------------------------------
# FakeLLMProvider
# ---------------------------------------------------------------------------

class FakeLLMProvider(LLMProvider):
    """LLMProvider stub that returns a configurable canned response."""

    def __init__(
        self,
        response_json: str = '{"ok": true}',
        model_id: str = "fake-model-v1",
        api_key: str = "fake-api-key",
        input_tokens: int = 10,
        output_tokens: int = 20,
    ) -> None:
        super().__init__(api_key=api_key, model_id=model_id)
        self._response_json = response_json
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        # Track calls for assertion in tests
        self.calls: list[dict] = []

    async def complete(
        self, system: str, user: str, temperature: float = 0.3
    ) -> LLMResponse:
        self.calls.append({"system": system, "user": user, "temperature": temperature})
        return LLMResponse(
            text=self._response_json,
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            model=self.model_id,
        )

    async def validate_key(self) -> bool:
        return True


# ---------------------------------------------------------------------------
# FakeTable / FakeSupabaseClient
# ---------------------------------------------------------------------------

class _QueryChain:
    """Chainable query builder; .execute() returns a result with .data."""

    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self._filters: list[tuple] = []
        self._insert_payload: list[dict] | None = None
        self._update_payload: dict | None = None

    # --- builder methods (return self for chaining) ---

    def select(self, *_args, **_kwargs) -> "_QueryChain":
        return self

    def insert(self, payload: dict | list[dict]) -> "_QueryChain":
        if isinstance(payload, dict):
            payload = [payload]
        self._insert_payload = payload
        return self

    def update(self, payload: dict) -> "_QueryChain":
        self._update_payload = payload
        return self

    def eq(self, column: str, value) -> "_QueryChain":
        self._filters.append((column, value))
        return self

    def order(self, *_args, **_kwargs) -> "_QueryChain":
        return self

    def limit(self, *_args, **_kwargs) -> "_QueryChain":
        return self

    # --- terminal ---

    def execute(self):
        """Apply pending mutations and return a result object."""
        if self._insert_payload is not None:
            self._rows.extend(self._insert_payload)
            return _Result(list(self._insert_payload))

        if self._update_payload is not None:
            matched = self._rows
            for col, val in self._filters:
                matched = [r for r in matched if r.get(col) == val]
            for row in matched:
                row.update(self._update_payload)
            return _Result(matched)

        # Plain select with optional eq filters
        matched = self._rows
        for col, val in self._filters:
            matched = [r for r in matched if r.get(col) == val]
        return _Result(matched)


class _Result:
    """Minimal Supabase result envelope with a .data attribute."""

    def __init__(self, data: list[dict]) -> None:
        self.data = data


class FakeTable:
    """Dict-backed table stub; all rows stored in self.rows."""

    def __init__(self, initial_rows: list[dict] | None = None) -> None:
        self.rows: list[dict] = list(initial_rows or [])

    def select(self, *args, **kwargs) -> _QueryChain:
        return _QueryChain(self.rows).select(*args, **kwargs)

    def insert(self, payload) -> _QueryChain:
        return _QueryChain(self.rows).insert(payload)

    def update(self, payload) -> _QueryChain:
        return _QueryChain(self.rows).update(payload)

    def eq(self, column: str, value) -> _QueryChain:
        # Top-level .eq() — returns chain scoped to all rows
        return _QueryChain(self.rows).eq(column, value)


class FakeSupabaseClient:
    """Supabase client stub; routes .table(name) to per-table FakeTable."""

    def __init__(self) -> None:
        self._tables: dict[str, FakeTable] = {}

    def table(self, name: str) -> FakeTable:
        if name not in self._tables:
            self._tables[name] = FakeTable()
        return self._tables[name]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_llm(request):
    """Return a FakeLLMProvider.

    Supports indirect parametrize:
        @pytest.mark.parametrize("fake_llm", ['{"nuggets":[]}'], indirect=True)
    """
    if hasattr(request, "param"):
        return FakeLLMProvider(response_json=request.param)
    return FakeLLMProvider()


@pytest.fixture
def fake_sb():
    """Return a fresh FakeSupabaseClient per test."""
    return FakeSupabaseClient()


def _load_fixture(filename: str) -> str:
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    with open(os.path.join(fixtures_dir, filename), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture
def pipeline_ctx(fake_sb):
    """PipelineContext populated with Satvik career fixture data."""
    career_text = _load_fixture("career_satvik.txt")
    return PipelineContext(
        job_id="test-job-satvik-001",
        user_id="test-user-satvik-001",
        jd_text=(
            "Senior Product Manager — FinTech. Drive product strategy for "
            "credit risk decisioning platform. 5+ years PM experience required. "
            "Strong data / ML background preferred."
        ),
        career_text=career_text,
        model_provider="fake",
        model_id="fake-model-v1",
        api_key="fake-api-key",
        template_id="cv-a4-standard",
    )


@pytest.fixture
def minimal_ctx(fake_sb):
    """PipelineContext with minimal one-line career text."""
    career_text = _load_fixture("career_minimal.txt")
    return PipelineContext(
        job_id="test-job-minimal-001",
        user_id="test-user-minimal-001",
        jd_text="Software Engineer role at a startup.",
        career_text=career_text,
        model_provider="fake",
        model_id="fake-model-v1",
        api_key="fake-api-key",
        template_id="cv-a4-standard",
    )
