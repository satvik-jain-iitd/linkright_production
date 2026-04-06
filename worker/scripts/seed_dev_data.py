"""Seed DEV_USER data into Supabase for local E2E testing.

Uses service role key (bypasses RLS). Requires env vars:
  SUPABASE_URL, SUPABASE_SERVICE_KEY, GROQ_API_KEY

Usage:
  cd Resume/worker
  GROQ_API_KEY=<key> python -m scripts.seed_dev_data
"""

import math
import os
import sys
from pathlib import Path

DEV_USER_ID = "c2305b3f-f934-4955-8c71-1875d7e45c64"
CAREER_PROFILE_PATH = Path(__file__).resolve().parent.parent.parent.parent / "linkright" / "satvik_jain_career_profile.md"


def chunk_text(text: str, max_chunk: int = 1000, hard_limit: int = 1500) -> list[str]:
    """Chunk text by paragraphs, merging small ones up to max_chunk chars."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""

    for para in paragraphs:
        if len(para) > hard_limit:
            # Split oversized paragraph by single newlines
            if current:
                chunks.append(current)
                current = ""
            lines = para.split("\n")
            sub = ""
            for line in lines:
                if len(sub) + len(line) + 1 > hard_limit:
                    if sub:
                        chunks.append(sub)
                    sub = line
                else:
                    sub = f"{sub}\n{line}" if sub else line
            if sub:
                chunks.append(sub)
        elif len(current) + len(para) + 2 > max_chunk:
            if current:
                chunks.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para

    if current:
        chunks.append(current)

    return chunks


def seed_user_settings(sb):
    """Upsert user_settings row for DEV_USER."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        print("WARNING: GROQ_API_KEY not set — user_settings.api_key will be empty")

    try:
        sb.table("user_settings").upsert({
            "user_id": DEV_USER_ID,
            "model_provider": "groq",
            "model_id": "llama-3.3-70b-versatile",
            "api_key": api_key,
            "updated_at": "now()",
        }).execute()
        print(f"  user_settings: upserted (provider=groq, model=llama-3.3-70b-versatile, api_key={'set' if api_key else 'empty'})")
    except Exception as e:
        if "relation" in str(e).lower() and "does not exist" in str(e).lower():
            print(f"  ERROR: user_settings table does not exist. Run sql/002_user_settings.sql first.")
        else:
            print(f"  ERROR seeding user_settings: {e}")
        return False
    return True


def seed_career_chunks(sb, career_text: str):
    """Delete existing chunks and insert new ones for DEV_USER."""
    try:
        # Delete existing
        sb.table("career_chunks").delete().eq("user_id", DEV_USER_ID).execute()

        # Chunk and insert
        chunks = chunk_text(career_text)
        rows = []
        for i, chunk in enumerate(chunks):
            rows.append({
                "user_id": DEV_USER_ID,
                "chunk_index": i,
                "chunk_text": chunk,
                "chunk_tokens": math.ceil(len(chunk) / 4),
            })

        # Insert in batches of 50
        for batch_start in range(0, len(rows), 50):
            batch = rows[batch_start:batch_start + 50]
            sb.table("career_chunks").insert(batch).execute()

        total_chars = sum(len(c) for c in chunks)
        print(f"  career_chunks: {len(chunks)} chunks, {total_chars:,} chars total")
    except Exception as e:
        print(f"  ERROR seeding career_chunks: {e}")
        return False
    return True


def main():
    # Validate env vars
    for var in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
        if var not in os.environ:
            print(f"ERROR: {var} not set")
            sys.exit(1)

    from app.db import create_supabase
    sb = create_supabase()

    # Read career profile
    if not CAREER_PROFILE_PATH.exists():
        print(f"ERROR: Career profile not found at {CAREER_PROFILE_PATH}")
        sys.exit(1)

    career_text = CAREER_PROFILE_PATH.read_text(encoding="utf-8")
    print(f"Seeding DEV_USER ({DEV_USER_ID[:8]}...) data:")
    print(f"  Career profile: {len(career_text):,} chars from {CAREER_PROFILE_PATH.name}")

    ok1 = seed_user_settings(sb)
    ok2 = seed_career_chunks(sb, career_text)

    if ok1 and ok2:
        print("\nSeed complete. Ready for E2E testing.")
    else:
        print("\nSeed had errors — check messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
