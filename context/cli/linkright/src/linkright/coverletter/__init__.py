"""LinkRight Cover Letter sub-tool (Pillar 1 extension).

5-step mini-pipeline:
  Step 1 — Parse JD into structured requirements (LLM extraction, low temp)
  Step 2 — Retrieve top-N matching nuggets (cosine similarity, no LLM)
  Step 3 — Generate 3-paragraph draft (LLM generation, medium temp ~0.6)
  Step 4 — Truth-engine validation (deterministic, no LLM)
  Step 5 — Format output (deterministic)

Entry point: `linkright cover-letter` (alias: `cl`)
"""
