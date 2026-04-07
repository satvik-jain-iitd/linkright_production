"""One-time script: extract + embed career nuggets for a user.

Usage:
  cd worker

  # From career text already in Supabase career_chunks:
  SUPABASE_URL=... SUPABASE_SERVICE_KEY=... GROQ_API_KEY=... JINA_API_KEY=... \
    python3 -m scripts.ingest_nuggets --user-id <uuid>

  # From a local career text file (faster for testing):
  SUPABASE_URL=... SUPABASE_SERVICE_KEY=... GROQ_API_KEY=... JINA_API_KEY=... \
    python3 -m scripts.ingest_nuggets --user-id <uuid> --career-file tests/fixtures/career_satvik.txt

Required env vars:
  SUPABASE_URL          — Supabase project URL
  SUPABASE_SERVICE_KEY  — Service role key (bypasses RLS)
  GROQ_API_KEY          — Groq API key for LLaMA extraction (free tier is fine)
  JINA_API_KEY          — Jina AI key for embeddings (free tier: 1M tokens/month)

Cost & time (Groq free tier):
  Groq  llama-3.3-70b : ~$0.00  (~1.5 min, free tier)
  Jina  jina-v3       : ~$0.00  (~1.5 min, free tier)
  Total                : ~$0.00  (~3-5 min total)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
import uuid

# Must be set BEFORE importing app.config so the flag is True at module load
os.environ["USE_NUGGETS"] = "true"

# Configure logging so orchestrator progress is visible
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

_WORKER_ROOT = os.path.join(os.path.dirname(__file__), "..")
if os.path.abspath(_WORKER_ROOT) not in sys.path:
    sys.path.insert(0, os.path.abspath(_WORKER_ROOT))

from supabase import create_client  # noqa: E402
from app.pipeline.orchestrator import phase_0_nuggets  # noqa: E402
from app.context import PipelineContext  # noqa: E402

_ESTIMATE = """
┌──────────────────────────────────────────────────────────┐
│  Cost & Time Estimate (Groq free tier)                   │
│  Groq  llama-3.3-70b-versatile : $0.00   (~1.5 min)    │
│  Jina  jina-embeddings-v3      : $0.00   (~1.5 min)    │
│  Total                          : $0.00   (~3-5 min)    │
│                                                          │
│  Groq free tier: 6k TPM / 14.4k TPD — run uses ~9.7k   │
│  Jina free tier: 1M tokens/month — run uses ~400        │
└──────────────────────────────────────────────────────────┘
"""


def _check_env() -> None:
    missing = [v for v in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "GROQ_API_KEY", "JINA_API_KEY") if not os.environ.get(v)]
    if missing:
        print(f"[error] Missing env vars: {', '.join(missing)}")
        sys.exit(1)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed career_nuggets for a user.")
    parser.add_argument("--user-id", required=True, help="Supabase auth user UUID")
    parser.add_argument(
        "--career-file",
        default=None,
        help="Path to a .txt career file. If omitted, fetches from career_chunks in Supabase.",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip the confirmation prompt (for non-interactive / scripted use).",
    )
    parser.add_argument(
        "--embed-only",
        action="store_true",
        help="Skip extraction — only embed existing career_nuggets rows that lack embeddings.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing nuggets before extracting. WARNING: destroys existing data. Use only when re-ingesting from scratch.",
    )
    args = parser.parse_args()

    # Embed-only mode doesn't need GROQ_API_KEY
    if not args.embed_only:
        _check_env()
    else:
        missing = [v for v in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "JINA_API_KEY") if not os.environ.get(v)]
        if missing:
            print(f"[error] Missing env vars: {', '.join(missing)}")
            sys.exit(1)

    sb_url = os.environ["SUPABASE_URL"]
    sb_key = os.environ["SUPABASE_SERVICE_KEY"]
    sb = create_client(sb_url, sb_key)

    # ── embed-only shortcut ───────────────────────────────────────────────
    if args.embed_only:
        from app.tools.nugget_embedder import embed_nuggets
        from app.tools.nugget_extractor import Nugget

        print(f"[embed-only] Fetching nuggets without embeddings for user {args.user_id} …")
        rows = (
            sb.table("career_nuggets")
            .select("id, nugget_index, answer")
            .eq("user_id", args.user_id)
            .is_("embedding", "null")
            .execute()
            .data or []
        )
        if not rows:
            print("[embed-only] Nothing to embed — all nuggets already have embeddings.")
            sys.exit(0)

        print(f"[embed-only] {len(rows)} nuggets need embedding …")
        nuggets = []
        for r in rows:
            n = Nugget.__new__(Nugget)
            object.__setattr__(n, "id", r["id"])
            object.__setattr__(n, "nugget_index", r["nugget_index"])
            object.__setattr__(n, "answer", r.get("answer") or "")
            object.__setattr__(n, "nugget_text", "")
            object.__setattr__(n, "question", "")
            object.__setattr__(n, "alt_questions", [])
            object.__setattr__(n, "primary_layer", "A")
            object.__setattr__(n, "section_type", None)
            object.__setattr__(n, "section_subtype", None)
            object.__setattr__(n, "resume_section_target", None)
            object.__setattr__(n, "resume_relevance", None)
            object.__setattr__(n, "life_domain", None)
            object.__setattr__(n, "life_l2", None)
            object.__setattr__(n, "importance", None)
            object.__setattr__(n, "temporality", None)
            object.__setattr__(n, "duration", None)
            object.__setattr__(n, "event_date", None)
            object.__setattr__(n, "role", None)
            object.__setattr__(n, "company", None)
            object.__setattr__(n, "people", [])
            object.__setattr__(n, "leadership_signal", False)
            object.__setattr__(n, "factuality", None)
            object.__setattr__(n, "tags", [])

            nuggets.append(n)

        t0 = time.time()
        asyncio.run(embed_nuggets(nuggets, os.environ["JINA_API_KEY"], sb, args.user_id))
        print(f"\n[done] Embedded {len(nuggets)} nuggets in {time.time() - t0:.0f}s")
        sys.exit(0)

    # ── 1. Get career text ────────────────────────────────────────────────
    if args.career_file:
        with open(args.career_file, encoding="utf-8") as f:
            career_text = f.read()
        print(f"[career] Loaded from file ({len(career_text)} chars): {args.career_file}")
    else:
        rows = (
            sb.table("career_chunks")
            .select("chunk_text, chunk_index")
            .eq("user_id", args.user_id)
            .order("chunk_index")
            .execute()
            .data or []
        )
        if not rows:
            print(
                "[error] No career_chunks found for this user_id.\n"
                "        Upload your career profile in the app first, then re-run."
            )
            sys.exit(1)
        career_text = "\n\n".join(r["chunk_text"] for r in rows)
        print(f"[career] Fetched {len(rows)} chunks from Supabase → {len(career_text)} chars")

    # ── 2. Show estimate + confirm ────────────────────────────────────────
    print(_ESTIMATE)
    if not args.yes:
        try:
            confirm = input("Proceed? [y/N] ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)
        if confirm != "y":
            print("Aborted.")
            sys.exit(0)

    # ── 3. Build context ──────────────────────────────────────────────────
    ctx = PipelineContext(
        job_id=str(uuid.uuid4()),  # valid UUID required by checkpoint saves
        user_id=args.user_id,
        career_text=career_text,
        jd_text="",
        model_provider="groq",
        model_id="llama-3.3-70b-versatile",
        api_key=None,
        template_id="cv-a4-standard",
    )

    # ── 4. Run phase 0 ────────────────────────────────────────────────────
    t0 = time.time()
    print("[phase_0] Starting nugget extraction + embedding …")
    print("          (30s delays between Groq batches — this is normal)")
    await phase_0_nuggets(ctx, sb, groq_api_key=os.environ.get("GROQ_API_KEY"), force=True, force_delete=args.force)
    elapsed = time.time() - t0

    # ── 5. Summary ────────────────────────────────────────────────────────
    nuggets = ctx._nuggets or []
    print(f"\n[done] {len(nuggets)} nuggets extracted + embedded in {elapsed:.0f}s")
    print(f"\nVerify in Supabase SQL editor:")
    print(f"  SELECT count(*), importance, section_type")
    print(f"  FROM career_nuggets")
    print(f"  WHERE user_id = '{args.user_id}'")
    print(f"  GROUP BY importance, section_type ORDER BY importance;")
    print(f"\n  -- Also check no failed embeddings:")
    print(f"  SELECT count(*) FROM career_nuggets")
    print(f"  WHERE user_id = '{args.user_id}'")
    print(f"  AND tags @> ARRAY['needs_embedding'];  -- should be 0")


if __name__ == "__main__":
    asyncio.run(main())
