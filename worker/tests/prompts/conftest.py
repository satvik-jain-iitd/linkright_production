"""Fixtures for prompt/retrieval diagnostic harness.

Loads live API credentials from `.env.local`, provides LLM providers matching
current production fallback behavior (Groq 70B primary, Oracle 1B condenser),
and a non-destructive guard on the Supabase client.

Reports land in `reports/` under a timestamped filename per module.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import pytest
from dotenv import load_dotenv

# Make `worker/` importable (matches pattern in parent conftest.py)
_HARNESS_DIR = Path(__file__).parent
_WORKER_ROOT = _HARNESS_DIR.parent.parent
if str(_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKER_ROOT))

# Load .env.local BEFORE importing worker modules (which read env vars at import)
_ENV_PATH = _HARNESS_DIR / ".env.local"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH, override=True)

# Also populate the NEXT_PUBLIC_SUPABASE_URL → SUPABASE_URL alias if only the
# NEXT_PUBLIC_ form was loaded
if not os.environ.get("SUPABASE_URL") and os.environ.get("NEXT_PUBLIC_SUPABASE_URL"):
    os.environ["SUPABASE_URL"] = os.environ["NEXT_PUBLIC_SUPABASE_URL"]

from supabase import create_client  # noqa: E402

from app.llm import get_provider  # noqa: E402
from app.llm.base import LLMProvider, LLMResponse  # noqa: E402
from app.llm.gemini import GeminiProvider  # noqa: E402
from app.llm.oracle import OracleProvider  # noqa: E402


class RotatingGeminiProvider(LLMProvider):
    """Wraps N Gemini keys, rotates on 429. Effective rate = N × 15 RPM."""

    def __init__(self, api_keys: list[str], model_id: str = "gemini-2.0-flash"):
        super().__init__(api_key=api_keys[0], model_id=model_id)
        self._providers = [GeminiProvider(api_key=k, model_id=model_id) for k in api_keys]
        self._idx = 0

    async def complete(self, system: str, user: str, temperature: float = 0.3) -> LLMResponse:
        import httpx
        errors = []
        # Try each key once; if all 429, fall through and let exception propagate
        for _ in range(len(self._providers)):
            provider = self._providers[self._idx]
            try:
                return await provider.complete(system, user, temperature)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    errors.append(f"key[{self._idx}]: 429")
                    self._idx = (self._idx + 1) % len(self._providers)
                    continue
                raise
            except RuntimeError as exc:
                # GeminiProvider raises this after internal retry exhaustion
                if "rate limit" in str(exc).lower():
                    errors.append(f"key[{self._idx}]: exhausted")
                    self._idx = (self._idx + 1) % len(self._providers)
                    continue
                raise
        raise RuntimeError(f"All {len(self._providers)} Gemini keys rate-limited: {errors}")

    async def validate_key(self) -> bool:
        for p in self._providers:
            if await p.validate_key():
                return True
        return False


# ---------------------------------------------------------------------------
# Core fixtures — data identity, paths
# ---------------------------------------------------------------------------

SATVIK_USER_ID = "7cc942ba-5ca8-4a43-83d7-14ebd968d46a"
FIXTURES_DIR = _HARNESS_DIR / "fixtures"
REPORTS_DIR = _HARNESS_DIR / "reports"
VARIANTS_DIR = FIXTURES_DIR / "prompt_variants"


@pytest.fixture(scope="session")
def satvik_user_id() -> str:
    return SATVIK_USER_ID


@pytest.fixture(scope="session")
def target_jds() -> list[dict]:
    with open(FIXTURES_DIR / "satvik_target_jds.json") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def career_text_live() -> str:
    """Satvik's career text. Prefer harness-local copy, fall back to /tmp."""
    local = FIXTURES_DIR / "satvik_career_text.txt"
    if local.exists():
        return local.read_text()
    tmp = Path("/tmp/career_text_live.txt")
    if tmp.exists():
        return tmp.read_text()
    pytest.skip("career_text not found; copy to fixtures/satvik_career_text.txt")
    return ""  # unreachable, silences type checker


