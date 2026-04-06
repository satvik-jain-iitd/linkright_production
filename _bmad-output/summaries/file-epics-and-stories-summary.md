# File Summary: epics-and-stories.md

- **File:** `_bmad-output/planning-artifacts/epics-and-stories.md`
- **Yeh file kya hai:** Complete story breakdown for LinkRight v2.0 — 22 stories across 4 epics

## Isme Kya Hai
- **Epic 1 (Foundation, Days 1-3):** 5 stories — test infra, DB migration+RLS, nugget extractor, embedder, Phase 0 wiring
- **Epic 2 (Quality Core, Week 1):** 3 stories — quality_judge.py, Phase 7 replacement, 3 bug fixes (contrast/keyword/width)
- **Epic 3 (Retrieval, Week 2):** 4 stories — hybrid retrieval, Phase 2.5 replacement, post-LLM validation, synonym retry loop
- **Epic 4 (Polish, Week 3):** 5 stories — telemetry, frontend dashboard, QJ tests (18), regression tests (7), nugget+retrieval tests (31)
- **Total:** 22 stories, acyclic dependency DAG, every FR mapped to at least 1 story
- **FR-4 absorbed** — no separate stories (merged into FR-9/10/11)
- **RLS security fix** embedded in Story 1.2 (career_nuggets migration)
- **Story format:** title, FR, priority, effort (S/M/L), dependencies, files, acceptance criteria

## Kaun Use Karega
- Sprint Planning (SP) — stories ko sprints me allocate karega
- Dev Story (DS) — har story ko implement karega using acceptance criteria
- ATDD (AT) — failing tests pehle likhega based on ACs
- bd create — har story ek bd task banega implementation me
