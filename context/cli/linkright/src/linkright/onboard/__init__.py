"""linkright onboard — first-run resume → CareerProfile via 4-step pipeline.

Replaces the broken `linkright profile create` flow. Resume-only at
onboarding (no markdown misclassification possible). Roles are extracted
and confirmed BEFORE facts → every fact carries role_id from creation
(no attribution loss).

Steps (per plan Part B.2):
  1. Ingest resume PDF as Evidence (tier=resume_canonical) — uses Phase 0
  2. LLM Pass 1: extract Roles → user batch-confirms
  3. LLM Pass 2: extract Facts per Role → user confirms top facts per role
  4. Cluster Facts → Signals (controlled vocabulary) → write CareerProfile
"""
from __future__ import annotations
