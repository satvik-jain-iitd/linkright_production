"""Tests for S1.5 — known AI/tech acronyms must not be learned/expanded.

Root cause: _UNIVERSAL_NO_EXPAND (orchestrator) and _COMMON_KNOWN_ACRONYMS
(scorecard) were both missing modern AI terms (GenAI, LLM, RAG, MCP, etc.).
The corpus could "learn" expansions like GenAI → Gen-Artificial Intelligence
from resume text such as "led GenAI (Gen-Artificial Intelligence) strategy".

These tests cover two enforcement layers:
- AC1: scorecard._learnable_expansions_from_text blocks known acronyms (no penalty)
- AC2: _UNIVERSAL_NO_EXPAND (mirrored) blocks corpus learning (no expansion)
- AC3: case-insensitive guard blocks lowercase corpus variants
- AC4: domain-specific acronyms (AML, SOX) remain learnable
"""
import pytest
from linkright.resume.scorecard import _learnable_expansions_from_text, _COMMON_KNOWN_ACRONYMS


# ── Mirror of orchestrator._UNIVERSAL_NO_EXPAND (can't import directly) ──────

def _no_expand_set() -> set:
    """Mirror of orchestrator._UNIVERSAL_NO_EXPAND — kept in sync with S1.5 fix."""
    return {
        "PM", "AI", "ML", "AR", "VR", "API", "SQL", "AWS", "GCP", "iOS", "OS",
        "UX", "UI", "REST", "JSON", "XML", "CSS", "JS", "PDF", "URL", "SDK",
        "HTML", "HTTP", "HTTPS", "DNS", "VPN", "SSL", "TLS", "DB", "RPC",
        "CPU", "GPU", "RAM", "SSD", "CLI", "GUI", "B2B", "B2C", "SaaS",
        "CRM", "ERP", "JD", "HR", "QA",
        "LLM", "LLMs", "NLP", "MCP", "RAG", "GenAI", "GPT", "BERT", "GAN",
        "MLOps", "AIOps", "NLU", "NLG", "XAI", "RL", "RLHF", "DL", "CV",
        "OCR", "NER", "ASR", "TTS", "STT",
        "OAuth", "JWT",
    }


# ── AC1: scorecard does NOT learn known AI acronyms ──────────────────────────
# Prevents fabricated expansions like "GenAI → Gen-Artificial Intelligence" from
# ever entering the learned dict and triggering a penalty on subsequent bullets.

@pytest.mark.parametrize("acronym,text", [
    ("LLM",   "Led LLM (Language Learning Machine) integration for search"),
    ("LLMs",  "Fine-tuned LLMs (Large Language Modules) on proprietary data"),
    ("NLP",   "Built NLP (Natural Language Pipeline) processing 500K queries"),
    ("MCP",   "Deployed MCP (Multi-Cloud Protocol) server for 12 agents"),
    ("RAG",   "Shipped RAG (Retrieval And Generation) system cutting tickets 25%"),
    ("GenAI", "Led GenAI (General Artificial Intelligence) strategy for $5M ARR"),
    ("GPT",   "Integrated GPT (General Purpose Transformer) assistant"),
    ("BERT",  "Fine-tuned BERT (Bidirectional Encoding Representation) model"),
    ("MLOps", "Built MLOps (Machine Learning Ops) platform"),
    ("AIOps", "Implemented AIOps (AI for IT Ops) pipeline"),
    ("OAuth", "Secured service via OAuth (Open Auth) 2.0 PKCE"),
    ("JWT",   "Rotated JWT (JSON Web Tokens) to cut auth errors 80%"),
])
def test_scorecard_does_not_learn_known_acronym(acronym, text):
    """_learnable_expansions_from_text must NOT learn known AI/tech acronyms."""
    learned = _learnable_expansions_from_text(text)
    assert acronym not in learned, (
        f"'{acronym}' was incorrectly learned from: {text!r}\n"
        f"  → would produce bad expansion: {learned.get(acronym)!r}"
    )


# ── AC2: _COMMON_KNOWN_ACRONYMS contains modern AI terms ─────────────────────

EXPECTED_IN_KNOWN = [
    "LLM", "LLMs", "NLP", "MCP", "RAG",
    "GenAI", "GPT", "BERT", "GAN",
    "MLOps", "AIOps", "NLU", "NLG", "XAI",
    "OCR", "NER", "OAuth", "JWT",
]

@pytest.mark.parametrize("term", EXPECTED_IN_KNOWN)
def test_term_in_common_known_acronyms(term):
    """_COMMON_KNOWN_ACRONYMS must contain modern AI/ML term."""
    assert term in _COMMON_KNOWN_ACRONYMS, (
        f"'{term}' missing from _COMMON_KNOWN_ACRONYMS — scorecard will learn "
        f"bad expansions and apply a penalty when the acronym appears unexpanded."
    )


# ── AC3: _UNIVERSAL_NO_EXPAND (mirrored) contains modern AI terms ─────────────

EXPECTED_IN_NO_EXPAND = [
    "LLM", "LLMs", "NLP", "MCP", "RAG",
    "GenAI", "GPT", "BERT", "GAN",
    "MLOps", "AIOps", "NLU", "NLG", "XAI",
    "OCR", "NER", "OAuth", "JWT",
]

@pytest.mark.parametrize("term", EXPECTED_IN_NO_EXPAND)
def test_term_in_universal_no_expand(term):
    """Mirrored _UNIVERSAL_NO_EXPAND must contain modern AI term."""
    assert term in _no_expand_set(), (
        f"'{term}' missing from _UNIVERSAL_NO_EXPAND — corpus will learn and expand it."
    )


# ── AC4: case-insensitive guard blocks lowercase corpus variants ──────────────

def test_lowercase_variants_blocked_by_upper_set():
    """Case-insensitive set must catch lowercase corpus variants like 'genai'."""
    no_expand_upper = {t.upper() for t in _no_expand_set()}
    for term in ["genai", "llm", "rag", "nlp", "mcp", "gpt", "oauth", "jwt"]:
        assert term.upper() in no_expand_upper, (
            f"Lowercase corpus variant '{term}' not blocked by _UNIVERSAL_NO_EXPAND_UPPER"
        )


# ── AC5: domain-specific acronyms remain learnable ───────────────────────────

@pytest.mark.parametrize("acronym,text", [
    ("AML",  "Led AML (Anti-Money Laundering) compliance initiative"),
    ("SOX",  "Implemented Sarbanes Oxley (SOX) controls for financial reporting"),
    ("GDPR", "Ensured GDPR (General Data Protection Regulation) compliance"),
    ("WCAG", "Achieved WCAG (Web Content Accessibility Guidelines) Level AA"),
])
def test_domain_specific_acronym_is_learnable(acronym, text):
    """Domain-specific acronyms (AML, SOX, GDPR) must be learned from source text."""
    learned = _learnable_expansions_from_text(text)
    assert acronym in learned, (
        f"'{acronym}' was not learned from: {text!r} — "
        f"domain-specific acronyms must remain learnable for first-use expansion."
    )


def test_domain_acronyms_not_in_no_expand():
    """Domain-specific acronyms must NOT be in _UNIVERSAL_NO_EXPAND."""
    no_expand = _no_expand_set()
    for ac in ["AML", "SOX", "GDPR", "WCAG"]:
        assert ac not in no_expand, (
            f"'{ac}' is in _UNIVERSAL_NO_EXPAND — it should be learnable from context"
        )
