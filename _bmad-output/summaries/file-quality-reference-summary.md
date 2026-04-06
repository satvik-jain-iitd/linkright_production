# File Summary: LINKRIGHT_QUALITY_REFERENCE.md

- **File:** `LINKRIGHT_QUALITY_REFERENCE.md` (repo root mein)
- **Purpose:** CLI tool ka quality system — yeh "gold standard" hai jo web app ko match karna hai

## Isme Kya Hai

- **Quality Judge (6 Checks)** — Har check ka weight, formula, aur threshold:
  - Keyword Coverage (30%) — P0/P1 JD keywords bullets mein hone chahiye
  - Width Fill (25%) — Har bullet 90-100% line fill hona chahiye (avg + min)
  - Verb Dedup (15%) — Koi bhi action verb repeat nahi hona chahiye
  - Page Fit (15%) — Sab content A4 pe fit hona chahiye (271.6mm)
  - WCAG Contrast (10%) — Brand colors 4.5:1 ratio pass karne chahiye
  - ATS Compliance (5%) — Koi `<table>` ya `<img>` tags nahi hone chahiye
- **Grading System** — A>=90, B>=75, C>=60, D>=40, F<40
- **BRS Scoring (5 Factors)** — Keyword overlap (35%), metric magnitude (25%), recency (20%), leadership (10%), uniqueness (10%)
- **Width Retry Loop** — 3 attempts per bullet, synonym suggestions se adjust karna
- **State Logging** — Har pipeline step ke baad JSON file save hoti hai `.linkright/state/` mein
- **Pydantic Schemas** — JDAnalysis, WrittenBullet, QualityReport, CareerSignals ke complete field definitions

## Kaun Use Karega

- Phase 5 mein Amelia (Dev) — quality_judge.py port karne ke liye exact reference
- Phase 4 mein Winston (Architect) — architecture decisions ke liye quality gate specs
- Phase 6 mein Murat (Test) — test cases likhne ke liye expected behavior
