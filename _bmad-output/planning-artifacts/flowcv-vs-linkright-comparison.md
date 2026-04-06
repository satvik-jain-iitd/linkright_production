# FlowCV vs LinkRight — Feature Comparison & Prioritization

## Legend
- **ADOPT** = Copy this feature into LinkRight
- **SKIP** = Not relevant or already better in LinkRight
- **DEFER** = Good idea but not for v2.0
- **ADVANTAGE** = LinkRight already has this, FlowCV doesn't

---

## 1. Resume Building Approach

| Aspect | FlowCV | LinkRight | Verdict |
|--------|--------|-----------|---------|
| Input method | Structured form (fields per section) | Raw text paste/upload | **ADOPT** — structured input = better embeddings, better quality |
| Section types | Personal, Summary, Experience, Education, Skills, Languages, Certs, Projects, Custom | Same via career_signals.yaml (CLI) / raw text (web) | **ADOPT** — web app should have structured form like CLI's YAML |
| Drag-drop reorder | Yes (sections + entries) | No | **ADOPT** — improves UX for section ordering |
| Rich-text editing | Per-field (bold, italic, bullets, links) | No inline editing (LLM generates all) | **DEFER** — our USP is LLM generation, not manual editing |
| Live preview | Real-time as user types | Only after full generation | **ADOPT** — show stencil preview during wizard steps |
| PDF import | Parse uploaded PDF → populate fields | No | **DEFER** — nice-to-have, not core |
| LinkedIn import | Listed as option | No | **DEFER** |

## 2. Template & Customization

| Aspect | FlowCV | LinkRight | Verdict |
|--------|--------|-----------|---------|
| Template gallery | 20+ templates, instant switch, no data loss | 1 template (cv-a4-standard) | **ADOPT** — multiple templates is table stakes |
| Layout control | Single/two-column toggle, section assignment | Fixed layout | **DEFER** — start with 3-5 templates first |
| Spacing sliders | Line, section, page margin, item spacing | Computed automatically via page_fit | **SKIP** — our auto-fit is actually better |
| Color customization | Preset palettes + hex picker | Brand color from JD company | **SKIP** — our auto-brand-color is smarter |
| Font selection | Google Fonts dropdown with search | Roboto only (precise width metrics) | **DEFER** — adding fonts means new width metrics per font |
| Header customization | Photo, layout presets, shape | No photo, fixed header | **DEFER** |

## 3. AI Features

