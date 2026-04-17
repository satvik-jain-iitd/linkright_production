# Prompt & Retrieval Diagnostic Harness

Live-API test harness for debugging resume-generation quality issues.
Isolates each pipeline stage so we can attribute output problems to the
right cause: retrieval, prompt design, or model capability.

## Modules (run in pipeline order)

| # | File | What it tests |
|---|---|---|
| 1 | `test_1_retrieval_quality.py` | `hybrid_retrieve()` — does it return the right nuggets? |
| 2 | `test_2_phase4a_verbose.py` | Phase 4a prompt — current vs proposed (grounding + keyword weight + Google Bock few-shot) |
| 3 | `test_3_phase4c_condense.py` | Phase 4c prompt — current vs proposed (anti-circular + variety rules) |
| 4 | `test_4_single_bullet_compress.py` | New click-to-compress prompt — Oracle 1B vs Groq 70B |

Modules 1→2→3 share data through session-scoped pytest fixtures
(`retrieval_cache`, `phase4a_output_cache`). Module 4 is independent.

## First-time setup

1. **Env file:** copy from Vercel pull into `.env.local` (gitignored):
   ```
   cd repo/website && vercel env pull /tmp/vercel.env --yes
   cp /tmp/vercel.env worker/tests/prompts/.env.local
   # Add worker-convention alias:
   echo 'SUPABASE_SERVICE_KEY="<service role key>"' >> worker/tests/prompts/.env.local
   echo 'SUPABASE_URL="https://<project>.supabase.co"' >> worker/tests/prompts/.env.local
   ```
2. **Career text fixture:** `fixtures/satvik_career_text.txt` (gitignored) —
   reconstructed from Supabase `user_work_history` + `career_nuggets` if missing
3. **Target JDs:** `fixtures/satvik_target_jds.json` — curated 3 JDs, committed

## Run

```bash
cd repo/worker

# All modules in order (M2 depends on M1's cache, M3 on M2's)
pytest tests/prompts/ -v -s

# Individual modules
pytest tests/prompts/test_1_retrieval_quality.py -v -s
pytest tests/prompts/test_4_single_bullet_compress.py -v -s  # independent
```

Reports land at `reports/{module}_{YYYYMMDD_HHMMSS}.md`. Gitignored.

## Key files

- `conftest.py` — session fixtures: `live_sb` (Supabase), `llm_primary` (Groq 70B),
  `llm_condenser` (Oracle 1B), `report_writer`, autoused read-only guard on the DB
- `fixtures/prompt_variants/` — text files for A/B: `*_current.txt` mirrors the
  production prompt, `*_proposed.txt` is the candidate rewrite
- `.env.local` — gitignored credentials
- `reports/` — gitignored output markdown

## Safety

- Autoused fixture `read_only_sb_guard` blocks `.insert/.update/.delete/.upsert`
  on all Supabase tables — harness cannot mutate production data
- No pipeline orchestrator is invoked; tests call `hybrid_retrieve` and
  `LLMProvider.complete` directly
- Live API calls: Supabase (read-only), Jina AI (embed queries), Groq (LLM),
  Oracle (LLM) — all metered on existing keys

## How to iterate a prompt

1. Edit `fixtures/prompt_variants/{phase}_proposed.txt`
2. Re-run that module
3. Diff the new report against the last one
4. When the proposed variant clearly wins: open a separate PR to promote it
   into `app/pipeline/prompts.py`

The harness **never** modifies production prompts — it only reads variants from
disk and runs them against live models.
