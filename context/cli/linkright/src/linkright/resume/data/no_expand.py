"""Shared no-expand acronym set — single source of truth.

Imported by:
- resume/orchestrator.py step_14: blocks corpus learning + inline expansion
- resume/scorecard.py:            blocks penalty for unexpanded occurrence

S1.5 (2026-05-11): modernised to include AI/ML compound terms that the corpus
was incorrectly learning and expanding (e.g. GenAI → Gen-Artificial Intelligence).

Rule for membership:
- Include only universally-known tokens where expansion is NEVER correct.
- Domain-specific acronyms (AML, SOX, GDPR, K8s) must NOT be here — they
  should be auto-learned from context ("Anti-Money Laundering (AML)") and
  expanded on first use.
"""
from __future__ import annotations

_UNIVERSAL_NO_EXPAND: frozenset[str] = frozenset({
    # General tech / infra
    "PM", "AI", "ML", "AR", "VR", "API", "SQL", "AWS", "GCP", "iOS", "OS",
    "UX", "UI", "REST", "JSON", "XML", "CSS", "JS", "PDF", "URL", "SDK",
    "HTML", "HTTP", "HTTPS", "DNS", "VPN", "SSL", "TLS", "DB", "RPC",
    "CPU", "GPU", "RAM", "SSD", "CLI", "GUI", "B2B", "B2C", "SaaS",
    "CRM", "ERP", "JD", "HR", "QA",
    # AI / ML compound terms — product names / paradigm labels.
    # Expansion is ALWAYS wrong (GenAI ≠ "Gen-Artificial Intelligence").
    "LLM", "LLMs", "NLP", "MCP", "RAG", "GenAI", "GPT", "BERT", "GAN",
    "MLOps", "AIOps", "NLU", "NLG", "XAI", "RL", "RLHF", "DL", "CV",
    "OCR", "NER", "ASR", "TTS", "STT",
    # Auth / protocol tokens
    "OAuth", "JWT",
})

# Pre-computed uppercase version for case-insensitive checks against
# corpus entries that may have been written as lowercase in prior runs.
_UNIVERSAL_NO_EXPAND_UPPER: frozenset[str] = frozenset(t.upper() for t in _UNIVERSAL_NO_EXPAND)
