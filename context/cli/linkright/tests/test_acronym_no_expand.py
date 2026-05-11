"""Tests for S1.5 — known AI/tech acronyms must not be learned/expanded.

Root cause: _UNIVERSAL_NO_EXPAND (orchestrator) and _COMMON_KNOWN_ACRONYMS
(scorecard) were both missing modern AI terms (GenAI, LLM, RAG, MCP, etc.).
The corpus could "learn" expansions like GenAI → Gen-Artificial Intelligence
from resume text such as "led GenAI (Gen-Artificial Intelligence) strategy".

These tests cover two enforcement layers:
- AC1: scorecard._learnable_expansions_from_text blocks known acronyms (no penalty)
- AC2: _UNIVERSAL_NO_EXPAND (imported directly) blocks corpus learning (no expansion)
- AC3: case-insensitive guard blocks lowercase corpus variants
- AC4: domain-specific acronyms (AML, SOX) remain learnable
- AC5: single source of truth — scorecard._COMMON_KNOWN_ACRONYMS IS _UNIVERSAL_NO_EXPAND
"""
import pytest
from linkright.resume.data.no_expand import _UNIVERSAL_NO_EXPAND, _UNIVERSAL_NO_EXPAND_UPPER
from linkright.resume.scorecard import _learnable_expansions_from_text, _COMMON_KNOWN_ACRONYMS


def _no_expand_set() -> frozenset:
    """Live reference — imported from data/no_expand.py, not a mirror."""
    return _UNIVERSAL_NO_EXPAND


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
    """Imported _UNIVERSAL_NO_EXPAND_UPPER must block lowercase corpus variants."""
    for term in ["genai", "llm", "rag", "nlp", "mcp", "gpt", "oauth", "jwt"]:
        assert term.upper() in _UNIVERSAL_NO_EXPAND_UPPER, (
            f"Lowercase corpus variant '{term}' not blocked by _UNIVERSAL_NO_EXPAND_UPPER"
        )


@pytest.mark.parametrize("variant,text", [
    # pat_b form: "Genai (General AI)" — starts [A-Z] then lowercase. Scorer must not learn.
    ("Genai",  "Led Genai (General AI) integration for search"),
    ("Mlops",  "Built Mlops (Machine Learning Ops) platform"),
    ("Oauth",  "Secured via Oauth (Open Auth) 2.0"),
])
def test_scorecard_does_not_learn_mixed_case_variant(variant, text):
    """_learnable_expansions_from_text must not learn mixed-case protected variants.

    'Genai' (capital G, lower rest) matches pat_b regex but must be blocked by
    the case-insensitive _KNOWN_UPPER check. Without this fix the scorer would
    learn the pair and penalise bullets where the variant appears unexpanded.
    """
    learned = _learnable_expansions_from_text(text)
    assert variant not in learned, (
        f"Mixed-case variant '{variant}' was incorrectly learned: {learned.get(variant)!r}"
    )


# ── AC5-identity: scorecard IS the shared set (no independent copy) ───────────

def test_scorecard_known_acronyms_is_shared_set():
    """_COMMON_KNOWN_ACRONYMS must be the same object as _UNIVERSAL_NO_EXPAND.

    Proves single source of truth — the two enforcement layers share one frozenset,
    drift between them is structurally impossible.
    """
    assert _COMMON_KNOWN_ACRONYMS is _UNIVERSAL_NO_EXPAND, (
        "_COMMON_KNOWN_ACRONYMS is a separate copy — scorecard.py must import "
        "from data/no_expand.py, not define its own set."
    )


# ── AC6: domain-specific acronyms remain learnable ───────────────────────────

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
