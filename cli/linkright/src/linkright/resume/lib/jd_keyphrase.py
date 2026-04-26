"""JD keyphrase extraction + source-grounding check for the JD-fishing guard.

A "JD-fishing" bullet is one that injects a JD-specific term (SOX, GDPR, K8s,
SAFe, etc.) which appears in the JD but does NOT appear anywhere in the
candidate's source nuggets / raw resume. This is fabrication dressed up as
JD-alignment.
"""
from __future__ import annotations

import re
from typing import Iterable

# Universal stopwords — small list, mostly to drop noise from the JD scan.
_STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "our", "are", "from", "this",
    "that", "will", "have", "has", "had", "been", "being", "was", "were", "but",
    "not", "all", "any", "can", "may", "must", "should", "would", "could",
    "into", "across", "within", "while", "than", "more", "less", "such", "also",
    "their", "they", "them", "these", "those", "what", "when", "where", "which",
    "who", "whom", "why", "how", "about", "above", "after", "before", "below",
    "between", "during", "under", "over", "through", "until", "once", "each",
    "every", "some", "both", "either", "neither", "other", "another",
    "team", "teams", "work", "working", "role", "roles", "candidate",
    "experience", "years", "year", "skills", "skill", "ability", "abilities",
    "responsibilities", "responsibility", "requirements", "requirement",
    "preferred", "required", "must-have", "nice-to-have", "qualifications",
    "company", "companies", "employer", "employers", "engineering", "engineer",
    "software", "developer", "development", "developers",
}

# Tokenize: words of 3+ chars OR all-caps acronyms of 2+ chars.
_TOKEN_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9\-_/+\.]{1,}\b")
_ACRO_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,}\b")


def _norm(tok: str) -> str:
    return tok.strip().lower().rstrip(".,;:!?)").lstrip("(")


def tokenize(text: str) -> set[str]:
    """Lowercase token set with stopwords removed. Includes acronyms (lowercased)."""
    if not text:
        return set()
    plain = re.sub(r"<[^>]+>", " ", text)
    out: set[str] = set()
    for m in _TOKEN_RE.finditer(plain):
        n = _norm(m.group(0))
        if len(n) >= 3 and n not in _STOPWORDS:
            out.add(n)
    return out


def extract_jd_terms(jd_text: str, *, min_len: int = 3) -> set[str]:
    """Extract candidate JD-specific terms.

    Includes:
    - All-caps acronyms (SOX, GDPR, AML, K8s)
    - Capitalized noun-like tokens (Kubernetes, Terraform)
    - Multi-char hyphenated compounds (end-to-end, micro-services)
    - Lowercase tech-vocab tokens of 4+ chars
    """
    if not jd_text:
        return set()
    plain = re.sub(r"<[^>]+>", " ", jd_text)
    terms: set[str] = set()

    # Acronyms — keep original case for clarity but compare lowercased
    for m in _ACRO_RE.finditer(plain):
        terms.add(m.group(0).lower())

    # General tokens
    for m in _TOKEN_RE.finditer(plain):
        n = _norm(m.group(0))
        if len(n) >= min_len and n not in _STOPWORDS:
            terms.add(n)

    return terms


def find_fishing(
    bullet_text: str,
    jd_terms: set[str],
    source_texts: Iterable[str],
) -> list[str]:
    """Return JD terms that appear in the bullet but NOT in source.

    These are likely-fabricated JD-fishing injections.
    """
    bullet_tokens = tokenize(bullet_text)
    if not bullet_tokens:
        return []
    source_tokens: set[str] = set()
    for s in source_texts:
        source_tokens |= tokenize(s)

    flagged: list[str] = []
    for tok in bullet_tokens:
        if tok in jd_terms and tok not in source_tokens:
            # crude stem fuzz: strip trailing s/ed/ing
            stem = re.sub(r"(s|ed|ing)$", "", tok)
            if stem and stem in source_tokens:
                continue
            flagged.append(tok)
    return flagged