| Aspect | FlowCV | LinkRight | Verdict |
|--------|--------|-----------|---------|
| AI Write (generate from scratch) | Per-field, based on job title | Full resume generation from JD + career | **ADVANTAGE** — LinkRight's JD-matching is far superior |
| AI Improve (refine existing) | Per-field inline button | Chat editor in StepReview | **ADOPT** — add inline "improve" per bullet in review |
| AI Summary generator | Standalone tool | Auto-generated in pipeline | **ADVANTAGE** — ours is integrated into pipeline |
| Quality scoring | NONE | Quality Judge with Grade A-F (v2.0) | **ADVANTAGE** — FlowCV has zero quality feedback |
| ATS analysis | NONE (noted as gap in teardown) | ATS compliance check (v2.0) | **ADVANTAGE** |
| Keyword optimization | NONE | BRS scoring against JD keywords | **ADVANTAGE** |
| Width precision | Basic spacing sliders | Sub-pixel Roboto font metrics | **ADVANTAGE** |
| Credit system | 3-10 free, then pay | BYOK (user's own API key) | **ADVANTAGE** — no credit limits |

## 4. Career Data Processing

| Aspect | FlowCV | LinkRight Current | LinkRight Could Be (with Life OS code) | Verdict |
|--------|--------|-------------------|---------------------------------------|---------|
| Input | Structured form per field | Raw text → paragraph chunking | Q&A extraction + semantic chunking + Hebbian edges | **ADOPT** — port Life OS pipeline |
| Storage | Server-side document DB | Supabase FTS (plain text) | ChromaDB/MongoDB with 768-dim vectors + 47-field metadata | **ADOPT** — proper vector embeddings |
| Retrieval | N/A (no search needed) | QMD hybrid / FTS fallback | Hybrid (BM25 + vector + RRF) + Hebbian-weighted spreading activation | **ADOPT** — massive quality improvement |
| Pre-processing | None (structured input) | None (raw text) | LLM Q&A extraction → nuggets → atomic facts | **ADOPT** — this fixes the root quality problem |

## 5. Additional Features

| Aspect | FlowCV | LinkRight | Verdict |
|--------|--------|-----------|---------|
| Cover letter builder | Yes (secondary quality) | No | **DEFER** — not core for v2.0 |
| Job tracker (Kanban) | Yes (basic, 5 columns) | No | **DEFER** — separate product |
| Website builder | Yes (Pro) | No | **SKIP** — not relevant |
| Share link | Yes (public URL) | No | **DEFER** |
| Multiple resumes | Unlimited, list view | Yes (dashboard) | Already have |
| Auto-save | Yes (debounced) | Yes (Supabase realtime) | Already have |
| Duplicate resume | Yes (one-click) | No | **ADOPT** — easy to add |
| Rename resume | Yes | No | **ADOPT** — easy to add |

## 6. Onboarding & UX

| Aspect | FlowCV | LinkRight | Verdict |
|--------|--------|-----------|---------|
| First-run experience | Zero friction — empty resume auto-created | 5-step wizard | **SKIP** — our wizard is intentionally guided |
| Onboarding tour | None | None | Both skip this |
| Empty states | Well-designed with CTAs | Basic | **ADOPT** — improve empty states |
| Error recovery | Offline buffering, clear error messages | Basic error display | **ADOPT** — better error UX |

---

## PRIORITIZED RECOMMENDATION

### v2.0 Scope (This Release) — Quality + Career Processing

| # | Feature | Source | Effort | Impact | Priority |
|---|---------|--------|--------|--------|----------|
| 1 | Quality Judge (6 checks, Grade A-F) | Original PRD | 3 hr | Critical | **P0** |
| 2 | Bug fixes (contrast, keyword, width) | Original PRD | 2 hr | Critical | **P0** |
| 3 | Career pre-processing: Q&A extraction from raw text | Life OS / life-history | 4 hr | Critical | **P0** |
| 4 | Semantic chunking (paragraph-aware, 50-500 tokens) | Life OS / Career-context | 3 hr | High | **P1** |
| 5 | Vector embeddings (BGE-base + Supabase pgvector) | Life OS / LinkRight | 4 hr | High | **P1** |
| 6 | Hybrid search (BM25 + vector + RRF) replacing FTS | LinkRight packages | 3 hr | High | **P1** |
| 7 | Post-LLM validation (Pydantic, length, verbs, tags) | Original PRD | 3 hr | High | **P1** |
| 8 | Synonym retry loop (3 attempts per bullet) | Original PRD | 2 hr | High | **P1** |
| 9 | Pipeline telemetry (phase snapshots) | Original PRD | 2 hr | Medium | **P2** |
| 10 | Frontend quality dashboard (grade badge, metrics) | Original PRD | 3 hr | Medium | **P2** |
| 11 | Inline "improve" per bullet in StepReview | FlowCV | 2 hr | Medium | **P2** |
| 12 | Test suite (unit + E2E) | Original PRD | 3 hr | Medium | **P2** |

### v2.1 Scope (Next Release) — FlowCV-Inspired UX

| # | Feature | Source | Effort |
|---|---------|--------|--------|
| 1 | Structured career input form (replace raw text) | FlowCV | 2 weeks |
| 2 | Template gallery (3-5 templates with instant switch) | FlowCV | 2 weeks |
| 3 | Live stencil preview during wizard | FlowCV | 1 week |
| 4 | Hebbian learning service (edge strengthening on retrieval) | Life OS | 1 week |
| 5 | Duplicate/rename resume from dashboard | FlowCV | 2 days |
| 6 | Better empty states with CTAs | FlowCV | 2 days |
| 7 | Cover letter builder | FlowCV | 3 weeks |
| 8 | Drag-drop section reorder | FlowCV | 1 week |

### v2.2 Scope (Future)

| # | Feature | Source |
|---|---------|--------|
| 1 | Multi-JD optimization matrix | Brainstorming |
| 2 | ATS simulation engine | Brainstorming |
| 3 | PDF/LinkedIn import | FlowCV |
| 4 | Font selection (multi-font width metrics) | FlowCV |
| 5 | Share link (public URL) | FlowCV |
| 6 | Job tracker Kanban | FlowCV |

---

## KEY INSIGHT

**FlowCV is a WYSIWYG editor** — user manually builds resume section by section.
**LinkRight is an AI generation engine** — LLM builds resume from career data + JD.

These are fundamentally different products. We should NOT try to become FlowCV. Instead:

1. **Steal the structured input** — FlowCV proves users WANT structured fields, not raw text. But we use them for BETTER AI generation, not manual editing.
2. **Steal the quality visibility** — FlowCV has ZERO quality feedback. We should be the first to show quality grades, keyword coverage, width precision as a differentiator.
3. **Steal the template flexibility** — Multiple templates with instant switch is expected. Users should pick after generation.
4. **Keep our AI core** — JD matching, BRS scoring, width precision, quality grading are things NO other builder has. Double down here.

**Bottom line for v2.0:**
- Fix quality (original PRD) ✓
- Add career pre-processing (Life OS code) ✓
- Skip FlowCV UX features (v2.1) ✓