# ---------------------------------------------------------------------------
# Supabase — live, read-only
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def live_sb():
    """Live Supabase client (service-role). Session-scoped to reuse conn."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get(
        "SUPABASE_SERVICE_ROLE_KEY"
    )
    if not url or not key:
        pytest.skip("SUPABASE_URL / SUPABASE_SERVICE_KEY missing in .env.local")
    return create_client(url, key)


@pytest.fixture(autouse=True)
def read_only_sb_guard(live_sb, monkeypatch):
    """Block any mutating Supabase call to prevent accidental prod writes."""
    original_table = live_sb.table

    def guarded_table(name: str):
        tbl = original_table(name)
        for forbidden in ("insert", "update", "delete", "upsert"):
            def raise_readonly(*args, _op=forbidden, **kwargs):
                raise RuntimeError(
                    f"Test attempted Supabase .{_op}() on '{name}' — harness is read-only"
                )
            monkeypatch.setattr(tbl, forbidden, raise_readonly, raising=False)
        return tbl

    monkeypatch.setattr(live_sb, "table", guarded_table)
    yield


# ---------------------------------------------------------------------------
# LLM providers (live, real API calls)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def llm_primary():
    """Phase 4a LLM. Prefer Gemini (production primary) with key rotation;
    fall back to Groq 70B if no Gemini keys present.

    Gemini has stricter free-tier RPM (15/key) than Groq (30 RPM) but produces
    better instruction-following. 3 rotated keys → effective 45 RPM.
    """
    keys = [
        os.environ[k] for k in ("GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3")
        if os.environ.get(k)
    ]
    if not keys and os.environ.get("GEMINI_API_KEY"):
        keys = [os.environ["GEMINI_API_KEY"]]
    if keys:
        model = os.environ.get("GEMINI_MODEL_ID", "gemini-2.0-flash")
        return RotatingGeminiProvider(api_keys=keys, model_id=model)
    groq_key = os.environ.get("PLATFORM_GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    if groq_key:
        return get_provider("groq", groq_key, "llama-3.3-70b-versatile")
    pytest.skip("Neither GEMINI_API_KEY nor PLATFORM_GROQ_API_KEY found in .env.local")


@pytest.fixture(scope="session")
def llm_condenser(llm_primary):
    """Phase 4c LLM. Oracle 1B primary, Groq 70B fallback if Oracle missing."""
    base = os.environ.get("ORACLE_BACKEND_URL")
    secret = os.environ.get("ORACLE_BACKEND_SECRET")
    if not base or not secret:
        return llm_primary  # graceful fallback
    return OracleProvider(base_url=base, secret=secret, endpoint="rewrite")


@pytest.fixture(scope="session")
def llm_compressor(llm_primary):
    """M4 click-to-compress: pair of (oracle_1b, groq_70b) for A/B comparison."""
    base = os.environ.get("ORACLE_BACKEND_URL")
    secret = os.environ.get("ORACLE_BACKEND_SECRET")
    oracle = None
    if base and secret:
        oracle = OracleProvider(base_url=base, secret=secret, endpoint="rewrite")
    return {"oracle": oracle, "groq": llm_primary}


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

@pytest.fixture
def report_writer() -> Callable[[str], Path]:
    """Returns a function(name) -> Path that creates a timestamped report file.

    Usage:
        def test_x(report_writer):
            path = report_writer("retrieval_quality")
            with path.open("a") as f:
                f.write("# Title\\n")
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def _writer(name: str) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = REPORTS_DIR / f"{name}_{ts}.md"
        path.touch()
        return path

    return _writer


# ---------------------------------------------------------------------------
# Cross-module caches (populated in M1, consumed in M2; M2 → M3)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def retrieval_cache() -> dict:
    """Populated by M1 with (jd_id, company) -> list[NuggetResult]."""
    return {}


@pytest.fixture(scope="session")
def phase4a_output_cache() -> dict:
    """Populated by M2 with (jd_id, company, variant) -> list[paragraph dict]."""
    return {}


# ---------------------------------------------------------------------------
# Prompt variant loader
# ---------------------------------------------------------------------------

@pytest.fixture
def load_variant() -> Callable[[str], str]:
    """load_variant('phase4a_proposed') → text content of that variant file.

    Variant files live at fixtures/prompt_variants/{name}.txt. Missing file
    returns '' so callers can fall through to in-code prompt.
    """
    def _load(name: str) -> str:
        path = VARIANTS_DIR / f"{name}.txt"
        return path.read_text() if path.exists() else ""

    return _load
