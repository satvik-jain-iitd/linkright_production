import os

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

# Optional: shared secret so only our Vercel API can trigger jobs
WORKER_SECRET = os.environ.get("WORKER_SECRET", "")

# Render assigns PORT automatically
PORT = int(os.environ.get("PORT", "8000"))

# Feature flags
USE_NUGGETS = os.getenv("USE_NUGGETS", "false").lower() == "true"

# Default LLM configuration (BYOK fallback — server-side key for zero-config)
DEFAULT_MODEL_PROVIDER = os.getenv("DEFAULT_MODEL_PROVIDER", "groq")
DEFAULT_MODEL_ID = os.getenv("DEFAULT_MODEL_ID", "llama-3.3-70b-versatile")
# Render env may use PLATFORM_GROQ_API_KEY (matches Vercel convention) — check both
DEFAULT_API_KEY = os.getenv("PLATFORM_GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")

# Gemini Flash — used for heavy reasoning phases (Phase 1+2 JD parse, Phase 4a bullets).
# Falls back through rotation keys (_1/_2/_3) when the singular GEMINI_API_KEY is
# absent, so setting only the numbered rotation keys on Render still works.
GEMINI_API_KEY = (
    os.getenv("GEMINI_API_KEY", "")
    or os.getenv("GEMINI_API_KEY_1", "")
    or os.getenv("GEMINI_API_KEY_2", "")
    or os.getenv("GEMINI_API_KEY_3", "")
)
# All Gemini keys available for rotation — each free-tier key has its own RPM/RPD
# quota, so round-robin lets us stack 3x capacity (or more) without paying.
GEMINI_API_KEYS: list[str] = [
    k for k in (
        os.getenv("GEMINI_API_KEY", ""),
        os.getenv("GEMINI_API_KEY_1", ""),
        os.getenv("GEMINI_API_KEY_2", ""),
        os.getenv("GEMINI_API_KEY_3", ""),
    ) if k
]
GEMINI_MODEL_ID = os.getenv("GEMINI_MODEL_ID", "gemini-2.0-flash")

# Oracle ARM — local LLM endpoint for Phase 5 width rewriting
# Phase 5 (bullet width tweaking) + Phase 3.5a (summary width) use local gemma3:1b
# To disable local LLM and fall back to Groq: unset ORACLE_BACKEND_URL
ORACLE_BACKEND_URL = os.getenv("ORACLE_BACKEND_URL", "")
ORACLE_BACKEND_SECRET = os.getenv("ORACLE_BACKEND_SECRET", "")

# ── Oracle Postgres — job-related data (companies, slug cache, enriched JDs) ──
# Constitutional rule: job data goes to Oracle PG; user PII stays on Supabase.
# See: feedback_split_db_architecture_locked.md
#
# Format: postgres://linkright_app:<password>@oracle-pg.linkright.in:5432/linkright_jobs
# SSL is REQUIRED — the asyncpg pool in app/oracle/pg.py enforces ssl="require".
# Leave unset while Oracle Postgres is being provisioned. All Oracle-PG-backed
# code paths check ORACLE_PG_ENABLED before connecting and raise a clear error.
ORACLE_PG_URL = os.environ.get("ORACLE_PG_URL")  # None = not yet provisioned
ORACLE_PG_ENABLED = bool(ORACLE_PG_URL and ORACLE_PG_URL.strip())
