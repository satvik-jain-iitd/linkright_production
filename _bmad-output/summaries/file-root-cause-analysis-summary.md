# File Summary: root-cause-analysis.md

- **File:** `_bmad-output/planning-artifacts/root-cause-analysis.md`
- **Yeh file kya hai:** 9 quality gaps ka detailed root-cause analysis with exact fixes

## Isme Kya Hai
- **9 gaps** ka systematic breakdown — har ek ke liye: root cause, impact, solution, verification
- **Priority matrix** — P0 (2 gaps: contrast + keywords), P1 (3 gaps: width + synonym + post-LLM), P2 (3 gaps: judge + Pydantic + vector), P3 (1 gap: state logging)
- **Exact file locations** — orchestrator.py line numbers, score_bullets.py functions, qmd_search.py methods
- **Fix descriptions** — specific code changes (kaunsa key change karna hai, kaunsa regex use karna hai, kaunsa function add karna hai)
- **Verification steps** — har fix ke liye test case (kya input dena hai, kya assert karna hai)
- **Effort estimates** — 5 min se lekar 3 hr tak, total ~16 hrs sab gaps fix karne ke liye

## Kaun Use Karega
- Phase 3 mein John (PM) — PRD mein acceptance criteria define karne ke liye
- Phase 4 mein Winston (Architect) — architecture decisions mein exact integration points
- Phase 5 mein Amelia (Dev) — direct reference jab code fix karegi
- Phase 6 mein Murat (Test) — test cases likhne ke liye expected behavior
