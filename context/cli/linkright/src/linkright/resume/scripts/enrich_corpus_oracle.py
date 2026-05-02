"""Offline Oracle-based enrichment of the learned corpus + SYNONYM_BANK.

Purpose
-------
The pipeline's per-run auto-learn (orchestrator step_14) only captures acronym
pairs explicitly defined in the user's resume / JD. Many users write "AML" or
"K8s" without ever defining them inline — we want graceful expansion in those
cases too, without hardcoding domain-specific dicts in code.

This script asks Oracle gemma3:1b (free, self-hosted) to:
1. Expand vocab_candidates (words seen in past runs) into 2-3 synonyms
2. Optionally suggest expansions for ALL-CAPS tokens that look like acronyms
   but have no expansion in the user's corpus

Run manually:
    PYTHONPATH=src python -m linkright.resume.scripts.enrich_corpus_oracle

Or schedule via cron (weekly):
    0 3 * * 0 cd /path/to/linkright && PYTHONPATH=src python -m linkright.resume.scripts.enrich_corpus_oracle

Requirements
------------
- ORACLE_BACKEND_URL + ORACLE_BACKEND_SECRET in env
- ~10-20 minutes runtime depending on corpus size
- ZERO ₹ cost (Oracle self-hosted)

Output
------
- Updates ~/.linkright/learned_corpus.json (acronyms section)
- Stamps last_enriched_at
- Prints before/after summary
"""
from __future__ import annotations

import re
import sys
import time

from ..data.learned_corpus import (
    add_vocab_candidates,
    load_corpus,
    save_corpus,
    stamp_enriched,
)
from ...llm.oracle import oracle_rewrite, oracle_health


def _ask_oracle_for_expansion(acronym: str) -> str | None:
    """Single Oracle gemma3:1b call to expand an acronym for a resume context.

    Returns the expansion phrase (1-5 words) or None if Oracle returns garbage.
    """
    prompt = (
        f"What does the acronym '{acronym}' commonly stand for in a professional "
        f"resume context? Reply with ONLY the expanded phrase (2-5 words). "
        f"If unknown or ambiguous, reply 'UNKNOWN'."
    )
    try:
        resp = oracle_rewrite(prompt, system="You are a professional resume editor.", temperature=0.1)
    except Exception as e:
        print(f"  [{acronym}] Oracle error: {e}")
        return None
    text = (resp.text or "").strip()
    # Take first line only
    text = text.split("\n")[0].strip().rstrip(".")
    if not text or "UNKNOWN" in text.upper() or len(text) > 80:
        return None
    # Validate: at least one initial overlaps with acronym
    word_initials = "".join(w[0].upper() for w in re.split(r"[\s\-]+", text) if w and w[0].isalpha())
    ac_letters = re.sub(r"[^A-Z]", "", acronym.upper())
    if ac_letters and not any(c in word_initials for c in ac_letters):
        return None
    return text


def main() -> int:
    print("=" * 64)
    print("Oracle-based corpus enrichment")
    print("=" * 64)

    if not oracle_health():
        print("ERROR: Oracle backend not reachable. Check ORACLE_BACKEND_URL + ORACLE_BACKEND_SECRET.")
        return 1

    corpus = load_corpus()
    initial_acronyms = len(corpus.get("acronyms") or {})
    initial_vocab = len(corpus.get("vocab_candidates") or [])
    print(f"Initial corpus: {initial_acronyms} acronyms, {initial_vocab} vocab candidates")
    print()

    # Find acronyms that exist in vocab_candidates (or were guessed elsewhere) but
    # have no expansion in corpus["acronyms"]. Also: scan for ALL-CAPS tokens in
    # vocab_candidates that look like acronyms.
    candidate_acronyms = set()
    for w in corpus.get("vocab_candidates") or []:
        w_clean = (w or "").strip()
        # Filter: 2-5 char ALL-CAPS sequences
        if 2 <= len(w_clean) <= 5 and w_clean.isupper() and w_clean.isalpha():
            if w_clean not in (corpus.get("acronyms") or {}):
                candidate_acronyms.add(w_clean)

    if not candidate_acronyms:
        print("No new acronym candidates to enrich. Add words to vocab_candidates "
              "via per-run learning, then re-run.")
        return 0

    print(f"Asking Oracle gemma3:1b to expand {len(candidate_acronyms)} candidate(s)...")
    t0 = time.time()
    new_count = 0
    for ac in sorted(candidate_acronyms):
        expansion = _ask_oracle_for_expansion(ac)
        if expansion:
            corpus["acronyms"][ac] = expansion
            new_count += 1
            print(f"  + {ac} → {expansion}")
        else:
            print(f"  - {ac} (no good expansion)")

    duration = time.time() - t0
    stamp_enriched(corpus)
    save_corpus(corpus)

    print()
    print(f"Done. Added {new_count} new acronym expansions in {duration:.1f}s.")
    print(f"Final corpus: {len(corpus['acronyms'])} acronyms, "
          f"{len(corpus.get('vocab_candidates') or [])} vocab candidates")
    print(f"Corpus saved to: ~/.linkright/learned_corpus.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
