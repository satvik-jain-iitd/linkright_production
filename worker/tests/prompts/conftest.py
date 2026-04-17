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
from app.llm.oracle import OracleProvider  # noqa: E402


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
    """Phase 4a LLM. Groq 70B — matches current production fallback path
    (Gemini has been rate-limited; Groq 70B is the effective primary)."""
    api_key = os.environ.get("PLATFORM_GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    if not api_key:
        pytest.skip("PLATFORM_GROQ_API_KEY missing in .env.local")
    return get_provider("groq", api_key, "llama-3.3-70b-versatile")


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
