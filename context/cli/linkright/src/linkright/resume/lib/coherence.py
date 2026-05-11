"""S5.6 — cross-bullet verb coherence enforcer."""
from __future__ import annotations

import re
from collections import Counter

from linkright.llm.oracle import oracle_generate

_VERB_RE = re.compile(r"^(?:●\s*)?([A-Z][a-z]+)\b")


def _leading_verb(bullet: str) -> str | None:
    m = _VERB_RE.match(bullet.strip())
    return m.group(1) if m else None


def _brs_score(bullet: str) -> float:
    """Lazy import to avoid circular; returns _brs if already tagged else 1.0."""
    return 1.0  # caller passes tagged dict separately


def enforce_verb_coherence(
    bullets: list[dict],  # each dict has keys: text_html, _weighted_brs, others
    section_id: str = "unknown",
    _oracle_ok: bool = False,
) -> list[dict]:
    """
    For each duplicate leading verb in the section, attempt Oracle rephrase.
    Reverts if rephrased bullet's structure heuristic fails.
    Max 1 attempt per bullet. Oracle unavailable → skip silently.
    """
    if not bullets or not _oracle_ok:
        return bullets

    # Count verbs
    verb_counts: Counter = Counter()
    for b in bullets:
        v = _leading_verb(b.get("text_html", ""))
        if v:
            verb_counts[v] += 1

    duplicate_verbs = {v for v, c in verb_counts.items() if c > 1}
    if not duplicate_verbs:
        return bullets

    seen_verbs: set[str] = set()
    result = []
    for b in bullets:
        text = b.get("text_html", "")
        verb = _leading_verb(text)
        if verb and verb in duplicate_verbs and verb in seen_verbs:
            # This is a duplicate — attempt rephrase
            prompt = (
                f"Rephrase this resume bullet without using the verb '{verb}'. "
                f"Keep the same achievement and metrics. Return only the rephrased bullet, nothing else.\n\n"
                f"Bullet: {text}"
            )
            try:
                llm_resp = oracle_generate(prompt, system="")
                rephrased = llm_resp.text.strip()
                orig_len = len(text)
                rephrased_len = len(rephrased)
                # Accept if non-empty, similar length (±50%), and starts with uppercase or bullet marker
                length_ok = orig_len * 0.5 <= rephrased_len <= orig_len * 1.5
                starts_ok = bool(re.match(r"^[A-Z●]", rephrased))
                if rephrased and length_ok and starts_ok:
                    new_b = dict(b)
                    new_b["text_html"] = rephrased
                    new_b["_verb_coherence_rephrased"] = True
                    new_b["_verb_coherence_original"] = text
                    result.append(new_b)
                    seen_verbs.add(_leading_verb(rephrased) or "")
                else:
                    result.append(b)
                    seen_verbs.add(verb)
            except Exception:
                result.append(b)
                seen_verbs.add(verb)
        else:
            result.append(b)
            if verb:
                seen_verbs.add(verb)
    return result
