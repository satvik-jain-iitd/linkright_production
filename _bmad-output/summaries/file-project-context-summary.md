# File Summary: project-context.md

- **File:** `_bmad-output/project-context.md`
- **Purpose:** LinkRight web app ka poora architecture document — BMAD agents ke liye banaya gaya

## Isme Kya Hai

- **Architecture Overview** — FastAPI backend + Next.js 16.2 frontend + Supabase (auth, DB, realtime)
- **8 Pipeline Phases** — Har phase ka input, output, LLM calls, aur quality gates documented:
  - Phase 1+2: JD parse + strategy select (LLM call)
  - Phase 2.5: Vector search QMD/FTS se career chunks laana
  - Phase 3-3.5: Page fit check + stencil HTML draft
  - Phase 4A-4C: Verbose bullets → BRS rank → condense (3 LLM calls)
  - Phase 5: Width optimization loop (1-2 LLM calls)
  - Phase 6-8: BRS re-score → validation → final HTML assembly
- **8 Shared Tools** — measure_width, score_bullets, validate_contrast, etc. sab ka schema
- **3 LLM Providers** — OpenRouter, Groq, Gemini with retry logic
- **Vector Search** — QMD daemon (hybrid BM25 + vector) with Supabase FTS fallback
- **Quality Gaps** — 3 critical bugs (contrast broken, keyword false positives, silent width failures) + 6 missing checks vs CLI

## Kaun Use Karega

- BMAD agents (Winston/Architect, John/PM, Murat/Test) — architecture decisions ke liye
- Phase 3 PRD creation mein input material ke taur pe
- Phase 4 architecture design mein reference ke liye
