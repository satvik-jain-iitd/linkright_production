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
DEFAULT_MODEL_ID = os.getenv("DEFAULT_MODEL_ID", "llama-3.1-8b-instant")
# Render env may use PLATFORM_GROQ_API_KEY (matches Vercel convention) — check both
DEFAULT_API_KEY = os.getenv("PLATFORM_GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")

# Oracle ARM — local LLM endpoint for Phase 5 width rewriting
# Phase 5 (bullet width tweaking) + Phase 3.5a (summary width) use local llama3.2:1b
# To disable local LLM and fall back to Groq: unset ORACLE_BACKEND_URL
ORACLE_BACKEND_URL = os.getenv("ORACLE_BACKEND_URL", "")
ORACLE_BACKEND_SECRET = os.getenv("ORACLE_BACKEND_SECRET", "")
