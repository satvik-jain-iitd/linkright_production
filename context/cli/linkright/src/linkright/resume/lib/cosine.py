"""Cosine similarity + greedy bipartite matching.

Mirrors the scoring logic in website/src/app/api/jd/analyze/route.ts —
in particular scoreRolesAgainstRequirements().
"""

from __future__ import annotations

import math
from typing import Optional


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na * nb == 0:
        return 0.0
    return dot / (na * nb)


def greedy_bipartite_match(
    req_embeddings: list[Optional[list[float]]],
    nuggets_with_emb: list[dict],  # each has {id, emb, text, ...}
    threshold: float,
) -> tuple[list[dict], dict]:
    """Greedy 1-req ↔ 1-nugget matching.

    Returns:
      matches: list of {req_idx, nugget_id, nugget_text, cosine}
      best_per_req: {req_idx: best_cosine_score}  (even if below threshold)
    """
    candidates: list[tuple[int, dict, float]] = []
    best_per_req: dict[int, float] = {i: 0.0 for i in range(len(req_embeddings))}

    for i, r_emb in enumerate(req_embeddings):
        if not r_emb:
            continue
        for n in nuggets_with_emb:
            if not n.get("emb"):
                continue
            sim = cosine(r_emb, n["emb"])
            if sim > best_per_req[i]:
                best_per_req[i] = sim
            if sim >= threshold:
                candidates.append((i, n, sim))

    candidates.sort(key=lambda x: x[2], reverse=True)

    claimed_reqs: set[int] = set()
    claimed_nuggets: set[str] = set()
    matches: list[dict] = []
    for req_idx, nugget, sim in candidates:
        if req_idx in claimed_reqs or nugget["id"] in claimed_nuggets:
            continue
        claimed_reqs.add(req_idx)
        claimed_nuggets.add(nugget["id"])
        matches.append(
            {
                "req_idx": req_idx,
                "nugget_id": nugget["id"],
                "nugget_text": nugget.get("text", ""),
                "cosine": round(sim, 4),
            }
        )

    return matches, best_per_req
