"""JD keyphrase extraction + source-grounding check for the JD-fishing guard.

A "JD-fishing" bullet is one that injects a JD-specific term (SOX, GDPR, K8s,
SAFe, etc.) which appears in the JD but does NOT appear anywhere in the
candidate's source nuggets / raw resume. This is fabrication dressed up as
JD-alignment.
"""
from __future__ import annotations

import re
from typing import Iterable

# Universal stopwords — drop noise from the JD scan.
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
    # S1.2: universal resume action verbs — appear in virtually all JDs AND bullets.
    # NOT domain-specific; never valid JD-fishing targets. Includes both base and
    # inflected forms because the stem regex (s/ed/ing) misses irregulars (led, drove).
    "lead", "led", "leads", "leading",
    "drive", "drove", "drives", "driving", "driven",
    "manage", "managed", "manages", "managing",
    "build", "built", "builds", "building",
    "launch", "launched", "launches", "launching",
    "develop", "developed", "develops", "developing",
    "design", "designed", "designs", "designing",
    "create", "created", "creates", "creating",
    "implement", "implemented", "implements", "implementing",
    "deploy", "deployed", "deploys", "deploying",
    "deliver", "delivered", "delivers", "delivering",
    "collaborate", "collaborated", "collaborates", "collaborating",
    "partner", "partnered", "partners", "partnering",
    "coordinate", "coordinated", "coordinates", "coordinating",
    "grow", "grew", "grows", "growing", "grown",
    "scale", "scaled", "scales", "scaling",
    "expand", "expanded", "expands", "expanding",
    "increase", "increased", "increases", "increasing",
    "reduce", "reduced", "reduces", "reducing",
    "improve", "improved", "improves", "improving",
    "optimize", "optimized", "optimizes", "optimizing",
    "establish", "established", "establishes", "establishing",
    "identify", "identified", "identifies", "identifying",
    "analyze", "analyzed", "analyzes", "analyzing",
    "evaluate", "evaluated", "evaluates", "evaluating",
    "present", "presented", "presents", "presenting",
    "train", "trained", "trains", "training",
    "mentor", "mentored", "mentors", "mentoring",
    "hire", "hired", "hires", "hiring",
    "direct", "directed", "directs", "directing",
    "oversee", "oversaw", "oversees", "overseeing", "overseen",
    "automate", "automated", "automates", "automating",
    "integrate", "integrated", "integrates", "integrating",
    "migrate", "migrated", "migrates", "migrating",
    "ship", "shipped", "ships", "shipping",
    "release", "released", "releases", "releasing",
    "monitor", "monitored", "monitors", "monitoring",
    "maintain", "maintained", "maintains", "maintaining",
    "spearhead", "spearheaded", "spearheads", "spearheading",
    "champion", "championed", "champions", "championing",
    "facilitate", "facilitated", "facilitates", "facilitating",
    "enable", "enabled", "enables", "enabling",
    "accelerate", "accelerated", "accelerates", "accelerating",
    "generate", "generated", "generates", "generating",
    "introduce", "introduced", "introduces", "introducing",
    "transform", "transformed", "transforms", "transforming",
    "execute", "executed", "executes", "executing",
    "own", "owned", "owns", "owning",
    "achieve", "achieved", "achieves", "achieving",
    "operate", "operated", "operates", "operating",
    "run", "ran", "runs", "running",
    "negotiate", "negotiated", "negotiates", "negotiating",
    "advise", "advised", "advises", "advising",
    "revamp", "revamped", "revamps", "revamping",
    "restructure", "restructured", "restructures", "restructuring",
    "streamline", "streamlined", "streamlines", "streamlining",
    "align", "aligned", "aligns", "aligning",
    "prioritize", "prioritized", "prioritizes", "prioritizing",
    "define", "defined", "defines", "defining",
}

# Tokenize: words of 3+ chars OR all-caps acronyms of 2+ chars.
_TOKEN_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9\-_/+\.]{1,}\b")
_ACRO_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,}\b")


def _norm(tok: str) -> str:
    return tok.strip().lower().rstrip(".,;:!?)").lstrip("(")


def tokenize(text: str) -> set[str]:
    """Lowercase token set with stopwords removed. Includes acronyms (lowercased)
    and yields sub-tokens for hyphenated/slashed compounds (e.g. "GDPR-compliant"
    → {"gdpr-compliant", "gdpr", "compliant"}).
    """
    if not text:
        return set()
    plain = re.sub(r"<[^>]+>", " ", text)
    out: set[str] = set()
    for m in _TOKEN_RE.finditer(plain):
        raw = _norm(m.group(0))
        candidates = [raw]
        if "-" in raw:
            candidates.extend(p for p in raw.split("-") if p)
        if "/" in raw:
            candidates.extend(p for p in raw.split("/") if p)
        for c in candidates:
            if len(c) >= 3 and c not in _STOPWORDS:
                out.add(c)
    return out


def extract_jd_terms(jd_text: str, *, min_len: int = 3) -> set[str]:
    """Extract candidate JD-specific terms.

    Includes:
    - All-caps acronyms (SOX, GDPR, AML, K8s)
    - Capitalized noun-like tokens (Kubernetes, Terraform)
    - Multi-char hyphenated compounds (end-to-end, micro-services)
    - Lowercase tech-vocab tokens of 4+ chars

    S5.3: all returned terms are guaranteed to be present (case-insensitive)
    in the source jd_text.  This is always true for single tokens extracted
    from the text itself, but the explicit gate keeps the contract clear and
    future-proofs against any phrase-level extraction added later.
    """
    if not jd_text:
        return set()
    plain = re.sub(r"<[^>]+>", " ", jd_text)
    jd_lower = jd_text.lower()
    terms: set[str] = set()

    # Acronyms — keep original case for clarity but compare lowercased
    for m in _ACRO_RE.finditer(plain):
        tok = m.group(0).lower()
        if tok in jd_lower:
            terms.add(tok)

    # General tokens
    for m in _TOKEN_RE.finditer(plain):
        n = _norm(m.group(0))
        if len(n) >= min_len and n not in _STOPWORDS and n in jd_lower:
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
