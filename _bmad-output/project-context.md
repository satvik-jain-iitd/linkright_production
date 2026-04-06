# Project Context — LinkRight Resume Engine

## Overview

LinkRight is a resume optimization platform with two codebases:
- **CLI** (`linkright/`) — Python, Anthropic API, 7-step pipeline, comprehensive quality gates
- **Web App** (`Resume/`) — Next.js 16.2 frontend + FastAPI worker, 8-phase async pipeline, deployed at sync.linkride.in

## Web App Architecture

### Frontend (Resume/website/)
- **Stack**: Next.js 16.2, React 19, TypeScript, Supabase Auth + Realtime
- **Pages**: `/auth`, `/dashboard`, `/resume/new` (5-step wizard), `/resume/[id]` (view)
- **Wizard Steps**: JD Input → Career Profile → Configure (model + API key + colors) → Enrich (Q&A) → Generate (realtime progress) → Review (iframe + PDF download)
- **State**: Supabase realtime subscription on `resume_jobs` table for progress updates

### Backend (Resume/worker/)
- **Stack**: FastAPI, Python 3.9+, httpx, Pydantic, BeautifulSoup4
- **Concurrency**: Max 3 simultaneous pipelines (semaphore), 5 jobs/hr per user
- **LLM Providers**: OpenRouter (200+ models), Groq (fast inference), Gemini
- **Vector Search**: QMD daemon (BM25 + vector + reranking) with Supabase FTS fallback

### 8-Phase Pipeline (orchestrator.py, 1578 lines)

| Phase | What | LLM? | Quality Gate |
|-------|------|------|-------------|
| 1+2 | Parse JD + Career + Strategy | Yes (temp 0.3) | JSON parse only |
| 2.5 | Vector retrieval (QMD/FTS) | No | None — empty chunks silent |
| 3 | Page fit planning | No | Warns if overflow |
| 3.5 | Stencil draft HTML | No | None |
| 4A | Verbose bullets per company | Yes (temp 0.4) | None — no length/verb check |
| 4B | Rank by BRS | No | 5-factor scoring |
| 4C | Condense to bullets | Yes (temp 0.2) | None — no width check until Phase 5 |
| 5 | Width optimization | Yes (temp 0.2) | Local re-measurement, 2 passes max |
| 6 | BRS re-scoring | No | Logged for analytics |
| 7 | Validation | No | Partial — contrast (BROKEN), page fit, keywords |
| 8 | Final assembly | No | None |

### 8 Shared Tools (worker/app/tools/)
1. `parse_template.py` — CSS extraction, line budget computation
2. `measure_width.py` — Roboto font-metric width calculation
3. `validate_contrast.py` — WCAG 2.0 AA contrast check
4. `validate_page_fit.py` — A4 vertical layout estimation
5. `suggest_synonyms.py` — Width-aware word substitution
6. `track_verbs.py` — Action verb dedup registry
7. `score_bullets.py` — BRS 5-factor scoring engine
8. `assemble_html.py` — Final HTML with brand colors

## Critical Quality Gaps (Web App vs CLI)

### Bugs
1. **Contrast check NEVER fires** — `orchestrator.py ~line 1212` checks `passes_aa_normal` but actual field is `passes_wcag_aa_normal_text`
2. **Keyword false positives** — `score_bullets.py` uses substring match ("engineer" matches "reengineering")
3. **Phase 5 silent failures** — After 2 LLM passes, bullets outside 90-100% fill silently accepted

### Missing Quality Checks (CLI has, Web App lacks)

| Check | CLI Weight | Web App State |
|-------|-----------|---------------|
| Keyword coverage (P0/P1) | 30% | Partial — matches HTML, substring, all keywords |
| Width fill (avg + min) | 25% | Partial — avg only, 10% weight |
| Verb deduplication | 15% | Trusts LLM's `verb` field, not extracted |
| Page fit (post-optimization) | 15% | Uses pre-optimization specs (stale) |
| WCAG contrast | 10% | Broken (wrong key name) |
| ATS compliance | 5% | Missing entirely |

### Missing Infrastructure
- **No Quality Judge module** — CLI has dedicated `quality_judge.py` with Grade A-F
- **No state logging** — CLI saves JSON after each step; web app only logs timings
- **No Pydantic validation on LLM responses** — Only catches JSONDecodeError
- **No width-check retry with synonyms** — CLI: 3 retries; web: 2 batch passes then give up
- **No post-LLM validation** — Phase 4A paragraph length, verb uniqueness, `<b>` tags not verified
- **No vector search quality** — No chunk dedup, no empty-chunk warnings

## Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `Resume/worker/app/pipeline/orchestrator.py` | 1578 | Main 8-phase pipeline |
| `Resume/worker/app/pipeline/prompts.py` | ~250 | All LLM prompt templates |
| `Resume/worker/app/qmd_search.py` | 111 | Vector search + FTS fallback |
| `Resume/worker/app/tools/score_bullets.py` | ~300 | BRS scoring engine |
| `Resume/worker/app/tools/measure_width.py` | ~200 | Font-metric width |
| `Resume/worker/app/tools/assemble_html.py` | ~400 | Final HTML assembly |
| `Resume/worker/app/main.py` | ~120 | FastAPI entry point |
| `Resume/worker/app/context.py` | ~50 | PipelineContext dataclass |
| `Resume/website/src/app/resume/new/steps/StepGenerate.tsx` | ~200 | Generation progress UI |
| `linkright/src/linkright/agents/quality_judge.py` | ~150 | CLI gold standard to port |

## Database (Supabase)

**Table: resume_jobs**
- `id`, `user_id`, `status` (queued/running/completed/failed)
- `current_phase`, `phase_number`, `progress_pct`
- `output_html`, `draft_html`, `stats` (JSONB)
- `jd_text`, `career_text`, `model_provider`, `model_id`
- `error_message`, `duration_ms`

**Table: career_chunks** — Indexed career text for FTS fallback

## Tech Dependencies
- **Python**: fastapi, uvicorn, httpx, pydantic, supabase, beautifulsoup4
- **Node**: next@16.2, react@19, @supabase/supabase-js, tailwindcss
- **External**: Supabase (auth + DB + realtime), QMD daemon (optional)
