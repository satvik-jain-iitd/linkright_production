# File Summary: prd.md

- **File:** `_bmad-output/planning-artifacts/prd.md`
- **Yeh file kya hai:** LinkRight v2.0 Quality Release ka Product Requirements Document

## Isme Kya Hai
- **Executive Summary** — 9 quality gaps, 2 critical bugs, CLI parity goal
- **Problem Statement** — contrast broken, keywords inflated, width silent, no grade visible
- **Success Criteria** — 90%+ Grade A/B, keyword >60%, fill >90%, zero verb dupes, 100% WCAG+ATS
- **3 User Journeys** — happy path (Grade A → download), failure (Grade C → suggestions), partial (vector empty → fallback)
- **7 Functional Requirements** grouped by epic:
  - FR-1 Quality Judge (P0), FR-2 Bug Fixes (P0), FR-3 Post-LLM Validation (P1)
  - FR-4 Vector Search (P1), FR-5 Telemetry (P2), FR-6 Frontend Dashboard (P2), FR-7 Tests (P2)
- **NFRs** — pipeline <3 min, 90%+ reliability, full telemetry, no breaking changes
- **Out of Scope** — moonshots deferred to v2.1 (multi-JD, ATS sim, auto-regen)
- **Risks** — grade mismatch, retry storms, regex edge cases, duration

## Kaun Use Karega
- Phase 3 mein validation (VP) ke liye — 13 checks against this PRD
- Phase 4 mein Winston (Architect) — architecture decisions ke basis ke liye
- Phase 5 mein stories ka source of truth — har FR ek ya zyada stories banega
